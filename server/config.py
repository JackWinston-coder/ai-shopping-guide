from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DOMAIN_RULES: dict[str, dict] = {
    "耳机": {
        "sub_categories": ["耳机"],
        "boost_terms": ["降噪", "无线"],
        "hard_constraint_fields": ["title", "sub_category"],
    },
    "跑步": {
        "sub_categories": ["跑步鞋", "徒步鞋", "篮球鞋"],
        "boost_terms": ["缓震", "运动鞋", "运动", "训练", "轻量", "速干", "鞋"],
        "hard_constraint_fields": ["title", "sub_category"],
        "hard_constraint_match": ["鞋"],
    },
    "咖啡": {
        "sub_categories": ["咖啡"],
        "boost_terms": ["提神", "冲泡"],
    },
    "油皮": {
        "sub_categories": [],
        "boost_terms": ["控油", "清爽", "油脂", "毛孔"],
    },
}


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
    return Settings()


settings = get_settings()
