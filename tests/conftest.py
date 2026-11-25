import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from codelens.api import app
from codelens.db import Base, Repository, get_session, make_engine
from codelens.schemas import RepoConfig
from codelens.settings import settings


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("CODELENS_ADMIN_TOKEN", "test-only-operator-token-" + "x" * 32)
    monkeypatch.setenv("CODELENS_WEBHOOK_SECRET", "test-only-webhook-secret")
    monkeypatch.setenv("CODELENS_ALLOWED_REPOSITORIES", "test/repository")
    settings.cache_clear()
    yield
    settings.cache_clear()


@pytest.fixture
def db(tmp_path, env):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            Repository(
                full_name="test/repository", installation_id=123, config=RepoConfig().model_dump()
            )
        )
        session.commit()
    yield factory
    engine.dispose()


@pytest.fixture
def client(db):
    def override():
        with db() as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth():
    return {"Authorization": "Bearer " + settings().admin_token.get_secret_value()}


@pytest.fixture
def payload():
    return {
        "action": "opened",
        "repository": {"full_name": "test/repository", "id": 321},
        "installation": {"id": 123},
        "pull_request": {
            "number": 1,
            "title": "Test change",
            "head": {"sha": "a" * 40},
            "base": {"sha": "b" * 40},
        },
    }


def signed(payload, delivery="delivery-1"):
    body = json.dumps(payload).encode()
    signature = hmac.new(
        settings().webhook_secret.get_secret_value().encode(), body, hashlib.sha256
    ).hexdigest()
    return {
        "content": body,
        "headers": {
            "X-Hub-Signature-256": f"sha256={signature}",
            "X-GitHub-Delivery": delivery,
            "X-GitHub-Event": "pull_request",
        },
    }
