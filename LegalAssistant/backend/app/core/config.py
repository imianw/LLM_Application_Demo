from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Legal Assistant"
    cors_origins: list[str] = Field(default=["http://localhost:5173", "http://127.0.0.1:5173"])

    data_dir: Path = ROOT_DIR / "data"
    data_file: Path = ROOT_DIR / "data" / "all_legal_clauses.json"

    dashscope_api_key: str | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    rerank_endpoint: str = "/rerank"
    rerank_url: str = "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank"
    qdrant_url: str | None = None
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "legal_assistant_labor_law"
    qdrant_batch_size: int = 64

    llm_model: str = "qwen-plus"
    embed_model: str = "text-embedding-v4"
    rerank_model: str = "qwen3-rerank"

    llm_endpoint: str = "/chat/completions"
    embedding_endpoint: str = "/embeddings"

    retrieval_top_k: int = 8
    rerank_top_k: int = 3
    min_rerank_score: float = 0.15
    request_timeout_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
