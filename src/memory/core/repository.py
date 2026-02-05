"""Repository management logic.

Provides high-level operations for managing repositories including:
- Creating repositories with validation
- Listing and retrieving repositories
- Deleting repositories with cascade cleanup
- Ensuring default repository exists
"""

from typing import Optional
from uuid import UUID

from memory.core.models import Repository
from memory.observability.logging import get_logger
from memory.storage.base import MetadataStore, VectorStore

logger = get_logger(__name__)


class RepositoryManager:
    """Manager for repository CRUD operations.

    Encapsulates repository management logic and coordinates between
    metadata store and vector store for consistent operations.
    """

    def __init__(self, metadata_store: MetadataStore, vector_store: VectorStore):
        """Initialize repository manager.

        Args:
            metadata_store: Storage for repository metadata
            vector_store: Storage for embeddings (for cascade deletion)
        """
        self.metadata_store = metadata_store
        self.vector_store = vector_store

    async def create_repository(
        self,
        name: str,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Repository:
        """Create a new repository.

        Args:
            name: Repository name (must be kebab-case)
            description: Optional description
            metadata: Optional metadata dictionary

        Returns:
            Created repository

        Raises:
            RepositoryError: If repository name is invalid or already exists
        """
        logger.info("repository_create_started", name=name)

        # Check if repository already exists
        existing = await self.metadata_store.get_repository_by_name(name)
        if existing:
            raise RepositoryError(f"Repository '{name}' already exists")

        # Create repository (validation happens in Pydantic model)
        try:
            repository = Repository(
                name=name,
                description=description,
                metadata=metadata or {},
            )
        except ValueError as e:
            raise RepositoryError(f"Invalid repository name: {e}") from e

        # Store repository
        await self.metadata_store.add_repository(repository)

        logger.info("repository_created", repository_id=str(repository.id), name=name)

        return repository

    async def get_repository(self, repository_id: UUID) -> Optional[Repository]:
        """Retrieve a repository by ID.

        Args:
            repository_id: Repository ID

        Returns:
            Repository if found, None otherwise
        """
        return await self.metadata_store.get_repository(repository_id)

    async def get_repository_by_name(self, name: str) -> Optional[Repository]:
        """Retrieve a repository by name.

        Args:
            name: Repository name

        Returns:
            Repository if found, None otherwise
        """
        return await self.metadata_store.get_repository_by_name(name)

    async def list_repositories(self) -> list[Repository]:
        """List all repositories.

        Returns:
            List of repositories
        """
        return await self.metadata_store.list_repositories()

    async def delete_repository(self, repository_id: UUID, force: bool = False) -> bool:
        """Delete a repository and all associated data.

        This performs cascade deletion:
        1. Delete all embeddings for the repository
        2. Delete all documents and chunks for the repository
        3. Delete the repository itself

        Args:
            repository_id: Repository ID to delete
            force: If True, skip confirmation (for programmatic use)

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryError: If deletion fails
        """
        logger.info("repository_delete_started", repository_id=str(repository_id))

        # Check if repository exists
        repository = await self.metadata_store.get_repository(repository_id)
        if not repository:
            logger.warning("repository_not_found", repository_id=str(repository_id))
            return False

        try:
            # Delete embeddings from vector store
            embedding_count = await self.vector_store.delete_by_repository(repository_id)
            logger.info(
                "repository_embeddings_deleted",
                repository_id=str(repository_id),
                count=embedding_count,
            )

            # Delete repository from metadata store (cascade deletes documents and chunks)
            deleted = await self.metadata_store.delete_repository(repository_id)

            if deleted:
                logger.info(
                    "repository_deleted",
                    repository_id=str(repository_id),
                    name=repository.name,
                )
            else:
                logger.warning(
                    "repository_delete_failed",
                    repository_id=str(repository_id),
                )

            return deleted

        except Exception as e:
            logger.error(
                "repository_delete_error",
                repository_id=str(repository_id),
                error=str(e),
            )
            raise RepositoryError(f"Failed to delete repository: {e}") from e

    async def clear_repository(self, repository_id: UUID) -> int:
        """Clear all documents from a repository.

        This removes all documents, chunks, and embeddings while
        preserving the repository itself.

        Args:
            repository_id: The repository ID to clear

        Returns:
            Number of documents deleted

        Raises:
            RepositoryNotFoundError: If repository doesn't exist
            RepositoryError: If deletion fails
        """
        logger.info("repository_clear_started", repository_id=str(repository_id))

        # Verify repository exists
        repository = await self.metadata_store.get_repository(repository_id)
        if not repository:
            logger.warning("repository_not_found", repository_id=str(repository_id))
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")

        try:
            # Delete from metadata store (documents and chunks via CASCADE)
            doc_count = await self.metadata_store.delete_by_repository(repository_id)

            # Delete from vector store
            await self.vector_store.delete_by_repository(repository_id)

            logger.info(
                "repository_cleared",
                repository_id=str(repository_id),
                document_count=doc_count,
            )

            return doc_count

        except Exception as e:
            logger.error(
                "repository_clear_error",
                repository_id=str(repository_id),
                error=str(e),
            )
            raise RepositoryError(f"Failed to clear repository: {e}") from e

    async def ensure_default_repository(self, default_name: str = "default") -> Repository:
        """Ensure the default repository exists, creating it if necessary.

        This should be called during system initialization to guarantee
        a default repository is available.

        Args:
            default_name: Name of the default repository

        Returns:
            The default repository (existing or newly created)
        """
        logger.info("ensure_default_repository", name=default_name)

        # Check if default repository exists
        repository = await self.metadata_store.get_repository_by_name(default_name)

        if repository:
            logger.info("default_repository_exists", repository_id=str(repository.id))
            return repository

        # Create default repository
        repository = await self.create_repository(
            name=default_name,
            description="Default repository for documents",
            metadata={"is_default": True},
        )

        logger.info(
            "default_repository_created",
            repository_id=str(repository.id),
            name=default_name,
        )

        return repository


class RepositoryError(Exception):
    """Exception raised during repository operations."""

    pass


class RepositoryNotFoundError(RepositoryError):
    """Exception raised when a repository is not found."""

    pass
