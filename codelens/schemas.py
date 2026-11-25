import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["critical", "high", "medium", "low", "info"]


class RepoConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1] = 1
    enabled: bool = True
    include: list[str] = Field(default_factory=lambda: ["*"])
    exclude: list[str] = Field(default_factory=list)
    analyzers: list[Literal["ruff", "eslint", "secrets"]] = Field(
        default_factory=lambda: ["ruff", "eslint", "secrets"]
    )
    ai_enabled: bool = False
    max_files: int = Field(default=20, ge=1, le=100)
    max_file_bytes: int = Field(default=100_000, ge=1000, le=200_000)
    max_total_bytes: int = Field(default=500_000, ge=1000, le=1_000_000)
    max_processing_seconds: int = Field(default=120, ge=5, le=240)
    severity_threshold: Severity = "info"
    github_feedback_enabled: Literal[False] = False


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Literal["static_analyzer", "secret_scanner"]
    analyzer: str
    rule_id: str
    severity: Severity
    category: str
    title: str
    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    explanation: str
    suggested_action: str
    evidence: str = "Source omitted to protect sensitive content."
    confidence: Literal["high", "medium", "low"] = "high"

    @property
    def fingerprint(self) -> str:
        key = f"{self.analyzer}:{self.rule_id}:{self.file_path}:{self.start_line}"
        return hashlib.sha256(key.encode()).hexdigest()[:24]


class Feedback(BaseModel):
    value: Literal["useful", "not_useful", "ignored", "unreviewed"]


class RepositoryInput(BaseModel):
    full_name: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    installation_id: int = Field(gt=0)
