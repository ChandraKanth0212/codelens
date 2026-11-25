"""RQ execution with a durable database outbox; Redis never receives source or secrets."""

import logging
import time

from redis import Redis
from rq import Queue, Retry
from rq.job import Callback
from rq.serializers import JSONSerializer
from sqlalchemy import select, update

from codelens.db import Run, Session, now
from codelens.settings import settings

logger = logging.getLogger("codelens.jobs")


def queue():
    connection = Redis.from_url(
        settings().redis_url.get_secret_value(), socket_timeout=3, socket_connect_timeout=3
    )
    return Queue("reviews", connection=connection, serializer=JSONSerializer)


def execute_review(run_id: int, generation: int):
    from codelens.worker import process_run

    with Session() as session:
        result = session.execute(
            update(Run)
            .where(Run.id == run_id, Run.generation == generation, Run.status == "queued")
            .values(status="running", started_at=now(), attempts=Run.attempts + 1)
        )
        session.commit()
        if not result.rowcount:
            return
    process_run(run_id)


def job_failed(job, connection, exception_type, exception, traceback):
    # Never persist exception text or RQ tracebacks in dashboard reports.
    with Session() as session:
        run = session.get(Run, int(job.args[0]))
        if run and run.generation == job.args[1] and run.status == "running":
            run.status = "queued" if run.attempts < 3 else "failed"
            if run.status == "failed":
                run.completed_at = now()
                run.report = {"errors": [{"message": "Job timeout or retry budget exhausted"}]}
            session.commit()


def dispatch_pending(session, target_queue=None):
    target = target_queue if target_queue is not None else queue()
    rows = session.scalars(select(Run).where(Run.status == "queued").order_by(Run.id).limit(100))
    dispatched = 0
    for run in rows:
        job_id = f"review-{run.id}-generation-{run.generation}-attempt-{run.attempts}"
        if target.fetch_job(job_id):
            continue
        target.enqueue(
            "codelens.jobs.execute_review",
            run.id,
            run.generation,
            job_id=job_id,
            unique=True,
            job_timeout=settings().job_timeout,
            result_ttl=3600,
            failure_ttl=3600,
            retry=Retry(max=2, interval=[5, 20]),
            on_failure=Callback("codelens.jobs.job_failed"),
        )
        dispatched += 1
    return dispatched


def main():
    from codelens.worker import maintain

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    while True:
        try:
            with Session() as session:
                maintain(session)
                dispatch_pending(session)
        except KeyboardInterrupt:
            return
        except Exception as error:
            logger.warning(
                "dispatch_unavailable type=%s; database jobs retained for retry",
                type(error).__name__,
            )
        time.sleep(2)


if __name__ == "__main__":
    main()
