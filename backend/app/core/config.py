from pathlib import Path

from pydantic_settings import BaseSettings

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

class Settings(BaseSettings):
    database_url: str

    class Config:
        env_file = ENV_FILE

settings = Settings()
