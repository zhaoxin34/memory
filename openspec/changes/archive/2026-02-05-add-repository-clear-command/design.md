# Design: Repository Clear Command

## Overview

This document outlines the technical implementation design for adding a `clear` subcommand to the `memory repo` CLI command that removes all documents, chunks, and embeddings from a specified repository while preserving the repository itself.

## Architecture

### Component Interactions

```
CLI Command (repo clear)
    ↓
RepositoryManager.clear_repository()
    ↓
MetadataStore.delete_by_repository()
    ↓
VectorStore.delete_by_repository()
    ↓
Return deletion count
```

## Implementation Details

### 1. Storage Layer Changes

#### MetadataStore Interface (`src/memory/storage/base.py`)

Add abstract method to `MetadataStore` base class:

```python
from abc import abstractmethod
from typing import Optional

class MetadataStore:
    @abstractmethod
    async def delete_by_repository(self, repository_id: str) -> int:
        """Delete all documents, chunks, and embeddings for a repository.

        Args:
            repository_id: The repository ID to delete

        Returns:
            Number of documents deleted

        Raises:
            StorageError: If deletion fails
        """
        pass
```

#### VectorStore Interface (`src/memory/storage/base.py`)

Add abstract method to `VectorStore` base class:

```python
class VectorStore:
    @abstractmethod
    async def delete_by_repository(self, repository_id: str) -> int:
        """Delete all embeddings for a repository.

        Args:
            repository_id: The repository ID to delete

        Returns:
            Number of embeddings deleted

        Raises:
            StorageError: If deletion fails
        """
        pass
```

#### InMemoryMetadataStore Implementation (`src/memory/storage/memory.py`)

```python
class InMemoryMetadataStore(MetadataStore):
    async def delete_by_repository(self, repository_id: str) -> int:
        """Delete all data for a repository from in-memory storage."""
        # Count documents to be deleted
        docs_to_delete = [doc for doc in self.documents.values()
                          if doc.repository_id == repository_id]
        doc_count = len(docs_to_delete)

        # Delete documents (chunks will be cascade deleted via foreign key)
        for doc in docs_to_delete:
            del self.documents[doc.id]

        # Explicitly delete chunks for this repository
        chunks_to_delete = [
            chunk_id for chunk_id, chunk in self.chunks.items()
            if chunk.repository_id == repository_id
        ]
        for chunk_id in chunks_to_delete:
            del self.chunks[chunk_id]

        # Delete embeddings for this repository
        embeddings_to_delete = [
            emb_id for emb_id, emb in self.embeddings.items()
            if emb.repository_id == repository_id
        ]
        for emb_id in embeddings_to_delete:
            del self.embeddings[emb_id]

        return doc_count
```

#### SQLiteMetadataStore Implementation (`src/memory/storage/sqlite.py`)

```python
class SQLiteMetadataStore(MetadataStore):
    async def delete_by_repository(self, repository_id: str) -> int:
        """Delete all data for a repository from SQLite."""
        async with self._get_connection() as conn:
            # Use CASCADE DELETE to automatically delete chunks and embeddings
            cursor = await conn.execute(
                "DELETE FROM documents WHERE repository_id = ?",
                (repository_id,)
            )
            doc_count = cursor.rowcount

        return doc_count

    async def _create_tables(self) -> None:
        """Ensure tables exist with CASCADE DELETE."""
        await super()._create_tables()

        # Recreate chunks table with CASCADE DELETE
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                repository_id TEXT NOT NULL,
                content TEXT NOT NULL,
                start_position INTEGER NOT NULL,
                end_position INTEGER NOT NULL,
                token_count INTEGER NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (repository_id) REFERENCES repositories(id)
                    ON DELETE CASCADE
            )
        """)

        # Recreate embeddings table with CASCADE DELETE
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL,
                repository_id TEXT NOT NULL,
                vector BLOB NOT NULL,
                model_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chunk_id) REFERENCES chunks(id)
                    ON DELETE CASCADE,
                FOREIGN KEY (repository_id) REFERENCES repositories(id)
                    ON DELETE CASCADE
            )
        """)
```

#### InMemoryVectorStore Implementation (`src/memory/storage/memory.py`)

```python
class InMemoryVectorStore(VectorStore):
    async def delete_by_repository(self, repository_id: str) -> int:
        """Delete all embeddings for a repository from in-memory storage."""
        collection_name = f"{self.collection_name}_{repository_id}"

        if collection_name in self.collections:
            # Get count before deletion
            embedding_count = len(self.collections[collection_name])

            # Delete the collection
            del self.collections[collection_name]

            return embedding_count

        return 0
```

#### ChromaVectorStore Implementation (`src/memory/storage/chroma.py`)

```python
class ChromaVectorStore(VectorStore):
    async def delete_by_repository(self, repository_id: str) -> int:
        """Delete all embeddings for a repository from ChromaDB."""
        collection_name = self._sanitize_collection_name(
            f"{self.collection_name}_{repository_id}"
        )

        try:
            collection = self.client.get_collection(collection_name)

            # Get all IDs in the collection
            ids = collection.get(ids=[])

            if ids and 'ids' in ids:
                # Delete all embeddings
                collection.delete(ids=ids['ids'])
                return len(ids['ids'])

            return 0

        except CollectionNotFoundError:
            # Collection doesn't exist, nothing to delete
            return 0
```

### 2. Repository Manager Changes

#### RepositoryManager Class (`src/memory/core/repository.py`)

Add new method to `RepositoryManager`:

