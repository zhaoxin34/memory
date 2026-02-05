# Proposal: Add Ingest Overwrite Option

## Why

Currently, when ingesting documents using the `memory ingest` command, if a document with the same source path already exists in the repository, the operation will fail with an error. This is problematic for users who:
- Need to update existing documents with new content
- Want to re-import documents after making changes
- Are using memory in a CI/CD pipeline where documents may change
- Need to refresh their knowledge base without manual cleanup

Users currently have to manually delete existing documents before re-importing, which is cumbersome for batch operations.

## What Changes

Add a `--force` (or `--overwrite`) option to the `ingest` command that enables overwriting existing documents with the same source path.

**New Capability:**
- Add `--force` / `--overwrite` flag to `ingest` command
- When enabled, delete existing documents before importing new ones
- Cascade delete all associated chunks and embeddings
- Provide clear feedback about what was overwritten

**Behavior:**
- **Without `--force`**: Current behavior - fails if document exists
- **With `--force`**: Overwrites existing document (same source_path + repository)
- Clear success messages showing document was overwritten vs newly created

## Capabilities

### New Capabilities
- `ingest-overwrite`: Complete document overwrite functionality with cascade deletion of chunks and embeddings

### Modified Capabilities
- `ingest-command`: Extends existing ingest command requirements to support overwrite behavior

## Impact

- **CLI Interface** (`src/memory/interfaces/cli.py`): Add `--force` option to ingest command
- **Ingestion Pipeline** (`src/memory/pipelines/ingestion.py`): Add overwrite check before ingestion
- **Metadata Store**: May need delete operation if not already present
- **Vector Store**: Cascade delete embeddings for overwritten documents
- **User Experience**: Clear messaging about overwrite vs new document creation
