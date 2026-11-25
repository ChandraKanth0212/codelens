import pytest
from sqlalchemy import select

from codelens.db import FindingRecord, Repository, Run, User
from codelens.users import provision
from tests.conftest import signed


@pytest.fixture
def identities(client, db, payload):
    response = client.post("/api/v1/webhooks/github", **signed(payload))
    assert response.status_code == 202
    run_id = response.json()["run_id"]
    with db() as session:
        other = Repository(full_name="other/private", installation_id=456)
        session.add(other)
        session.commit()
        owner = provision(session, "owner@example.test", "Owner", [1], "owner")
        reviewer = provision(session, "reviewer@example.test", "Reviewer", [1], "reviewer")
        outsider = provision(session, "outsider@example.test", "Other", [other.id], "owner")
        run = session.get(Run, run_id)
        finding = FindingRecord(
            run_id=run_id, fingerprint="test", data={"title": "private finding"}
        )
        session.add(finding)
        session.commit()
        assert all(
            user.token_hash not in {owner, reviewer, outsider}
            for user in session.scalars(select(User))
        )
        return {
            "owner": {"Authorization": f"Bearer {owner}"},
            "reviewer": {"Authorization": f"Bearer {reviewer}"},
            "outsider": {"Authorization": f"Bearer {outsider}"},
            "run": run_id,
            "pr": run.pull_request_id,
            "finding": finding.id,
        }


def test_unowned_objects_are_invisible(client, identities):
    auth = identities["outsider"]
    for path in [
        "/repositories/1",
        f"/review-runs/{identities['run']}",
        f"/review-runs/{identities['run']}/findings",
        f"/pull-requests/{identities['pr']}",
    ]:
        assert client.get("/api/v1" + path, headers=auth).status_code == 404
    assert client.get("/api/v1/review-runs", headers=auth).json() == []
    assert client.get("/api/v1/pull-requests", headers=auth).json() == []
    assert client.patch("/api/v1/repositories/1/config", headers=auth, json={}).status_code == 404
    assert (
        client.post(
            f"/api/v1/findings/{identities['finding']}/feedback",
            headers=auth,
            json={"value": "useful"},
        ).status_code
        == 404
    )


def test_reviewer_reads_but_cannot_configure(client, identities):
    auth = identities["reviewer"]
    assert client.get(f"/api/v1/review-runs/{identities['run']}", headers=auth).status_code == 200
    assert client.get("/api/v1/repositories", headers=auth).json()[0]["can_configure"] is False
    assert (
        client.patch(
            "/api/v1/repositories/1/config", headers=auth, json={"ai_enabled": True}
        ).status_code
        == 403
    )
    assert client.post("/api/v1/demo", headers=auth).status_code == 403
    assert (
        client.post(
            "/api/v1/repositories",
            headers=auth,
            json={"full_name": "test/new", "installation_id": 123},
        ).status_code
        == 403
    )
    assert (
        client.patch(
            "/api/v1/repositories/1/config", headers=identities["owner"], json={"enabled": False}
        ).status_code
        == 200
    )


def test_revoked_user_cannot_authenticate(client, identities, db):
    with db() as session:
        user = session.scalar(select(User).where(User.email == "owner@example.test"))
        user.enabled = False
        session.commit()
    assert client.get("/api/v1/repositories", headers=identities["owner"]).status_code == 401
