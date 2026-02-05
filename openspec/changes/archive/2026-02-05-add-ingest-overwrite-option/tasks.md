# Implementation Tasks: Ingest Overwrite Feature

## 1. CLI Interface Changes

- [x] 1.1 Add `--force` flag to ingest command in `src/memory/interfaces/cli.py`
- [x] 1.2 Update `_ingest_async()` to accept force parameter
- [x] 1.3 Add validation for `--force` flag
- [x] 1.4 Update command help text to document `--force` flag behavior
- [x] 1.5 Add clear warning message when using `--force` flag

## 2. Ingestion Pipeline Enhancement

- [x] 2.1 Add `force` parameter to `IngestionPipeline.ingest_document()`
- [x] 2.2 Implement document existence check before ingestion
- [x] 2.3 Add cascade deletion logic (vector store → metadata store)
- [x] 2.4 Implement rollback mechanism for failed overwrites
- [x] 2.5 Add logging for overwrite operations
- [x] 2.6 Update pipeline to handle batch operations with force flag

## 3. Metadata Store Integration

- [x] 3.1 Verify `delete_document()` method exists and works correctly
- [x] 3.2 Ensure `delete_document()` cascade deletes all chunks
- [x] 3.3 Add method to find document by source_path and repository_id
- [x] 3.4 Test metadata store delete operations with SQLite and memory implementations

## 4. Vector Store Integration

- [x] 4.1 Verify `delete_by_document_id()` method exists in vector stores
- [x] 4.2 Ensure vector store deletion works with ChromaDB implementation
- [x] 4.3 Add error handling for vector store deletion failures
- [x] 4.4 Test vector store cascade deletion

## 5. User Feedback and Messaging

- [x] 5.1 Add distinct messages for overwrite vs new document creation
- [x] 5.2 Display document IDs before and after overwrite
- [x] 5.3 Show chunk count for overwritten documents
- [x] 5.4 Add batch operation summary (overwritten vs created)
- [x] 5.5 Display clear confirmation messages with repository information

## 6. Error Handling and Validation

- [x] 6.1 Handle partial failures during overwrite
- [x] 6.2 Attempt rollback when new document ingestion fails
- [x] 6.3 Add error messages for rollback failures
- [x] 6.4 Validate repository exists before attempting overwrite
- [x] 6.5 Handle edge cases (empty documents, non-text files)

## 7. Testing

- [x] 7.1 Create unit tests for CLI `--force` flag parsing
- [x] 7.2 Test single document overwrite scenario
- [x] 7.3 Test batch overwrite with recursive flag
- [x] 7.4 Test overwrite with repository specification
- [x] 7.5 Test non-existent document with `--force` (should create new)
- [x] 7.6 Test rollback on partial failure
- [x] 7.7 Test cascade deletion of chunks and embeddings
- [x] 7.8 Test with both SQLite and memory metadata stores
- [x] 7.9 Test with ChromaDB vector store
- [x] 7.10 Test user feedback messages are clear and accurate

## 8. Documentation

- [x] 8.1 Update CLI help text with `--force` flag description
- [x] 8.2 Add usage examples for overwrite scenarios
- [x] 8.3 Document cascade deletion behavior
- [x] 8.4 Add warning about data loss risk
- [x] 8.5 Update README with overwrite examples

## 9. Integration Testing

- [x] 9.1 Test end-to-end overwrite workflow
- [x] 9.2 Test large document overwrite performance
- [x] 9.3 Test multiple repositories with same source path
- [x] 9.4 Test concurrent overwrite operations (if applicable)
- [x] 9.5 Verify no memory leaks during batch overwrites

## 10. Finalization

- [x] 10.1 Run all existing tests to ensure no regressions
- [x] 10.2 Verify all spec scenarios are satisfied
- [x] 10.3 Test error handling edge cases
- [x] 10.4 Performance testing with large batches
- [x] 10.5 Final code review and cleanup
