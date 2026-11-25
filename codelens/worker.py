import logging
import time
from datetime import timedelta

from sqlalchemy import delete, select, update

from codelens.ai import OpenAIExplanationProvider
from codelens.analyzers import lint, secrets
from codelens.db import Delivery, FindingRecord, Repository, Run, Session, now
from codelens.demo import FILES
from codelens.diffs import added_lines
from codelens.github import GitHub, GitHubTransientError
from codelens.schemas import Finding, RepoConfig
from codelens.settings import settings

logger = logging.getLogger("codelens.worker")


def analyze(files: list[dict], config: RepoConfig):
    findings, errors = {}, []
    deadline = time.monotonic() + config.max_processing_seconds
    for file in files:
        path, content = file["path"], file["content"]
        lines = added_lines(file["patch"])
        adapters = ["ruff" if path.endswith(".py") else "eslint", "secrets"]
        for analyzer in adapters:
            if time.monotonic() >= deadline:
                errors.append(
                    {
                        "analyzer": "pipeline",
                        "message": "Analysis processing-time limit reached; remaining checks skipped.",
                    }
                )
                return list(findings.values()), errors
            if analyzer not in config.analyzers:
                continue
            try:
                result = (
                    secrets(path, content, lines)
                    if analyzer == "secrets"
                    else lint(path, content, lines, analyzer)
                )
                for finding in result:
                    findings[finding.fingerprint] = finding
            except Exception:
                errors.append(
                    {
                        "analyzer": analyzer,
                        "file": path,
                        "message": "Analyzer failed or timed out; no clean-scan claim can be made.",
                    }
                )
    return list(findings.values()), errors


def claim(session):
    # Postgres uses SKIP LOCKED; SQLite demo uses a compare-and-swap update.
    run = session.scalar(
        select(Run)
        .where(Run.status == "queued")
        .order_by(Run.id)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not run:
        return None
    result = session.execute(
        update(Run)
        .where(Run.id == run.id, Run.status == "queued")
        .values(status="running", started_at=now(), attempts=Run.attempts + 1)
    )
    session.commit()
    return run.id if result.rowcount else None


def process_run(run_id: int, session_factory=Session):
    with session_factory() as session:
        run = session.get(Run, run_id)
        if not run or run.status != "running":
            return
        repo = session.get(Repository, run.repository_id)
        config = RepoConfig.model_validate(repo.config)
        try:
            skipped = []
            if run.is_demo:
                files = FILES
            else:
                if not settings().allows(repo.full_name):
                    raise RuntimeError("Repository no longer allowlisted")
                github = GitHub(settings(), repo.installation_id)
                try:
                    files, skipped, config = github.retrieve(
                        repo.full_name, run.number, run.head_sha, config
                    )
                finally:
                    github.close()
            if settings().analyzer_mode == "spool":
                from codelens.sandbox import request_analysis

                findings, errors = request_analysis(files, config)
            else:
                findings, errors = analyze(files, config)
            ai = {"status": "disabled"}
            if not run.is_demo and config.ai_enabled and settings().ai_enabled:
                try:
                    ai = OpenAIExplanationProvider(settings()).explain(findings)
                    allowed_lines = {f["path"]: added_lines(f["patch"]) for f in files}
                    for item in ai.pop("findings", []):
                        finding = Finding.model_validate(item)
                        lines = allowed_lines.get(finding.file_path, set())
                        if (
                            finding.source == "ai"
                            and finding.start_line <= finding.end_line
                            and finding.end_line - finding.start_line < 1000
                            and all(
                                n in lines for n in range(finding.start_line, finding.end_line + 1)
                            )
                        ):
                            findings.append(finding)
                        else:
                            ai["rejected_findings"] = ai.get("rejected_findings", 0) + 1
                except Exception:
                    ai = {"status": "failed", "reason": "Provider unavailable or invalid response"}
                    errors.append({"analyzer": "ai", "message": ai["reason"]})
            session.execute(delete(FindingRecord).where(FindingRecord.run_id == run.id))
            for finding in findings:
                session.add(
                    FindingRecord(
                        run_id=run.id, fingerprint=finding.fingerprint, data=finding.model_dump()
                    )
                )
            run.status = "partial" if errors else "completed"
            run.report = {
                "files_reviewed": [f["path"] for f in files],
                "skipped": skipped,
                "errors": errors,
                "ai": ai,
                "finding_count": len(findings),
                "config": config.model_dump(),
                "notice": "Findings are review assistance, not proof of safety or vulnerability.",
            }
        except GitHubTransientError:
            # RQ applies bounded backoff; callback retains a safe state for the next attempt.
            raise RuntimeError("GitHub temporarily unavailable; review retry requested") from None
        except Exception:
            # Exception strings may contain sensitive provider responses or source.
            run.status = "failed"
            run.report = {
                "errors": [
                    {
                        "message": "Retrieval failed. Check App permissions, commit freshness, configuration, and file limits."
                    }
                ]
            }
        run.completed_at = now()
        session.commit()
        logger.info("run_finished run_id=%s status=%s", run.id, run.status)


def maintain(session):
    cutoff = now() - timedelta(minutes=15)
    session.execute(
        update(Run)
        .where(Run.status == "running", Run.started_at < cutoff, Run.attempts < 3)
        .values(status="queued")
    )
    session.execute(
        update(Run)
        .where(Run.status == "running", Run.started_at < cutoff, Run.attempts >= 3)
        .values(
            status="failed",
            completed_at=now(),
            report={"errors": [{"message": "Worker retry budget exhausted"}]},
        )
    )
    old = select(Run.id).where(
        Run.created_at < now() - timedelta(days=settings().retention_days),
        Run.status.in_(["completed", "partial", "failed"]),
    )
    session.execute(delete(Delivery).where(Delivery.run_id.in_(old)))
    session.execute(delete(FindingRecord).where(FindingRecord.run_id.in_(old)))
    session.execute(delete(Run).where(Run.id.in_(old)))
    session.commit()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    tick = 0
    while True:
        try:
            with Session() as session:
                if tick % 60 == 0:
                    maintain(session)
                run_id = claim(session)
            if run_id:
                process_run(run_id)
            else:
                time.sleep(2)
            tick += 1
        except KeyboardInterrupt:
            return
        except Exception:
            logger.error("worker_iteration_failed; retrying in 5 seconds")
            time.sleep(5)


if __name__ == "__main__":
    main()
