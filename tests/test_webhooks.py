import pytest
from sqlalchemy import func, select

from codelens.db import Delivery, Run
from tests.conftest import signed


def test_invalid_signature(client, payload):
    request = signed(payload)
    request["headers"]["X-Hub-Signature-256"] = "sha256=bad"
    assert client.post("/api/v1/webhooks/github", **request).status_code == 401


def test_duplicate_delivery_and_commit(client, payload, db):
    for delivery in ["a", "a", "b"]:
        assert (
            client.post("/api/v1/webhooks/github", **signed(payload, delivery)).status_code == 202
        )
    with db() as session:
        assert session.scalar(select(func.count()).select_from(Run)) == 1
        assert session.scalar(select(func.count()).select_from(Delivery)) == 2
    payload["pull_request"]["head"]["sha"] = "b" * 40
    payload["action"] = "synchronize"
    assert client.post("/api/v1/webhooks/github", **signed(payload, "c")).status_code == 202
    with db() as session:
        assert session.scalar(select(func.count()).select_from(Run)) == 2


@pytest.mark.parametrize(
    "field,value", [("installation", {"id": 999}), ("repository", {"full_name": "evil/repo"})]
)
def test_repository_authorization(client, payload, field, value):
    payload[field] = value
    assert client.post("/api/v1/webhooks/github", **signed(payload)).status_code == 403


def test_ignored_and_malformed(client, payload):
    payload["action"] = "closed"
    assert client.post("/api/v1/webhooks/github", **signed(payload)).json()["ignored"]
    payload["action"] = "opened"
    payload["pull_request"]["head"]["sha"] = "../../x"
    assert client.post("/api/v1/webhooks/github", **signed(payload)).status_code == 400
    assert client.post("/api/v1/webhooks/github", **signed([])).status_code == 400


def test_size_limit(client):
    assert client.post("/api/v1/webhooks/github", content=b"x" * 1_000_001).status_code == 413


def test_queue_limit(client, payload, monkeypatch):
    from codelens.settings import settings

    monkeypatch.setenv("CODELENS_MAX_QUEUE", "0")
    settings.cache_clear()
    assert client.post("/api/v1/webhooks/github", **signed(payload)).status_code == 429


@pytest.mark.parametrize(
    "path", ["/repositories", "/review-runs", "/review-runs/1/findings", "/settings"]
)
def test_dashboard_requires_auth(client, path):
    assert client.get("/api/v1" + path).status_code == 401


def test_disable_and_config_validation(client, auth, payload):
    assert (
        client.patch(
            "/api/v1/repositories/1/config", headers=auth, json={"shell": "bad"}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/api/v1/repositories/1/config", headers=auth, json={"max_files": 101}
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/api/v1/repositories/1/config", headers=auth, json={"enabled": False}
        ).status_code
        == 200
    )
    assert client.post("/api/v1/webhooks/github", **signed(payload)).json()["ignored"]
