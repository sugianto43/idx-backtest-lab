from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    version: str = "0.1.0"
    database_path: str = "./data/idx_backtesting_lab.duckdb"
    optimization_max_candidate_count: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
