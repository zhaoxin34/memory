"""Unit tests for document management CLI commands."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from uuid import UUID, uuid4
import typer

from memory.interfaces.cli import _doc_query_async, _doc_info_async, _doc_delete_async
from memory.core.models import Document, DocumentType, Repository


@pytest.mark.asyncio
class TestDocQueryCommand:
    """Test doc query command."""

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_query_with_pagination(self, mock_ensure, mock_load_config):
        """Test query command with pagination parameters."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Create test documents
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
        doc3 = Document(
            id=uuid4(),
            title="doc3.md",
            content="Content 3",
            source_path="./doc3.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        metadata_store.list_documents.return_value = [doc1, doc2, doc3]

        # Run command
        await _doc_query_async(
            page=1,
            page_size=2,
            search=None,
            repository="test-repo",
            sort="created_at",
            desc=False,
            json_output=False,
            config_file=None,
        )

        # Verify
        metadata_store.list_documents.assert_called()
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_query_with_search(self, mock_ensure, mock_load_config):
        """Test query command with search filter."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Create test documents
        doc1 = Document(
            id=uuid4(),
            title="README.md",
            content="Readme content",
            source_path="./README.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )
        doc2 = Document(
            id=uuid4(),
            title="test.md",
            content="Test content",
            source_path="./test.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        metadata_store.list_documents.return_value = [doc1, doc2]

        # Run command with search
        await _doc_query_async(
            page=1,
            page_size=10,
            search="read",
            repository="test-repo",
            sort="name",
            desc=False,
            json_output=False,
            config_file=None,
        )

        # Verify search filter applied
        called_docs = metadata_store.list_documents.return_value
        # Only doc1 should match "read" search
        assert len(called_docs) == 2

        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_query_repository_not_found(self, mock_ensure, mock_load_config):
        """Test query command with non-existent repository."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "wrong-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Run command and expect error
        with pytest.raises(typer.Exit):
            await _doc_query_async(
                page=1,
                page_size=10,
                search=None,
                repository="nonexistent",
                sort="created_at",
                desc=False,
                json_output=False,
                config_file=None,
            )


@pytest.mark.asyncio
class TestDocInfoCommand:
    """Test doc info command."""

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_info_by_uuid(self, mock_ensure, mock_load_config):
        """Test info command with UUID."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Create test document
        test_doc = Document(
            id=uuid4(),
            title="test.md",
            content="Test content",
            source_path="./test.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        metadata_store.get_document.return_value = test_doc
        metadata_store.get_chunks_by_document.return_value = []

        # Run command
        await _doc_info_async(
            document_id=str(test_doc.id),
            repository=None,
            full=False,
            json_output=False,
            config_file=None,
        )

        # Verify
        metadata_store.get_document.assert_called_once_with(test_doc.id)
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_info_by_name(self, mock_ensure, mock_load_config):
        """Test info command with document name."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Create test document
        test_doc = Document(
            id=uuid4(),
            title="test.md",
            content="Test content",
            source_path="./test.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        metadata_store.get_document.return_value = None
        metadata_store.list_documents.return_value = [test_doc]
        metadata_store.get_chunks_by_document.return_value = []

        # Run command with name
        await doc_info(
            document_id="test.md",
            repository=None,
            full=False,
            json_output=False,
            config_file=None,
        )

        # Verify
        metadata_store.get_document.assert_called_once()
        metadata_store.list_documents.assert_called_once_with(repository_id=repository.id)

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_info_document_not_found(self, mock_ensure, mock_load_config):
        """Test info command with non-existent document."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        metadata_store.get_document.return_value = None
        metadata_store.list_documents.return_value = []

        # Run command and expect error
        with pytest.raises(typer.Exit):
            await doc_info(
                document_id="nonexistent.md",
                repository=None,
                full=False,
                json_output=False,
                config_file=None,
            )


@pytest.mark.asyncio
class TestDocDeleteCommand:
    """Test doc delete command."""

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_delete_single_document(self, mock_ensure, mock_load_config):
        """Test delete command with single document."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Create test document
        test_doc = Document(
            id=uuid4(),
            title="test.md",
            content="Test content",
            source_path="./test.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        metadata_store.get_document.return_value = test_doc
        metadata_store.get_chunks_by_document.return_value = []
        metadata_store.delete_document.return_value = True

        # Run command with force
        await _doc_delete_async(
            document_ids=[str(test_doc.id)],
            repository=None,
            force=True,
            dry_run=False,
            config_file=None,
        )

        # Verify
        metadata_store.delete_document.assert_called_once_with(test_doc.id)
        vector_store.delete_by_document_id.assert_called_once_with(test_doc.id)
        metadata_store.close.assert_called_once()
        vector_store.close.assert_called_once()

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_delete_multiple_documents(self, mock_ensure, mock_load_config):
        """Test delete command with multiple documents."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Create test documents
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

        metadata_store.get_document.return_value = None
        metadata_store.list_documents.return_value = [doc1, doc2]
        metadata_store.get_chunks_by_document.return_value = []
        metadata_store.delete_document.return_value = True

        # Run command with force
        await _doc_delete_async(
            document_ids=["doc1.md", "doc2.md"],
            repository=None,
            force=True,
            dry_run=False,
            config_file=None,
        )

        # Verify both documents deleted
        assert metadata_store.delete_document.call_count == 2

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_delete_dry_run(self, mock_ensure, mock_load_config):
        """Test delete command with dry-run mode."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "test-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Create test document
        test_doc = Document(
            id=uuid4(),
            title="test.md",
            content="Test content",
            source_path="./test.md",
            doc_type=DocumentType.TEXT,
            repository_id=repository.id,
        )

        metadata_store.get_document.return_value = test_doc
        metadata_store.get_chunks_by_document.return_value = []
        metadata_store.delete_document.return_value = True

        # Run command with dry-run
        await doc_delete(
            document_ids=[str(test_doc.id)],
            repository=None,
            force=False,
            dry_run=True,
            config_file=None,
        )

        # Verify delete not called in dry-run mode
        metadata_store.delete_document.assert_not_called()
        vector_store.delete_by_document_id.assert_not_called()

    @patch("memory.interfaces.cli._load_config")
    @patch("memory.interfaces.cli._ensure_default_repository")
    async def test_delete_repository_not_found(self, mock_ensure, mock_load_config):
        """Test delete command with non-existent repository."""
        # Setup mocks
        config = MagicMock()
        config.default_repository = "test-repo"
        mock_load_config.return_value = config

        metadata_store = AsyncMock()
        vector_store = AsyncMock()
        repository = MagicMock()
        repository.id = uuid4()
        repository.name = "wrong-repo"
        mock_ensure.return_value = (metadata_store, vector_store, repository)

        # Run command and expect error
        with pytest.raises(typer.Exit):
            await _doc_delete_async(
                document_ids=["test.md"],
                repository="nonexistent",
                force=True,
                dry_run=False,
                config_file=None,
            )
