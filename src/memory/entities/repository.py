"""Repository entity - represents a document collection."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Repository(BaseModel):
    """A repository for organizing and isolating document collections.

    Repositories provide logical isolation between different projects or topics,
    ensuring that documents, chunks, and embeddings are kept separate.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., pattern="^[a-z0-9-]+$", description="Repository name (kebab-case)")
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Repository name cannot be empty")
        return v
