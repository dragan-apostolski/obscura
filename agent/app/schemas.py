"""Request and response models. The API contract lives here, in one place."""
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=50)


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    thread_id: str | None = Field(
        default=None,
        # Server-issued UUID4 only. The id is effectively a bearer token for a
        # conversation, so client-invented ones are rejected rather than created.
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        description="Omit for a one-shot question; the response carries the new id. Pass "
                    "it back to continue that conversation — history is loaded from the "
                    "checkpointer, not resent.",
    )


class AskResponse(BaseModel):
    query: str
    answer: str
    sources: list[str] = []
    thread_id: str | None = None


class ErrorResponse(BaseModel):
    error: str
    request_id: str
