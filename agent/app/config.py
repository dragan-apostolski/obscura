"""Central settings, loaded from .env. Import `settings` anywhere."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    openai_api_key: str = ""          # unused now (local embeddings); kept optional
    anthropic_api_key: str = ""       # generation, from L03

    embedding_model: str = "BAAI/bge-small-en-v1.5"   # local, free, 384-dim
    reranker_model: str = "BAAI/bge-reranker-base"    # local cross-encoder (L03)
    generation_model: str = "claude-sonnet-5"
    embedding_dim: int = 384

    chunk_tokens: int = 400
    chunk_overlap: int = 50

    # Langfuse (L08) — optional for now
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"


settings = Settings()  # type: ignore[call-arg]
