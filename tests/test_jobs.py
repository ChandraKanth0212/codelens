import fakeredis
from rq import Queue, SimpleWorker
from rq.serializers import JSONSerializer

from codelens.db import Run
from codelens.jobs import dispatch_pending


def test_durable_outbox_dispatch_is_idempotent(db, monkeypatch):
    import codelens.jobs as jobs
    import codelens.worker as worker

    monkeypatch.setattr(jobs, "Session", db)
    monkeypatch.setattr(worker, "process_run", lambda run_id: finish(db, run_id))
    connection = fakeredis.FakeRedis()
    queue = Queue("reviews", connection=connection, serializer=JSONSerializer)
    with db() as session:
        run = Run(repository_id=1, number=42, title="Outbox", head_sha="e" * 40)
        session.add(run)
        session.commit()
        assert dispatch_pending(session, queue) == 1
        assert queue.jobs[0].func_name == "codelens.jobs.execute_review"
        assert dispatch_pending(session, queue) == 0
        run_id = run.id
    runner = SimpleWorker([queue], connection=connection, serializer=JSONSerializer)
    runner.work(burst=True)
    with db() as session:
        assert session.get(Run, run_id).status == "completed"


def finish(factory, run_id):
    with factory() as session:
        run = session.get(Run, run_id)
        assert run.status == "running"
        run.status = "completed"
        session.commit()


def test_redis_outage_keeps_durable_job(db):
    class Unavailable:
        def fetch_job(self, job_id):
            raise ConnectionError("unavailable")

    with db() as session:
        run = Run(repository_id=1, number=42, title="Outbox", head_sha="f" * 40)
        session.add(run)
        session.commit()
        import pytest

        with pytest.raises(ConnectionError):
            dispatch_pending(session, Unavailable())
        assert session.get(Run, run.id).status == "queued"


def test_old_generation_cannot_claim_new_review(db, monkeypatch):
    import codelens.jobs as jobs

    monkeypatch.setattr(jobs, "Session", db)
    with db() as session:
        run = Run(repository_id=1, number=1, title="Rerun", head_sha="a" * 40, generation=1)
        session.add(run)
        session.commit()
        run_id = run.id
    jobs.execute_review(run_id, 0)
    with db() as session:
        assert session.get(Run, run_id).status == "queued"


def test_failure_callback_bounds_retries_and_ignores_old_generation(db, monkeypatch):
    from types import SimpleNamespace

    import codelens.jobs as jobs

    monkeypatch.setattr(jobs, "Session", db)
    with db() as session:
        run = Run(
            repository_id=1,
            number=1,
            title="Retry",
            head_sha="c" * 40,
            status="running",
            attempts=1,
            generation=2,
        )
        session.add(run)
        session.commit()
        run_id = run.id
    error = RuntimeError("sensitive exception")
    jobs.job_failed(SimpleNamespace(args=(run_id, 1)), None, RuntimeError, error, None)
    with db() as session:
        assert session.get(Run, run_id).status == "running"
    jobs.job_failed(SimpleNamespace(args=(run_id, 2)), None, RuntimeError, error, None)
    with db() as session:
        run = session.get(Run, run_id)
        assert run.status == "queued"
        run.status, run.attempts = "running", 3
        session.commit()
    jobs.job_failed(SimpleNamespace(args=(run_id, 2)), None, RuntimeError, error, None)
    with db() as session:
        run = session.get(Run, run_id)
        assert run.status == "failed" and run.completed_at
        assert "sensitive exception" not in str(run.report)
