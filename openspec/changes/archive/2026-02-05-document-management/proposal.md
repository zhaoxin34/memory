## Why

Currently, the Memory system only supports document ingestion at the repository level, but lacks granular document-level management. Users can import documents into repositories but cannot query, view details, or delete individual documents. This limits usability and makes it difficult to manage large document collections within a repository. Without these capabilities, users must resort to external tools or manual database operations to perform basic document management tasks.

## What Changes

Add three new CLI commands for document-level management:

1. **memory doc query** - Query and list documents with advanced filtering
   - Pagination support (--page, --page-size)
   - Fuzzy search by document name (--search)
   - Repository filtering (--repository)
   - Sort options (--sort by created_at, updated_at, name)
   - Display document metadata (ID, name, source_path, chunk_count, created_at)

2. **memory doc info** - Display detailed information about a specific document
   - Document metadata (ID, name, type, source_path, repository_id)
   - Content preview (first N characters)
   - Chunk statistics (count, average size, distribution)
   - Associated metadata (created_at, updated_at, file_size)

3. **memory doc delete** - Delete a specific document and all associated data
   - Cascade delete: document + all chunks + all embeddings
   - Interactive confirmation (unless --force is specified)
   - Support for multiple document IDs in a single command
   - Repository-scoped deletion (only deletes from specified repository)

## Capabilities

### New Capabilities
- **document-query**: Query documents with pagination, fuzzy search, and repository filtering
- **document-info**: Display detailed document information and statistics
- **document-delete**: Delete documents with cascade operation to remove chunks and embeddings

### Modified Capabilities
- None. This change only adds new capabilities without modifying existing requirements.

## Impact

**Affected Code:**
- CLI interface (`src/memory/interfaces/cli.py`): Add three new command groups and handlers
- Pipelines layer: No changes required - existing pipelines already support the needed operations
- Storage layer: No changes required - MetadataStore already has list_documents() and delete_document() methods
- Core models: No changes required - Document model already exists

**APIs:**
- No API changes - this is purely a CLI enhancement

**Dependencies:**
- No new dependencies added
- Uses existing MetadataStore methods: list_documents(), get_document(), delete_document()
- Uses existing VectorStore methods: delete_by_document_id()

**Systems:**
- No system-level changes
- Works with all existing storage implementations (memory, sqlite, chroma)
