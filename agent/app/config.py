"""Central settings, loaded from .env. Import `settings` anywhere."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    openai_api_key: str = ""          # unused now (local embeddings); kept optional
    anthropic_api_key: str = ""       # generation
    gemini_api_key: str = ""          # eval judge

    embedding_model: str = "BAAI/bge-small-en-v1.5"   # local, free, 384-dim
    reranker_model: str = "BAAI/bge-reranker-large"   # local cross-encoder
    generation_model: str = "claude-sonnet-5"
    request_timeout: float = 90.0   # seconds; ChatAnthropic hangs forever if left unset
    # Ragas judge: Gemini via its OpenAI-compatible endpoint.
    judge_model: str = "gemini-2.5-flash"
    judge_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    embedding_dim: int = 384

    chunk_tokens: int = 400
    chunk_overlap: int = 50

    # Langfuse — optional for now
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"


settings = Settings()  # type: ignore[call-arg]
