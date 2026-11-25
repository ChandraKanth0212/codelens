from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CODELENS_", env_file=".env", extra="ignore")
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

    def allows(self, name: str) -> bool:
        return name.lower() in {
            value.strip().lower() for value in self.allowed_repositories.split(",") if value.strip()
        }


@lru_cache
def settings() -> Settings:
    return Settings()
