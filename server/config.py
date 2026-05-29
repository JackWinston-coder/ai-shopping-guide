from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    zhipu_api_key: str = ""
    zhipu_llm_model: str = "GLM-5.1"
    zhipu_llm_model_fast: str = "GLM-4.5-Air"
    zhipu_embedding_model: str = "embedding-3"
    server_port: int = 8000
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    chroma_path: str = "./data/chroma"
    product_data_path: str = "./data"
    image_data_path: str = "./data"
    session_max_history: int = 50
    session_context_window: int = 10
    summary_max_tokens: int = 300
    rag_top_k: int = 5
    rag_candidate_multiplier: int = 3
    rag_vector_weight: float = 0.6
    rag_structured_weight: float = 0.4
    local_embedding_dimensions: int = 256
    jwt_secret: str = "change-me-in-production"
    jwt_expire_days: int = 7
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("zhipu_llm_model", "zhipu_llm_model_fast", "zhipu_embedding_model", mode="before")
    @classmethod
    def use_default_for_blank_model(cls, value: str, info):
        if value:
            return value
        defaults = {
            "zhipu_llm_model": "GLM-5.1",
            "zhipu_llm_model_fast": "GLM-4.5-Air",
            "zhipu_embedding_model": "embedding-3",
        }
        return defaults[info.field_name]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.jwt_secret == "change-me-in-production":
        import logging
        logging.getLogger(__name__).warning(
            "JWT_SECRET is using the default value 'change-me-in-production'. "
            "Please set a secure secret in production via the JWT_SECRET environment variable."
        )
    return s


settings = get_settings()
