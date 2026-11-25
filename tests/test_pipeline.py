from datetime import timedelta

from sqlalchemy import select

from codelens.db import Run, now
from codelens.worker import claim, maintain, process_run
from tests.conftest import signed


def test_webhook_to_persisted_report(client, auth, payload, db, monkeypatch):
    from codelens.demo import FILES
    from codelens.github import GitHub

    monkeypatch.setattr(GitHub, "__init__", lambda *args: None)
    monkeypatch.setattr(
        GitHub, "retrieve", lambda self, repo, number, sha, config: (FILES, [], config)
    )
    monkeypatch.setattr(GitHub, "close", lambda self: None)
    run_id = client.post("/api/v1/webhooks/github", **signed(payload)).json()["run_id"]
    with db() as session:
        assert claim(session) == run_id
    process_run(run_id, db)
    run = client.get(f"/api/v1/review-runs/{run_id}", headers=auth).json()
    assert run["status"] == "completed"
    assert run["head_sha"] == "a" * 40
    findings = client.get(f"/api/v1/review-runs/{run_id}/findings", headers=auth).json()
    assert {f["analyzer"] for f in findings} == {"ruff", "eslint"}
    finding = findings[0]
    assert (
        client.post(
            f"/api/v1/findings/{finding['id']}/feedback", headers=auth, json={"value": "useful"}
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/review-runs/{run_id}/findings", headers=auth).json()[0]["feedback"]
        == "useful"
    )
    assert "service_fee" not in str(findings)


def test_demo_and_deletion(client, auth, db):
    run_id = client.post("/api/v1/demo", headers=auth).json()["run_id"]
    with db() as session:
        claim(session)
    process_run(run_id, db)
    run = client.get(f"/api/v1/review-runs/{run_id}", headers=auth).json()
    assert run["is_demo"] and run["status"] == "completed"
    assert (
        client.delete(f"/api/v1/repositories/{run['repository_id']}", headers=auth).status_code
        == 204
    )
    assert client.get(f"/api/v1/review-runs/{run_id}", headers=auth).status_code == 404


def test_worker_claim_and_stale_retry(db):
    with db() as session:
        session.add(Run(repository_id=1, number=1, title="Test", head_sha="a" * 40))
        session.commit()
        run_id = claim(session)
        assert claim(session) is None
        session.get(Run, run_id).started_at = now() - timedelta(hours=1)
        session.commit()
        maintain(session)
        session.expire_all()
        assert session.get(Run, run_id).status == "queued"
        assert claim(session) == run_id
        run = session.get(Run, run_id)
        run.started_at = now() - timedelta(hours=1)
        run.attempts = 3
        session.commit()
        maintain(session)
        session.expire_all()
        assert session.get(Run, run_id).status == "failed"


def test_retention(db):
    with db() as session:
        session.add(
            Run(
                repository_id=1,
                number=1,
                title="Old",
                head_sha="c" * 40,
                status="completed",
                created_at=now() - timedelta(days=40),
            )
        )
        session.commit()
        maintain(session)
        assert session.scalar(select(Run)) is None


def test_provider_failure_preserves_static_findings(client, auth, payload, db, monkeypatch):
    from codelens.ai import OpenAIExplanationProvider
    from codelens.db import Repository
    from codelens.demo import FILES
    from codelens.github import GitHub
    from codelens.settings import settings

    monkeypatch.setenv("CODELENS_AI_ENABLED", "true")
    settings.cache_clear()
    with db() as session:
        repo = session.get(Repository, 1)
        repo.config = {**repo.config, "ai_enabled": True}
        session.commit()
    monkeypatch.setattr(GitHub, "__init__", lambda *args: None)
    monkeypatch.setattr(
        GitHub, "retrieve", lambda self, repo, number, sha, config: (FILES, [], config)
    )
    monkeypatch.setattr(GitHub, "close", lambda self: None)

    def fail(*args):
        raise RuntimeError("sensitive provider detail")

    monkeypatch.setattr(OpenAIExplanationProvider, "explain", fail)
    run_id = client.post("/api/v1/webhooks/github", **signed(payload)).json()["run_id"]
    with db() as session:
        claim(session)
    process_run(run_id, db)
    run = client.get(f"/api/v1/review-runs/{run_id}", headers=auth).json()
    assert run["status"] == "partial"
    assert run["report"]["finding_count"] >= 4
    assert run["report"]["ai"]["status"] == "failed"
    assert "sensitive provider detail" not in str(run)
