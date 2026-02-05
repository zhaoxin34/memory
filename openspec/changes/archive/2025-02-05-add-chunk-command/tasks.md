# Implementation Tasks: Chunk Command

## 1. CLI Command Structure

- [x] 1.1 Add `@app.command()` decorator for chunk command in `src/memory/interfaces/cli.py`
- [x] 1.2 Define command signature with positional `source` argument
- [x] 1.3 Add CLI parameters: `--size`, `--overlap`, `--test`, `--json`, `--verbose`, `--repository`
- [x] 1.4 Create async wrapper function `_chunk_async()`
- [x] 1.5 Add command help text and parameter descriptions

## 2. Document Resolution Logic

- [x] 2.1 Implement input type detection (file path vs UUID vs name)
- [x] 2.2 Add file system check for direct file/directory access
- [x] 2.3 Implement UUID-based document lookup in metadata store
- [x] 2.4 Add name-based document search with multi-match handling
- [x] 2.5 Create unified document retrieval function
- [x] 2.6 Add repository-scoped lookup with `--repository` parameter

## 3. Chunking Integration

- [x] 3.1 Import `chunk_markdown_document()` from `src/memory/core/markdown_chunking.py`
- [x] 3.2 Create dynamic `ChunkingConfig` from CLI parameters
- [x] 3.3 Implement test mode that doesn't persist to repository
- [x] 3.4 Handle both Markdown and plain text documents
- [x] 3.5 Add chunking statistics calculation (count, avg, min, max)
- [x] 3.6 Track semantic chunk types (heading, paragraph, code, list, etc.)

## 4. Output Formatting

- [x] 4.1 Create default table output with Rich library
- [x] 4.2 Implement table columns: Index, Type, Size, Range, Preview
- [x] 4.3 Add JSON output format with complete metadata
- [x] 4.4 Implement verbose mode with full content and mapping
- [x] 4.5 Create statistics summary display
- [x] 4.6 Add chunk type distribution visualization

## 5. Error Handling and Validation

- [x] 5.1 Add "document not found" error handling
- [x] 5.2 Handle invalid file paths gracefully
- [x] 5.3 Add non-text file detection and warnings
- [x] 5.4 Handle empty documents with appropriate message
- [x] 5.5 Validate chunking parameters (size > 0, overlap >= 0)
- [x] 5.6 Add repository existence check
- [x] 5.7 Implement multi-match name disambiguation

## 6. Integration and Cleanup

- [x] 6.1 Add resource cleanup with `finally` blocks
- [x] 6.2 Integrate with existing `_ensure_default_repository()` function
- [x] 6.3 Add repository information display
- [x] 6.4 Ensure consistent logging with existing commands
- [x] 6.5 Add progress indicators for large documents

## 7. Testing and Documentation

- [x] 7.1 Create unit tests for document resolution logic
- [x] 7.2 Add tests for chunking parameter override
- [x] 7.3 Test all output formats (table, JSON, verbose)
- [x] 7.4 Add integration tests with sample documents
- [x] 7.5 Test error scenarios and edge cases
- [x] 7.6 Verify Markdown vs plain text handling
- [x] 7.7 Update CLI help documentation
- [x] 7.8 Add usage examples to help text

## 8. Finalization

- [x] 8.1 Run comprehensive test suite
- [x] 8.2 Verify all specs scenarios are satisfied
- [x] 8.3 Test with various document types and sizes
- [x] 8.4 Validate repository integration works correctly
- [x] 8.5 Performance testing with large documents
