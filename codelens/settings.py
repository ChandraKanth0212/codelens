from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CODELENS_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )
    database_url: str = "sqlite:///./codelens.db"
    redis_url: SecretStr = SecretStr("redis://localhost:6379/0")
    job_timeout: int = Field(default=300, ge=30, le=600)
    analyzer_mode: Literal["local", "spool"] = "local"
    analysis_directory: str = "/analysis"
    admin_token: SecretStr = SecretStr("")
    webhook_secret: SecretStr = SecretStr("")
    github_app_id: str = ""
    github_private_key_path: str = ""
    allowed_repositories: str = ""
    max_queue: int = Field(default=100, ge=0, le=10000)
    ai_enabled: bool = False
    ai_key: SecretStr = SecretStr("")
    ai_model: str = "gpt-4.1-mini"
    retention_days: int = Field(default=30, ge=1, le=3650)

    @field_validator("admin_token", "webhook_secret")
    @classmethod
    def reject_example_credentials(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() in {
            "replace-with-a-random-token-at-least-32-characters",
            "replace-with-another-random-secret",
        }:
            raise ValueError("Replace example credentials with independently generated secrets")
        return value

    def allows(self, name: str) -> bool:
        return name.lower() in {
            value.strip().lower() for value in self.allowed_repositories.split(",") if value.strip()
        }


@lru_cache
def settings() -> Settings:
    return Settings()
