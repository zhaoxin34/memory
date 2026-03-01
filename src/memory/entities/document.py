"""Document entity - represents a source document."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class DocumentType(str, Enum):
    """Supported document types."""

    MARKDOWN = "markdown"
    PDF = "pdf"
    HTML = "html"
    TEXT = "text"
    UNKNOWN = "unknown"


class Document(BaseModel):
    """A source document in the knowledge base.

    Represents a single document that has been ingested into the system.
    Documents are split into chunks for embedding and retrieval.
    """

    id: UUID = Field(default_factory=uuid4)
    repository_id: UUID = Field(..., description="Repository this document belongs to")
    source_path: str = Field(..., description="Original path or URL of the document")
    doc_type: DocumentType = Field(default=DocumentType.UNKNOWN)
    title: str | None = None
    content: str = Field(..., description="Full text content of the document")
    content_md5: str | None = Field(None, description="MD5 hash of the document content")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Document content cannot be empty")
        return v