```python
class RepositoryManager:
    async def clear_repository(self, repository_id: str) -> int:
        """Clear all documents from a repository.

        This removes all documents, chunks, and embeddings while
        preserving the repository itself.

        Args:
            repository_id: The repository ID to clear

        Returns:
            Number of documents deleted

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            StorageError: If deletion fails
        """
        # Verify repository exists
        repository = await self.get_repository(repository_id)
        if not repository:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")

        # Delete from metadata store
        doc_count = await self.metadata_store.delete_by_repository(repository_id)

        # Delete from vector store
        await self.vector_store.delete_by_repository(repository_id)

        logger.info(
            "Repository cleared",
            repository_id=repository_id,
            document_count=doc_count
        )

        return doc_count
```

### 3. CLI Command Implementation

#### Repo Commands (`src/memory/interfaces/cli.py`)

Add new `repo clear` subcommand:

```python
@click.group()
def repo():
    """Repository management commands."""
    pass

@repo.command()
@click.argument('repository_name')
@click.option('--dry-run', is_flag=True,
              help='Preview what would be deleted without actually deleting')
@click.option('--yes', '-y', is_flag=True,
              help='Skip confirmation prompt')
@click.pass_context
async def clear(ctx, repository_name, dry_run, yes):
    """Clear all documents from a repository.

    This removes all documents, chunks, and embeddings from the
    specified repository while preserving the repository itself.

    REPOSITORY_NAME: Name of the repository to clear
    """
    config = ctx.obj['config']

    # Get repository manager
    repository_manager = RepositoryManager(
        metadata_store=await create_metadata_store(config),
        vector_store=await create_vector_store(config)
    )

    # Get repository by name
    repository = await repository_manager.get_repository_by_name(repository_name)

    if not repository:
        click.echo(
            f"Error: Repository '{repository_name}' not found",
            err=True
        )
        ctx.exit(1)

    # Get document count for preview
    documents = await repository_manager.metadata_store.list_documents(
        repository_id=repository.id,
        limit=0
    )
    # Note: Need to add count method or get total count

    if dry_run:
        click.echo(f"DRY RUN: Would clear {doc_count} documents from '{repository_name}'")
        click.echo("No changes were made.")
        ctx.exit(0)

    # Confirmation prompt
    if not yes:
        click.echo(f"\nWARNING: This will permanently delete ALL documents")
        click.echo(f"from repository '{repository_name}'.\n")

        if not click.confirm('Are you sure you want to continue?'):
            click.echo("Operation cancelled.")
            ctx.exit(0)

    # Clear repository
    try:
        deleted_count = await repository_manager.clear_repository(repository.id)

        click.echo(f"\n✓ Successfully cleared {deleted_count} documents")
        click.echo(f"  Repository '{repository_name}' is now empty")

    except Exception as e:
        click.echo(f"\n✗ Error clearing repository: {e}", err=True)
        ctx.exit(1)
```

## Safety Mechanisms

### 1. Confirmation Prompts

- Default behavior requires explicit user confirmation
- `--yes` flag bypasses confirmation (use with caution)
- Clear warning message about irreversible nature

### 2. Dry-Run Mode

- `--dry-run` flag previews operations
- Shows document count that would be deleted
- No actual changes are made
- Useful for scripting and automation

### 3. Repository Preservation

- Only deletes documents, chunks, and embeddings
- Repository configuration remains intact
- Repository metadata preserved
- Can continue using repository immediately after

## Error Handling

### Repository Not Found
- Clear error message
- Non-zero exit code
- No changes made

### Storage Errors
- Catch and display storage-specific errors
- Log error details for debugging
- Non-zero exit code
- Atomic operation (all-or-nothing)

### Concurrent Access
- Repository should be locked during clear operation
- Prevent simultaneous modifications
- Use database transactions for consistency

## Performance Considerations

### Batch Deletion
- VectorStore: Delete collections in bulk
- MetadataStore: Use CASCADE DELETE or batch queries
- Avoid O(n) individual deletions

### Progress Indication
- For large repositories, show progress
- Consider async operations to avoid blocking

### Memory Usage
- InMemory stores: Clear collections immediately
- ChromaDB: Drop collections entirely
- SQLite: Use transactions for efficiency

## Testing Strategy

### Unit Tests

1. **MetadataStore Tests**
   - Test `delete_by_repository()` with existing repository
   - Test with non-existent repository
   - Test with empty repository
   - Test CASCADE DELETE behavior

2. **VectorStore Tests**
   - Test `delete_by_repository()` with existing repository
   - Test with non-existent repository
   - Test with empty repository
   - Test collection cleanup

3. **RepositoryManager Tests**
   - Test `clear_repository()` happy path
   - Test with non-existent repository
   - Test repository preservation
   - Test error handling

### Integration Tests

1. **CLI Tests**
   - Test dry-run mode
   - Test confirmation prompt
   - Test --yes flag
   - Test error cases

2. **End-to-End Tests**
   - Create repository → Add documents → Clear → Verify empty
   - Verify repository metadata intact
   - Verify can add documents after clear

## Migration Strategy

### No Breaking Changes
- Pure additive feature
- No existing functionality modified
- Backward compatible

### Optional Feature
- Works with all storage implementations
- Graceful degradation for future stores

## Future Enhancements

### Potential Additions

1. **Selective Clearing**
   - Clear by document type
   - Clear by date range
   - Clear by tags/metadata

2. **Partial Recovery**
   - Trash/restore functionality
   - Backup before clear

3. **Bulk Operations**
   - Clear multiple repositories
   - Clear all repositories

4. **Async Progress**
   - Real-time progress bar
   - Cancelable operations

## Conclusion

This design provides a safe, efficient, and user-friendly way to clear repositories while maintaining data integrity and providing appropriate safeguards against accidental data loss.
