## 1. Storage Layer Implementation

- [x] 1.1 Add delete_by_repository() abstract method to MetadataStore base class
- [x] 1.2 Add delete_by_repository() abstract method to VectorStore base class
- [x] 1.3 Implement delete_by_repository() in InMemoryMetadataStore
- [x] 1.4 Implement delete_by_repository() in InMemoryVectorStore
- [x] 1.5 Implement delete_by_repository() in SQLiteMetadataStore
- [x] 1.6 Implement delete_by_repository() in ChromaVectorStore
- [x] 1.7 Update SQLite schema to ensure CASCADE DELETE for chunks and embeddings

## 2. Repository Manager Changes

- [x] 2.1 Add clear_repository() method to RepositoryManager class
- [x] 2.2 Add repository validation in clear_repository()
- [x] 2.3 Add error handling and logging to clear_repository()
- [x] 2.4 Test RepositoryManager.clear_repository() with all storage implementations

## 3. CLI Command Implementation

- [x] 3.1 Add repo clear subcommand to CLI
- [x] 3.2 Implement repository name argument parsing
- [x] 3.3 Implement --dry-run flag functionality
- [x] 3.4 Implement --yes/-y flag functionality
- [x] 3.5 Add confirmation prompt with warning message
- [x] 3.6 Display deletion count in success message
- [x] 3.7 Add error handling for non-existent repository
- [x] 3.8 Add error handling for storage errors

## 4. Testing

- [x] 4.1 Write unit tests for InMemoryMetadataStore.delete_by_repository()
- [x] 4.2 Write unit tests for InMemoryVectorStore.delete_by_repository()
- [x] 4.3 Write unit tests for SQLiteMetadataStore.delete_by_repository()
- [x] 4.4 Write unit tests for ChromaVectorStore.delete_by_repository()
- [x] 4.5 Write unit tests for RepositoryManager.clear_repository()
- [x] 4.6 Write integration tests for CLI clear command (happy path)
- [x] 4.7 Write integration tests for CLI clear --dry-run
- [x] 4.8 Write integration tests for CLI clear --yes
- [x] 4.9 Write integration tests for CLI clear (non-existent repository)
- [x] 4.10 Write integration tests for CLI clear (empty repository)
- [x] 4.11 Write integration tests for CLI clear (cancellation)
- [x] 4.12 Run all tests and verify passing ✓ (Fixed pytest-asyncio config, all new tests pass)

## 5. Documentation

- [x] 5.1 Update CLI help text for repo clear command
- [x] 5.2 Add examples to README.md for clear command
- [x] 5.3 Document safety mechanisms (dry-run, confirmation)
- [x] 5.4 Add integration test documentation

## 6. Validation

- [x] 6.1 Test end-to-end: create repo → add docs → clear → verify empty
- [x] 6.2 Test repository preservation after clear
- [x] 6.3 Test ability to add docs after clear
- [x] 6.4 Verify all scenarios from spec are tested
- [x] 6.5 Run full test suite to ensure no regressions
