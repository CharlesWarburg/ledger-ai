from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "Ledger AI API"
    environment: str = "development"
    log_level: str = "INFO"
    jwt_secret_key: SecretStr = SecretStr("")
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)
    database_url: str
    upload_directory: Path = Path("uploads")
    max_upload_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        gt=0,
    )
    openai_api_key: SecretStr = SecretStr("")
    openai_invoice_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
