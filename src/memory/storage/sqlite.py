"""SQLite storage implementation for metadata.

Provides persistent storage for documents, chunks, and repositories using SQLite.
Uses aiosqlite for async operations.
"""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

import aiosqlite

from memory.core.models import Chunk, Document, DocumentType, Repository
from memory.storage.base import MetadataStore, StorageConfig, StorageError


class SQLiteMetadataStore(MetadataStore):
    """SQLite metadata store implementation.

    Stores documents, chunks, and repositories in SQLite database.
    Uses aiosqlite for async operations.
    """

    def __init__(self, config: StorageConfig) -> None:
        """Initialize SQLite metadata store."""
        super().__init__(config)
        # Handle connection_string - can be None or a path
        import os

        conn_str = config.connection_string
        if conn_str is None:
            # Default to ~/.memory/metadata.db
            db_dir = os.path.expanduser("~/.memory")
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.join(db_dir, "metadata.db")
        elif conn_str.startswith("sqlite:///"):
            # Extract the path part and expand user
            self.db_path = os.path.expanduser(conn_str.replace("sqlite:///", ""))
        else:
            # Expand user path if needed
            self.db_path = os.path.expanduser(conn_str)

        self.connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize the metadata store (create tables)."""
        try:
            self.connection = await aiosqlite.connect(self.db_path)
            self.connection.row_factory = aiosqlite.Row

            # Create repositories table
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)

            # Create documents table with repository_id
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    content_md5 TEXT,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
                )
            """)

            # Migration: Add content_md5 column if it doesn't exist
            # Check if column exists first
            cursor = await self.connection.execute("PRAGMA table_info(documents)")
            columns = [row[1] for row in await cursor.fetchall()]
            if 'content_md5' not in columns:
                await self.connection.execute("""
                    ALTER TABLE documents ADD COLUMN content_md5 TEXT
                """)

            # Create chunks table with repository_id
            await self.connection.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    start_char INTEGER NOT NULL,
                    end_char INTEGER NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)

            # Enable foreign key constraints for CASCADE DELETE to work
            await self.connection.execute("PRAGMA foreign_keys = ON")

            # Create indices for better query performance
            await self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_repository ON documents(repository_id)"
            )
            await self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_repository ON chunks(repository_id)"
            )
            await self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id)"
            )
            await self.connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_repositories_name ON repositories(name)"
            )

            await self.connection.commit()

        except Exception as e:
            raise StorageError(
                f"Failed to initialize SQLite metadata store: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def add_repository(self, repository: Repository) -> None:
        """Store a repository."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            await self.connection.execute(
                """
                INSERT INTO repositories (id, name, description, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(repository.id),
                    repository.name,
                    repository.description,
                    repository.created_at.isoformat(),
                    repository.updated_at.isoformat(),
                    json.dumps(repository.metadata),
                ),
            )
            await self.connection.commit()
        except Exception as e:
            raise StorageError(
                f"Failed to add repository: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def get_repository(self, repository_id: UUID) -> Optional[Repository]:
        """Retrieve a repository by ID."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            cursor = await self.connection.execute(
                "SELECT * FROM repositories WHERE id = ?",
                (str(repository_id),),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return Repository(
                id=UUID(row["id"]),
                name=row["name"],
                description=row["description"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                metadata=json.loads(row["metadata"]),
            )
        except Exception as e:
            raise StorageError(
                f"Failed to get repository: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def get_repository_by_name(self, name: str) -> Optional[Repository]:
        """Retrieve a repository by name."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            cursor = await self.connection.execute(
                "SELECT * FROM repositories WHERE name = ?",
                (name,),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return Repository(
                id=UUID(row["id"]),
                name=row["name"],
                description=row["description"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                metadata=json.loads(row["metadata"]),
            )
        except Exception as e:
            raise StorageError(
                f"Failed to get repository by name: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def list_repositories(self) -> list[Repository]:
        """List all repositories."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            cursor = await self.connection.execute("SELECT * FROM repositories ORDER BY created_at")
            rows = await cursor.fetchall()

            return [
                Repository(
                    id=UUID(row["id"]),
                    name=row["name"],
                    description=row["description"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                    metadata=json.loads(row["metadata"]),
                )
                for row in rows
            ]
        except Exception as e:
            raise StorageError(
                f"Failed to list repositories: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def delete_repository(self, repository_id: UUID) -> bool:
        """Delete a repository."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            cursor = await self.connection.execute(
                "DELETE FROM repositories WHERE id = ?",
                (str(repository_id),),
            )
            await self.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            raise StorageError(
                f"Failed to delete repository: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def delete_by_repository(self, repository_id: UUID) -> int:
        """Delete all documents, chunks, and embeddings for a repository.

        This removes all data associated with a repository while preserving
        the repository itself.

        Args:
            repository_id: Repository ID to clear

        Returns:
            Number of documents deleted

        Raises:
            StorageError: If deletion fails
        """
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            # Delete all documents for this repository
            # Chunks will be automatically deleted via CASCADE DELETE
            cursor = await self.connection.execute(
                "DELETE FROM documents WHERE repository_id = ?",
                (str(repository_id),),
            )
            await self.connection.commit()
            doc_count = cursor.rowcount
            return doc_count
        except Exception as e:
            raise StorageError(
                f"Failed to delete documents by repository: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def add_document(self, document: Document) -> None:
        """Store a document."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            await self.connection.execute(
                """
                INSERT INTO documents (id, repository_id, source_path, doc_type, title, content, content_md5, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(document.id),
                    str(document.repository_id),
                    document.source_path,
                    document.doc_type.value,
                    document.title,
                    document.content,
                    document.content_md5,
                    json.dumps(document.metadata),
                    document.created_at.isoformat(),
                    document.updated_at.isoformat(),
                ),
            )
            await self.connection.commit()
        except Exception as e:
            raise StorageError(
                f"Failed to add document: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def get_document(self, document_id: UUID) -> Optional[Document]:
        """Retrieve a document by ID."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            cursor = await self.connection.execute(
                "SELECT * FROM documents WHERE id = ?",
                (str(document_id),),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return Document(
                id=UUID(row["id"]),
                repository_id=UUID(row["repository_id"]),
                source_path=row["source_path"],
                doc_type=DocumentType(row["doc_type"]),
                title=row["title"],
                content=row["content"],
                content_md5=row["content_md5"],
                metadata=json.loads(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
        except Exception as e:
            raise StorageError(
                f"Failed to get document: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def add_chunk(self, chunk: Chunk) -> None:
        """Store a chunk."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            await self.connection.execute(
                """
                INSERT INTO chunks (id, repository_id, document_id, content, chunk_index, start_char, end_char, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(chunk.id),
                    str(chunk.repository_id),
                    str(chunk.document_id),
                    chunk.content,
                    chunk.chunk_index,
                    chunk.start_char,
                    chunk.end_char,
                    json.dumps(chunk.metadata),
                    chunk.created_at.isoformat(),
                ),
            )
            await self.connection.commit()
        except Exception as e:
            raise StorageError(
                f"Failed to add chunk: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def get_chunk(self, chunk_id: UUID) -> Optional[Chunk]:
        """Retrieve a chunk by ID."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            cursor = await self.connection.execute(
                "SELECT * FROM chunks WHERE id = ?",
                (str(chunk_id),),
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return Chunk(
                id=UUID(row["id"]),
                repository_id=UUID(row["repository_id"]),
                document_id=UUID(row["document_id"]),
                content=row["content"],
                chunk_index=row["chunk_index"],
                start_char=row["start_char"],
                end_char=row["end_char"],
                metadata=json.loads(row["metadata"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        except Exception as e:
            raise StorageError(
                f"Failed to get chunk: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def get_chunks_by_document(self, document_id: UUID) -> list[Chunk]:
        """Retrieve all chunks for a document."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            cursor = await self.connection.execute(
                "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index",
                (str(document_id),),
            )
            rows = await cursor.fetchall()

            return [
                Chunk(
                    id=UUID(row["id"]),
                    repository_id=UUID(row["repository_id"]),
                    document_id=UUID(row["document_id"]),
                    content=row["content"],
                    chunk_index=row["chunk_index"],
                    start_char=row["start_char"],
                    end_char=row["end_char"],
                    metadata=json.loads(row["metadata"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]
        except Exception as e:
            raise StorageError(
                f"Failed to get chunks by document: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def delete_document(self, document_id: UUID) -> bool:
        """Delete a document and its chunks."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            # Delete chunks first (cascade should handle this, but being explicit)
            await self.connection.execute(
                "DELETE FROM chunks WHERE document_id = ?",
                (str(document_id),),
            )

            # Delete document
            cursor = await self.connection.execute(
                "DELETE FROM documents WHERE id = ?",
                (str(document_id),),
            )
            await self.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            raise StorageError(
                f"Failed to delete document: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def list_documents(
        self, limit: int = 100, offset: int = 0, repository_id: Optional[UUID] = None
    ) -> list[Document]:
        """List documents with pagination."""
        if not self.connection:
            raise StorageError("Database not initialized", storage_type="sqlite")

        try:
            if repository_id is not None:
                cursor = await self.connection.execute(
                    "SELECT * FROM documents WHERE repository_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (str(repository_id), limit, offset),
                )
            else:
                cursor = await self.connection.execute(
                    "SELECT * FROM documents ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                )

            rows = await cursor.fetchall()

            return [
                Document(
                    id=UUID(row["id"]),
                    repository_id=UUID(row["repository_id"]),
                    source_path=row["source_path"],
                    doc_type=DocumentType(row["doc_type"]),
                    title=row["title"],
                    content=row["content"],
                    content_md5=row["content_md5"],
                    metadata=json.loads(row["metadata"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]
        except Exception as e:
            raise StorageError(
                f"Failed to list documents: {e}",
                storage_type="sqlite",
                original_error=e,
            )

    async def close(self) -> None:
        """Close connections and cleanup resources."""
        if self.connection:
            await self.connection.close()
            self.connection = None
