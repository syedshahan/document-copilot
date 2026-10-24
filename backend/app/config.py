from pathlib import Path
from typing import Annotated, Any

from pydantic import AnyHttpUrl, Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: AnyHttpUrl
    supabase_anon_key: SecretStr
    supabase_service_role_key: SecretStr

    database_url: PostgresDsn

    gemini_api_key: SecretStr
    gemini_embedding_model: str
    gemini_embedding_dimensions: int = Field(gt=0)

    allowed_origins: Annotated[list[AnyHttpUrl], NoDecode]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
        return origins


settings = Settings()
