"""Optional advisory explanations; sends rule metadata only, never code or paths."""

from typing import Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field

from codelens.schemas import Finding
from codelens.settings import Settings


class Advice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(max_length=2000)


class ExplanationProvider(Protocol):
    def explain(self, findings: list[Finding]) -> dict: ...


class OpenAIExplanationProvider:
    def __init__(self, config: Settings):
        self.config = config

    def explain(self, findings: list[Finding]) -> dict:
        metadata = [
            {"analyzer": f.analyzer, "rule": f.rule_id, "severity": f.severity}
            for f in findings[:30]
            if f.source == "static_analyzer"
        ]
        if not metadata:
            return {"status": "skipped", "reason": "No eligible static findings"}
        with httpx.Client(timeout=20) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.config.ai_key.get_secret_value()}"},
                json={
                    "model": self.config.ai_model,
                    "max_tokens": 600,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {
                            "role": "system",
                            "content": "Explain static rule metadata to a developer. "
                            "Do not assert verified vulnerabilities or invent code context. "
                            "Return JSON with only a summary string. Your advice is advisory.",
                        },
                        {"role": "user", "content": __import__("json").dumps(metadata)},
                    ],
                },
            )
            response.raise_for_status()
            advice = Advice.model_validate_json(response.json()["choices"][0]["message"]["content"])
        return {
            "status": "completed",
            "advisory": True,
            "provider": "openai",
            "model": self.config.ai_model,
            "prompt_version": "rules-only-v1",
            **advice.model_dump(),
        }
