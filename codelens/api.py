import hashlib
import hmac
import json
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from codelens.db import Delivery, FindingRecord, Repository, Run, get_session
from codelens.schemas import Feedback, RepoConfig, RepositoryInput
from codelens.settings import settings


@asynccontextmanager
async def lifespan(app):
    if len(settings().admin_token.get_secret_value()) < 32:
        raise RuntimeError("Set CODELENS_ADMIN_TOKEN to at least 32 random characters")
    yield


app = FastAPI(title="CodeLens", version="0.1.0", lifespan=lifespan)


def authenticated(authorization: str = Header(default="")):
    expected = settings().admin_token.get_secret_value()
    if not expected or not hmac.compare_digest(
        authorization.encode(), f"Bearer {expected}".encode()
    ):
        raise HTTPException(401, "A valid operator token is required")


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
def configuration():
    config = settings()
    return {
        "github_configured": bool(config.github_app_id and config.github_private_key_path),
        "webhook_configured": bool(config.webhook_secret.get_secret_value()),
        "ai_enabled": config.ai_enabled,
        "retention_days": config.retention_days,
        "allowed_repositories": [
            v.strip() for v in config.allowed_repositories.split(",") if v.strip()
        ],
        "auth_mode": "single_operator",
    }


@app.get("/api/v1/repositories", dependencies=protected)
def repositories(session=Depends(get_session)):
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "installation_id": r.installation_id,
            "config": RepoConfig.model_validate(r.config).model_dump(),
        }
        for r in session.scalars(select(Repository))
    ]


@app.post("/api/v1/repositories", dependencies=protected, status_code=201)
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
def configure(repo_id: int, body: RepoConfig, session=Depends(get_session)):
    repo = session.get(Repository, repo_id)
    if not repo:
        raise HTTPException(404, "Repository not found")
    repo.config = body.model_dump()
    session.commit()
    return repo.config


@app.delete("/api/v1/repositories/{repo_id}", dependencies=protected, status_code=204)
def delete_repository(repo_id: int, session=Depends(get_session)):
    repo = session.get(Repository, repo_id)
    if not repo:
        raise HTTPException(404, "Repository not found")
    ids = select(Run.id).where(Run.repository_id == repo_id)
    if session.scalar(
        select(Run.id).where(Run.repository_id == repo_id, Run.status.in_(["running", "queued"]))
    ):
        raise HTTPException(409, "Wait until active reviews finish before deleting")
    session.execute(delete(FindingRecord).where(FindingRecord.run_id.in_(ids)))
    session.execute(delete(Delivery).where(Delivery.run_id.in_(ids)))
    session.execute(delete(Run).where(Run.repository_id == repo_id))
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
        "status": run.status,
        "is_demo": run.is_demo,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
        "report": run.report,
        "url": None if run.is_demo else f"https://github.com/{repo.full_name}/pull/{run.number}",
    }


@app.get("/api/v1/review-runs", dependencies=protected)
def runs(session=Depends(get_session)):
    result = session.execute(
        select(Run, Repository).join(Repository).order_by(Run.id.desc()).limit(100)
    )
    return [run_dict(run, repo) for run, repo in result]


@app.get("/api/v1/review-runs/{run_id}", dependencies=protected)
def run_detail(run_id: int, session=Depends(get_session)):
    run = session.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Review not found")
    return run_dict(run, session.get(Repository, run.repository_id))


@app.get("/api/v1/review-runs/{run_id}/findings", dependencies=protected)
def findings(run_id: int, session=Depends(get_session)):
    if not session.get(Run, run_id):
        raise HTTPException(404, "Review not found")
    return [
        {**f.data, "id": f.id, "fingerprint": f.fingerprint, "feedback": f.feedback}
        for f in session.scalars(select(FindingRecord).where(FindingRecord.run_id == run_id))
    ]


@app.post("/api/v1/findings/{finding_id}/feedback", dependencies=protected)
def feedback(finding_id: int, body: Feedback, session=Depends(get_session)):
    finding = session.get(FindingRecord, finding_id)
    if not finding:
        raise HTTPException(404, "Finding not found")
    finding.feedback = body.value
    session.commit()
    return {"feedback": finding.feedback}


@app.post("/api/v1/demo", dependencies=protected, status_code=202)
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
        installation = int(event["installation"]["id"])
        pr = event["pull_request"]
        sha, title, number = pr["head"]["sha"], pr["title"], int(pr["number"])
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or not isinstance(title, str) or number < 1:
            raise ValueError()
    except (ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(400, "Malformed pull request event") from None
    repo = session.scalar(
        select(Repository).where(
            Repository.full_name == name, Repository.installation_id == installation
        )
    )
    if not repo or not settings().allows(name):
        raise HTTPException(403, "Repository or installation is not authorized")
    if not RepoConfig.model_validate(repo.config).enabled:
        return {"ignored": True, "reason": "Repository disabled"}
    duplicate = session.get(Delivery, delivery_id)
    if duplicate:
        return {"run_id": duplicate.run_id, "duplicate": True}
    run = session.scalar(
        select(Run).where(Run.repository_id == repo.id, Run.number == number, Run.head_sha == sha)
    )
    if not run:
        pending = session.scalar(
            select(func.count()).select_from(Run).where(Run.status.in_(["queued", "running"]))
        )
        if pending >= settings().max_queue:
            raise HTTPException(429, "Queue is full; redeliver this event later")
        run = Run(repository_id=repo.id, number=number, title=title[:512], head_sha=sha)
        session.add(run)
    try:
        session.flush()
        session.add(Delivery(id=delivery_id, run_id=run.id))
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


dist = Path(__file__).resolve().parent.parent / "web" / "dist"
if dist.exists():
    app.mount("/", StaticFiles(directory=dist, html=True), name="dashboard")
