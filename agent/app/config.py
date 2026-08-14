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
    generation_model: str = "claude-haiku-4-5"
    request_timeout: float = 90.0   # seconds; ChatAnthropic hangs forever if left unset
    # Ragas judge: Gemini via its OpenAI-compatible endpoint.
    judge_model: str = "gemini-2.5-flash"
    judge_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    embedding_dim: int = 384

    chunk_tokens: int = 400
    chunk_overlap: int = 50

    # Connection pools. Two exist: one for tool/retrieval queries, one the checkpointer
    # owns. A process holds up to (db + checkpoint) max_size connections, so size them
    # together — Supabase's session-mode pooler pins a real backend per connection, and
    # `uvicorn --workers N` multiplies both.
    db_pool_min_size: int = 1
    db_pool_max_size: int = 8
    checkpoint_pool_max_size: int = 4

    # Tool results are the bulk of an agent's context — one manual search is ~2k tokens,
    # and without this they ride along on every later turn of a conversation. Above this
    # many tokens, older tool outputs are dropped from what gets resent.
    context_edit_trigger_tokens: int = 24000
    context_edit_keep_tool_results: int = 3

    # Stamped onto every trace so a metric change can be tied to the prompt that produced
    # it. Bump whenever SYSTEM_PROMPT or a tool docstring changes.
    prompt_version: str = "2026-08-13"

    # Langfuse — optional for now
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"


settings = Settings()  # type: ignore[call-arg]
