"""Signed webhook -> RQ -> real analyzers -> authorized dashboard API.

GitHub retrieval and Redis storage are test doubles; this is not a live App test.
"""

import fakeredis
import pytest
from rq import Queue, SimpleWorker
from rq.serializers import JSONSerializer

from codelens.demo import FILES
from codelens.github import GitHub
from tests.conftest import signed


@pytest.mark.parametrize("event", ["opened", "synchronize", "reopened"])
def test_signed_event_through_rq_and_real_analyzers(client, auth, payload, db, monkeypatch, event):
    import codelens.jobs as jobs
    import codelens.worker as worker

    actual_process = worker.process_run
    monkeypatch.setattr(jobs, "Session", db)
    monkeypatch.setattr(worker, "process_run", lambda run_id: actual_process(run_id, db))
    monkeypatch.setattr(GitHub, "__init__", lambda *args: None)
    monkeypatch.setattr(GitHub, "close", lambda self: None)
    monkeypatch.setattr(
        GitHub, "retrieve", lambda self, repo, number, sha, config: (FILES, [], config)
    )
    payload["action"] = event
    accepted = client.post("/api/v1/webhooks/github", **signed(payload))
    assert accepted.status_code == 202
    run_id = accepted.json()["run_id"]
    connection = fakeredis.FakeRedis()
    queue = Queue("reviews", connection=connection, serializer=JSONSerializer)
    with db() as session:
        assert jobs.dispatch_pending(session, queue) == 1
        assert jobs.dispatch_pending(session, queue) == 0
    SimpleWorker([queue], connection=connection, serializer=JSONSerializer).work(burst=True)
    report = client.get(f"/api/v1/review-runs/{run_id}", headers=auth).json()
    assert report["status"] == "completed"
    assert report["head_sha"] == payload["pull_request"]["head"]["sha"]
    findings = client.get(f"/api/v1/review-runs/{run_id}/findings", headers=auth).json()
    assert {"F821", "F401", "eqeqeq"} <= {f["rule_id"] for f in findings}
    assert client.post("/api/v1/webhooks/github", **signed(payload)).status_code == 202
    assert len(client.get("/api/v1/review-runs", headers=auth).json()) == 1
    with db() as session:
        assert jobs.dispatch_pending(session, queue) == 0


def test_signature_covers_exact_body_and_is_required(client, payload):
    request = signed(payload)
    request["content"] += b" "
    assert client.post("/api/v1/webhooks/github", **request).status_code == 401
    request = signed(payload)
    del request["headers"]["X-Hub-Signature-256"]
    assert client.post("/api/v1/webhooks/github", **request).status_code == 401
