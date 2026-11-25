import json

import httpx
import pytest
from pydantic import ValidationError

from codelens.ai import Advice, OpenAIExplanationProvider
from codelens.analyzers import secrets
from codelens.schemas import Finding
from codelens.settings import Settings


def test_invalid_ai_schema():
    for payload in [
        {"findings": []},
        {"summary": "x", "code": "injected"},
        {"summary": "x" * 2001},
    ]:
        with pytest.raises(ValidationError):
            Advice.model_validate(payload)


def test_ai_sends_only_rule_metadata(monkeypatch):
    def respond(request):
        data = json.loads(request.content)
        sent = json.dumps(data)
        assert "private/path.py" not in sent
        assert "confidential-evidence" not in sent
        assert "ghp_" not in sent
        assert "F401" in sent
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"summary":"Remove unused imports."}'}}]},
        )

    client_type = httpx.Client
    monkeypatch.setattr(
        "codelens.ai.httpx.Client",
        lambda **kwargs: client_type(transport=httpx.MockTransport(respond), **kwargs),
    )
    finding = Finding(
        source="static_analyzer",
        analyzer="ruff",
        rule_id="F401",
        severity="low",
        category="maintainability",
        title="Unused import",
        file_path="private/path.py",
        start_line=1,
        end_line=1,
        explanation="confidential-evidence",
        suggested_action="remove",
    )
    secret = secrets("app.py", 'token = "ghp_' + "a" * 36 + '"', {1})
    result = OpenAIExplanationProvider(Settings()).explain([finding, *secret])
    assert result["advisory"] is True
    assert result["prompt_version"] == "rules-only-v1"
