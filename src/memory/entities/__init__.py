"""Entities - Domain models for the knowledge base system.

This module contains pure domain entities without business logic:
- Repository: A logical container for organizing documents
- Document: A source document (file, webpage, etc.)
- Chunk: A segment of a document suitable for embedding
- Embedding: A vector representation of a chunk
- SearchResult: A retrieved chunk with relevance score
"""

from memory.entities.chunk import Chunk
from memory.entities.document import Document, DocumentType
from memory.entities.embedding import Embedding
from memory.entities.repository import Repository
from memory.entities.search_result import SearchResult

__all__ = [
    "Chunk",
    "Document",
    "DocumentType",
    "Embedding",
    "Repository",
    "SearchResult",
]
