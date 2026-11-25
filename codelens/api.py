import hashlib
import hmac
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from codelens.auth import authenticated, can_configure, operator, permitted_ids, require_repository
from codelens.db import (
    Delivery,
    FindingRecord,
    GitHubInstallation,
    PullRequest,
    Repository,
    RepositoryAccess,
    Run,
    get_session,
)
from codelens.schemas import Feedback, RepoConfig, RepositoryInput
from codelens.settings import settings


@asynccontextmanager
async def lifespan(app):
    if len(settings().admin_token.get_secret_value()) < 32:
        raise RuntimeError("Set CODELENS_ADMIN_TOKEN to at least 32 random characters")
    yield


app = FastAPI(title="CodeLens", version="0.1.0", lifespan=lifespan)


protected = [Depends(authenticated)]


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
    )
    return response


@app.get("/api/v1/health")
def health(session=Depends(get_session)):
    session.execute(text("SELECT 1"))
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/settings", dependencies=protected)
def configuration(principal=Depends(authenticated), session=Depends(get_session)):
    config = settings()
    return {
        "github_configured": bool(config.github_app_id and config.github_private_key_path),
        "webhook_configured": bool(config.webhook_secret.get_secret_value()),
        "ai_enabled": config.ai_enabled,
        "retention_days": config.retention_days,
        "allowed_repositories": [
            v.strip() for v in config.allowed_repositories.split(",") if v.strip()
        ]
        if principal.is_operator
        else list(
            session.scalars(
                select(Repository.full_name).where(Repository.id.in_(permitted_ids(principal)))
            )
        ),
        "auth_mode": "repository_tokens",
        "is_operator": principal.is_operator,
    }


@app.get("/api/v1/repositories", dependencies=protected)
def repositories(principal=Depends(authenticated), session=Depends(get_session)):
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "installation_id": r.installation_id,
            "config": RepoConfig.model_validate(r.config).model_dump(),
            "can_configure": can_configure(session, principal, r.id),
        }
        for r in session.scalars(
            select(Repository).where(Repository.id.in_(permitted_ids(principal)))
        )
    ]


@app.post("/api/v1/repositories", dependencies=[Depends(operator)], status_code=201)
def add_repository(body: RepositoryInput, session=Depends(get_session)):
    if not settings().allows(body.full_name):
        raise HTTPException(403, "Add this repository to CODELENS_ALLOWED_REPOSITORIES first")
    repo = session.scalar(select(Repository).where(Repository.full_name == body.full_name.lower()))
    if repo:
        raise HTTPException(409, "Repository is already registered")
    repo = Repository(
        full_name=body.full_name.lower(),
        installation_id=body.installation_id,
        config=RepoConfig().model_dump(),
    )
    session.add(repo)
    session.commit()
    return {"id": repo.id}


@app.patch("/api/v1/repositories/{repo_id}/config", dependencies=protected)
def configure(
    repo_id: int, body: RepoConfig, principal=Depends(authenticated), session=Depends(get_session)
):
    repo = require_repository(session, principal, repo_id, write=True)
    repo.config = body.model_dump()
    session.commit()
    return repo.config


@app.delete("/api/v1/repositories/{repo_id}", dependencies=protected, status_code=204)
def delete_repository(repo_id: int, principal=Depends(authenticated), session=Depends(get_session)):
    repo = require_repository(session, principal, repo_id, write=True)
    ids = select(Run.id).where(Run.repository_id == repo_id)
    if session.scalar(
        select(Run.id).where(Run.repository_id == repo_id, Run.status.in_(["running", "queued"]))
    ):
        raise HTTPException(409, "Wait until active reviews finish before deleting")
    session.execute(delete(FindingRecord).where(FindingRecord.run_id.in_(ids)))
    session.execute(delete(Delivery).where(Delivery.run_id.in_(ids)))
    session.execute(delete(Run).where(Run.repository_id == repo_id))
    session.execute(delete(PullRequest).where(PullRequest.repository_id == repo_id))
    session.execute(delete(RepositoryAccess).where(RepositoryAccess.repository_id == repo_id))
    session.delete(repo)
    session.commit()


def run_dict(run, repo):
    return {
        "id": run.id,
        "repository_id": repo.id,
        "repository": repo.full_name,
        "number": run.number,
        "title": run.title,
        "head_sha": run.head_sha,
        "base_sha": run.base_sha,
        "pull_request_id": run.pull_request_id,
        "status": run.status,
        "is_demo": run.is_demo,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
        "report": run.report,
        "url": None if run.is_demo else f"https://github.com/{repo.full_name}/pull/{run.number}",
    }


