from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field
import os

class Settings(BaseSettings):
    """
    Core configuration using zero-trust principles.
    Secrets are read from environment and kept as SecretStr to prevent leak in logs.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    # LLM Settings
    openai_api_key: SecretStr = Field(..., description="OpenAI API Key for Agent reasoning")

    # API Settings
    statsbomb_github_url: str = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
    api_football_key: SecretStr | None = None

    # Storage Settings
    fernet_encryption_key: SecretStr = Field(..., description="Valid Fernet key for encrypting data at rest")
    duckdb_path: str = Field("data/db/football_gravity.duckdb", description="Path to DuckDB database")

    # Audit & Security
    audit_log_path: str = "logs/audit.jsonl"
    log_level: str = "INFO"

    def get_fernet_bytes(self) -> bytes:
        return self.fernet_encryption_key.get_secret_value().encode('utf-8')

# Singleton settings instance
def get_settings() -> Settings:
    return Settings()
