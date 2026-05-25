from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration kept in env vars so deployments can change orbit cadence and DB targets."""

    database_url: str = Field(
        default="postgresql+psycopg://groundtrack:groundtrack@localhost:5432/groundtrack",
        alias="DATABASE_URL",
    )
    tle_refresh_hours: int = Field(default=24, alias="TLE_REFRESH_HOURS")
    recompute_interval_minutes: int = Field(default=60, alias="RECOMPUTE_INTERVAL_MINUTES")
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    cors_origins: list[str] = Field(default=["http://localhost:4200"], alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
