from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_ROOT / ".env", REPOSITORY_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Seoullo API"
    app_env: str = "development"
    debug: bool = False
    api_prefix: str = "/api"
    frontend_origins: str = "http://localhost:5173"

    database_path: str = ""
    seoul_data_dir: str = ""

    fingerprint_secret: str = "change-me-in-production"

    kakao_rest_api_key: str = ""

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-5-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_reason_timeout_seconds: float = 20.0
    chat_semantic_search_enabled: bool = False

    pinecone_api_key: str = ""
    pinecone_index_name: str = "seoullo"
    pinecone_emotion_index_name: str = "seoullo-emotions"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"
    pinecone_places_namespace: str = "places"
    pinecone_checkins_namespace: str = "checkins"
    pinecone_community_namespace: str = "community"
    pinecone_emotion_namespace: str = "profiles"

    @property
    def database_file(self) -> Path:
        value = self.database_path.strip()
        return Path(value).expanduser().resolve() if value else REPOSITORY_ROOT / "database" / "seoullo.db"

    @property
    def data_directory(self) -> Path:
        value = self.seoul_data_dir.strip()
        return Path(value).expanduser().resolve() if value else REPOSITORY_ROOT / "data" / "서울"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_file.as_posix()}"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def pinecone_configured(self) -> bool:
        return bool(self.pinecone_api_key and self.openai_api_key)

    @property
    def pinecone_emotion_configured(self) -> bool:
        return bool(self.pinecone_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
