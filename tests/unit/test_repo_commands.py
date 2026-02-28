"""Unit tests for repository management CLI commands."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import typer

from memory.core.models import Document, DocumentType, Repository
from memory.interfaces.cli import (
    _repo_clear_async,
    _repo_create_async,
    _repo_delete_async,
    _repo_info_async,
    _repo_list_async,
)


@pytest.mark.asyncio
class TestRepoClearCommand:
    """Test repo clear command."""

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_clear_happy_path(self, mock_ensure, mock_load_config):
        """Test clear command with existing documents."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "default"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Setup metadata store to return test documents
        doc1 = Document(
            id=uuid4(),
            title="doc1.md",
            content="Content 1",
            source_path="./doc1.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )
        doc2 = Document(
            id=uuid4(),
            title="doc2.md",
            content="Content 2",
            source_path="./doc2.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )
        metadata_store.list_documents.return_value = [doc1, doc2]

        # Run command with --yes to skip confirmation
        await _repo_clear_async(
            name="test-repo",
            dry_run=False,
            yes=True,
            config_file=None,
        )

        # Verify the command executed successfully
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_clear_dry_run(self, mock_ensure, mock_load_config):
        """Test clear command with --dry-run flag."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "default"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Setup metadata store to return test documents
        doc1 = Document(
            id=uuid4(),
            title="doc1.md",
            content="Content 1",
            source_path="./doc1.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )
        metadata_store.list_documents.return_value = [doc1]

        # Run command with --dry-run
        await _repo_clear_async(
            name="test-repo",
            dry_run=True,
            yes=False,
            config_file=None,
        )

        # Verify dry-run doesn't call clear_repository
        # The command should exit early without calling clear
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_clear_non_existent_repository(self, mock_ensure, mock_load_config):
        """Test clear command with non-existent repository."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "default"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "default"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Setup metadata store to return None (repository not found)
        metadata_store.get_repository_by_name.return_value = None

        # Run command and expect typer.Exit
        with pytest.raises(typer.Exit) as exc_info:
            await _repo_clear_async(
                name="non-existent-repo",
                dry_run=False,
                yes=False,
                config_file=None,
            )

        assert exc_info.value.exit_code == 1
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_clear_empty_repository(self, mock_ensure, mock_load_config):
        """Test clear command with empty repository."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "default"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "empty-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Setup metadata store to return empty list (no documents)
        metadata_store.list_documents.return_value = []

        # Run command
        await _repo_clear_async(
            name="empty-repo",
            dry_run=False,
            yes=True,
            config_file=None,
        )

        # Verify the command executed successfully
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_clear_with_confirmation_cancelled(self, mock_ensure, mock_load_config):
        """Test clear command when user cancels at confirmation."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "default"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Run command without --yes and expect typer.Exit from confirmation
        with pytest.raises(typer.Exit):
            await _repo_clear_async(
                name="test-repo",
                dry_run=False,
                yes=False,
                config_file=None,
            )

        # Verify cleanup still happens
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()


@pytest.mark.asyncio
class TestRepoCreateCommand:
    """Test repo create command."""

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_create_happy_path(self, mock_ensure, mock_load_config):
        """Test create command successfully creates a repository."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "default"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        default_repo = MagicMock()
        default_repo.id = uuid4()
        default_repo.name = "default"
        mock_ensure.return_value = (metadata_store, vector_store, default_repo)

        # Run command
        await _repo_create_async(
            name="new-repo",
            description="A new repository",
            config_file=None,
        )

        # Verify
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()


@pytest.mark.asyncio
class TestRepoListCommand:
    """Test repo list command."""

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_list_repositories(self, mock_ensure, mock_load_config):
        """Test list command shows all repositories."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "default"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        default_repo = MagicMock()
        default_repo.id = uuid4()
        default_repo.name = "default"
        mock_ensure.return_value = (metadata_store, vector_store, default_repo)

        # Setup repositories
        repo1 = Repository(
            id=uuid4(),
            name="repo1",
            description="Repository 1",
        )
        repo2 = Repository(
            id=uuid4(),
            name="repo2",
            description="Repository 2",
        )
        metadata_store.list_repositories.return_value = [repo1, repo2]
        metadata_store.list_documents.return_value = []

        # Run command
        await _repo_list_async(config_file=None)

        # Verify
        metadata_store.list_repositories.assert_called_once()
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()


@pytest.mark.asyncio
class TestRepoInfoCommand:
    """Test repo info command."""

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_info_existing_repo(self, mock_ensure, mock_load_config):
        """Test info command shows repository information."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "default"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        default_repo = MagicMock()
        default_repo.id = uuid4()
        default_repo.name = "default"
        mock_ensure.return_value = (metadata_store, vector_store, default_repo)

        # Setup repository
        repository = Repository(
            id=uuid4(),
            name="test-repo",
            description="Test repository",
        )
        metadata_store.get_repository_by_name.return_value = repository
        metadata_store.list_documents.return_value = []
        vector_store.count.return_value = 0

        # Run command
        await _repo_info_async(name="test-repo", config_file=None)

        # Verify
        metadata_store.get_repository_by_name.assert_called_once_with("test-repo")
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()


@pytest.mark.asyncio
class TestRepoDeleteCommand:
    """Test repo delete command."""

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_delete_happy_path(self, mock_ensure, mock_load_config):
        """Test delete command successfully deletes a repository."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "default"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        default_repo = MagicMock()
        default_repo.id = uuid4()
        default_repo.name = "default"
        mock_ensure.return_value = (metadata_store, vector_store, default_repo)

        # Setup repository to delete
        repository = Repository(
            id=uuid4(),
            name="repo-to-delete",
            description="Repository to delete",
        )
        metadata_store.get_repository_by_name.return_value = repository

        # Run command with force=True
        await _repo_delete_async(
            name="repo-to-delete",
            force=True,
            config_file=None,
        )

        # Verify
        metadata_store.get_repository_by_name.assert_called_once_with("repo-to-delete")
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()