@app.get("/api/v1/review-runs", dependencies=protected)
def runs(principal=Depends(authenticated), session=Depends(get_session)):
    result = session.execute(
        select(Run, Repository)
        .join(Repository)
        .where(Run.repository_id.in_(permitted_ids(principal)))
        .order_by(Run.id.desc())
        .limit(100)
    )
    return [run_dict(run, repo) for run, repo in result]


@app.get("/api/v1/review-runs/{run_id}", dependencies=protected)
def run_detail(run_id: int, principal=Depends(authenticated), session=Depends(get_session)):
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Review not found")
    require_repository(session, principal, run.repository_id)
    return run_dict(run, session.get(Repository, run.repository_id))


@app.get("/api/v1/review-runs/{run_id}/findings", dependencies=protected)
def findings(run_id: int, principal=Depends(authenticated), session=Depends(get_session)):
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Review not found")
    require_repository(session, principal, run.repository_id)
    return [
        {**f.data, "id": f.id, "fingerprint": f.fingerprint, "feedback": f.feedback}
        for f in session.scalars(select(FindingRecord).where(FindingRecord.run_id == run_id))
    ]


@app.post("/api/v1/findings/{finding_id}/feedback", dependencies=protected)
def feedback(
    finding_id: int, body: Feedback, principal=Depends(authenticated), session=Depends(get_session)
):
    finding = session.get(FindingRecord, finding_id)
    if not finding:
        raise HTTPException(404, "Finding not found")
    run = session.get(Run, finding.run_id)
    require_repository(session, principal, run.repository_id)
    finding.feedback = body.value
    session.commit()
    return {"feedback": finding.feedback}


@app.post("/api/v1/demo", dependencies=[Depends(operator)], status_code=202)
def demo(session=Depends(get_session)):
    repo = session.scalar(select(Repository).where(Repository.full_name == "demo/checkout-service"))
    if not repo:
        repo = Repository(
            full_name="demo/checkout-service", installation_id=0, config=RepoConfig().model_dump()
        )
        session.add(repo)
        session.flush()
    run = session.scalar(select(Run).where(Run.repository_id == repo.id, Run.is_demo.is_(True)))
    if not run:
        run = Run(
            repository_id=repo.id,
            number=42,
            title="Add discount validation to checkout",
            head_sha="a1b2c3d4" * 5,
            is_demo=True,
        )
        session.add(run)
    elif run.status in {"completed", "partial", "failed"}:
        run.status = "queued"
        run.report = {}
        run.completed_at = None
        run.attempts = 0
        run.generation += 1
    session.commit()
    return {"run_id": run.id}


