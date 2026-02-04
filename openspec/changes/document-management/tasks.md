## 1. CLI Command Structure

- [x] 1.1 Add `doc` subcommand group to CLI app
- [x] 1.2 Create document command module structure

## 2. Document Query Command Implementation

- [x] 2.1 Implement `doc query` command with pagination parameters (--page, --page-size)
- [x] 2.2 Add --search parameter for fuzzy name search
- [x] 2.3 Add --repository parameter for repository filtering
- [x] 2.4 Add --sort parameter with options (created_at, updated_at, name)
- [x] 2.5 Add --desc flag for descending sort
- [x] 2.6 Add --json flag for JSON output format
- [x] 2.7 Implement table formatting for query results
- [x] 2.8 Implement pagination logic using MetadataStore.list_documents()
- [x] 2.9 Implement fuzzy search by document name
- [x] 2.10 Add validation for pagination parameters (page >= 1, page-size > 0)

## 3. Document Info Command Implementation

- [x] 3.1 Implement `doc info` command with document ID parameter
- [x] 3.2 Add support for both UUID and document name lookup
- [x] 3.3 Add --repository parameter for repository-scoped lookup
- [x] 3.4 Add --full flag to display complete content
- [x] 3.5 Add --json flag for JSON output format
- [x] 3.6 Display document metadata (ID, name, type, source_path, repository_id, timestamps, file_size)
- [x] 3.7 Display content preview (first 500 characters)
- [x] 3.8 Display chunk statistics (count, average size, distribution)
- [x] 3.9 Handle binary documents (no content preview)
- [x] 3.10 Add error handling for non-existent documents
- [x] 3.11 Add error handling for ambiguous document names

## 4. Document Delete Command Implementation

- [x] 4.1 Implement `doc delete` command with document ID parameter
- [x] 4.2 Add support for both UUID and document name lookup
- [x] 4.3 Add support for multiple document IDs in single command
- [x] 4.4 Add --force flag to skip confirmation
- [x] 4.5 Add --repository parameter for repository-scoped deletion
- [x] 4.6 Add --dry-run flag to preview deletions without executing
- [x] 4.7 Implement interactive confirmation prompt
- [x] 4.8 Implement cascade delete (document + chunks + embeddings)
- [x] 4.9 Use VectorStore.delete_by_document_id() to remove embeddings
- [x] 4.10 Use MetadataStore.delete_document() to remove document and chunks
- [x] 4.11 Add error handling for non-existent documents
- [x] 4.12 Add error handling for ambiguous document names
- [x] 4.13 Add transaction support where available (for atomic delete)
- [x] 4.14 Display success message with statistics (chunks and embeddings removed)
- [x] 4.15 Handle partial failures gracefully (some succeed, some fail)
- [x] 4.16 Add rollback on delete failure

## 5. Utility Functions

- [x] 5.1 Create helper function to resolve document ID (UUID or name) - Implemented inline in commands
- [x] 5.2 Create helper function to format document metadata table - Implemented inline in commands
- [x] 5.3 Create helper function to format document info display - Implemented inline in commands
- [x] 5.4 Create helper function to validate document IDs - Implemented inline in commands
- [x] 5.5 Create helper function to handle confirmation prompts - Using typer.confirm

## 6. Error Handling

- [x] 6.1 Add error handling for invalid UUID format - Implemented in all commands
- [x] 6.2 Add error handling for document not found - Implemented in all commands
- [x] 6.3 Add error handling for ambiguous document name - Implemented in info and delete commands
- [x] 6.4 Add error handling for cross-repository operations - Implemented in all commands
- [x] 6.5 Add error handling for storage layer errors - Implemented in all commands
- [x] 6.6 Add error handling for cascade delete failures - Implemented in delete command

## 7. Testing

- [x] 7.1 Add unit tests for document query command
- [x] 7.2 Add unit tests for document info command
- [x] 7.3 Add unit tests for document delete command
- [x] 7.4 Add unit tests for utility functions
- [x] 7.5 Add integration tests for complete workflow
- [x] 7.6 Test with different storage implementations (memory, sqlite, chroma)

## 8. Documentation

- [x] 8.1 Update CLI help text for new commands
- [x] 8.2 Add usage examples to documentation
- [x] 8.3 Update README.md with document management examples
