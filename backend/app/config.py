from __future__ import annotations
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    serper_api_key: str = ""        # serper.dev — 2,500 free queries, no CC required
    news_api_key: str = ""          # newsapi.org — 100 req/day free
    guardian_api_key: str = ""      # open-platform.theguardian.com — 500 req/day free
    database_url: str = "sqlite+aiosqlite:///./data/socratix.db"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()