@app.post("/api/v1/webhooks/github", status_code=202)
async def webhook(request: Request, session=Depends(get_session)):
    secret = settings().webhook_secret.get_secret_value()
    if not secret:
        raise HTTPException(503, "Webhook integration is not configured")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 1_000_000:
            raise HTTPException(413, "Webhook payload exceeds limit")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(
        expected.encode(), request.headers.get("x-hub-signature-256", "").encode()
    ):
        raise HTTPException(401, "Invalid webhook signature")
    if request.headers.get("x-github-event") != "pull_request":
        return {"ignored": True}
    delivery_id = request.headers.get("x-github-delivery", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", delivery_id):
        raise HTTPException(400, "Invalid delivery ID")
    try:
        event = json.loads(body)
        if not isinstance(event, dict):
            raise ValueError()
        if event.get("action") not in {"opened", "synchronize", "reopened"}:
            return {"ignored": True}
        name = event["repository"]["full_name"].lower()
        github_repo_id = int(event["repository"]["id"])
        installation = int(event["installation"]["id"])
        pr = event["pull_request"]
        sha, title, number = pr["head"]["sha"], pr["title"], int(pr["number"])
        base_sha = pr["base"]["sha"]
        if (
            not re.fullmatch(r"[0-9a-f]{40}", sha)
            or not re.fullmatch(r"[0-9a-f]{40}", base_sha)
            or not isinstance(title, str)
            or number < 1
            or github_repo_id < 1
        ):
            raise ValueError()
    except (ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(400, "Malformed pull request event") from None
    repo = session.scalar(
        select(Repository)
        .where(Repository.full_name == name, Repository.installation_id == installation)
        .with_for_update()
    )
    if not repo or not settings().allows(name):
        raise HTTPException(403, "Repository or installation is not authorized")
    if repo.github_repository_id not in (None, github_repo_id):
        raise HTTPException(403, "Repository identity mismatch")
    if not RepoConfig.model_validate(repo.config).enabled:
        return {"ignored": True, "reason": "Repository disabled"}
    duplicate = session.get(Delivery, delivery_id)
    if duplicate:
        return {"run_id": duplicate.run_id, "duplicate": True}
    install = session.scalar(
        select(GitHubInstallation).where(GitHubInstallation.github_installation_id == installation)
    )
    if not install:
        try:
            with session.begin_nested():
                install = GitHubInstallation(
                    github_installation_id=installation, account_login=name.split("/")[0]
                )
                session.add(install)
                session.flush()
        except IntegrityError:
            install = session.scalar(
                select(GitHubInstallation).where(
                    GitHubInstallation.github_installation_id == installation
                )
            )
    repo.installation_record_id = install.id
    repo.github_repository_id = github_repo_id
    repo.default_branch = str(event["repository"].get("default_branch", "main"))[:256]
    pull = session.scalar(
        select(PullRequest).where(
            PullRequest.repository_id == repo.id, PullRequest.number == number
        )
    )
    if not pull:
        pull = PullRequest(
            repository_id=repo.id,
            number=number,
            title=title[:512],
            html_url=f"https://github.com/{name}/pull/{number}",
            head_sha=sha,
            base_sha=base_sha,
        )
        session.add(pull)
    else:
        pull.title, pull.head_sha, pull.base_sha = title[:512], sha, base_sha
    session.flush()
    run = session.scalar(
        select(Run).where(Run.repository_id == repo.id, Run.number == number, Run.head_sha == sha)
    )
    if not run:
        pending = session.scalar(
            select(func.count()).select_from(Run).where(Run.status.in_(["queued", "running"]))
        )
        if pending >= settings().max_queue:
            raise HTTPException(429, "Queue is full; redeliver this event later")
        run = Run(
            repository_id=repo.id,
            number=number,
            title=title[:512],
            head_sha=sha,
            base_sha=base_sha,
            pull_request_id=pull.id,
        )
        session.add(run)
    try:
        session.flush()
        session.add(
            Delivery(
                id=delivery_id,
                run_id=run.id,
                event_metadata={
                    "action": event["action"],
                    "repository_id": github_repo_id,
                    "installation_id": installation,
                    "head_sha": sha,
                    "base_sha": base_sha,
                },
            )
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        run = session.scalar(
            select(Run).where(
                Run.repository_id == repo.id, Run.number == number, Run.head_sha == sha
            )
        )
        if not run:
            raise HTTPException(409, "Concurrent delivery; retry") from None
    return {"run_id": run.id}


@app.get("/api/v1/repositories/{repo_id}", dependencies=protected)
def repository_detail(repo_id: int, principal=Depends(authenticated), session=Depends(get_session)):
    repo = require_repository(session, principal, repo_id)
    return {
        "id": repo.id,
        "full_name": repo.full_name,
        "github_repository_id": repo.github_repository_id,
        "installation_id": repo.installation_id,
        "default_branch": repo.default_branch,
        "config": RepoConfig.model_validate(repo.config).model_dump(),
    }


def pr_dict(pull):
    return {
        "id": pull.id,
        "repository_id": pull.repository_id,
        "number": pull.number,
        "title": pull.title,
        "url": pull.html_url,
        "head_sha": pull.head_sha,
        "base_sha": pull.base_sha,
        "state": pull.state,
        "updated_at": pull.updated_at,
    }


@app.get("/api/v1/pull-requests", dependencies=protected)
def pull_requests(principal=Depends(authenticated), session=Depends(get_session)):
    return [
        pr_dict(pull)
        for pull in session.scalars(
            select(PullRequest)
            .where(PullRequest.repository_id.in_(permitted_ids(principal)))
            .order_by(PullRequest.updated_at.desc())
            .limit(100)
        )
    ]


@app.get("/api/v1/pull-requests/{pr_id}", dependencies=protected)
def pull_request_detail(pr_id: int, principal=Depends(authenticated), session=Depends(get_session)):
    pull = session.get(PullRequest, pr_id)
    if not pull:
        raise HTTPException(404, "Pull request not found")
    require_repository(session, principal, pull.repository_id)
    return pr_dict(pull)


dist = Path(__file__).resolve().parent.parent / "web" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="dashboard")
