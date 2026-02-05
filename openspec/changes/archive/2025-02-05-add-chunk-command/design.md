# Design: Chunk Command Implementation

## Context

The Memory CLI currently provides commands for ingesting documents (`ingest`), searching (`search`), and asking questions (`ask`), but lacks visibility into how documents are actually chunked during ingestion. Users need to analyze and visualize the chunking process to:
- Debug chunking parameters for optimal retrieval quality
- Understand how semantic boundaries are respected
- Experiment with different chunking strategies
- Validate that documents are being split appropriately

The system already has robust chunking capabilities in `src/memory/core/markdown_chunking.py` that perform intelligent Markdown-aware chunking. This design leverages that existing functionality while adding a new command-line interface for visualization and analysis.

## Goals / Non-Goals

**Goals:**
- Integrate chunk analysis command into existing CLI architecture
- Support both repository documents and raw file analysis
- Provide flexible output formats (table, JSON, verbose)
- Enable parameter experimentation without affecting stored data
- Maintain consistency with existing CLI patterns and user experience

**Non-Goals:**
- Modifying the core chunking algorithms
- Adding new storage backends
- Implementing batch chunk analysis of multiple repositories
- Creating a web interface for chunk visualization
- Changing the ingestion pipeline behavior

## Decisions

### Decision 1: Command Structure - Single Command vs Subcommand Group

**Choice**: Implement as a single command `memory chunk` with multiple parameters
**Rationale**:
- Simpler CLI surface area compared to subcommands (`memory chunk show`, `memory chunk analyze`)
- Follows pattern of existing commands like `search` and `ask`
- Parameters (`--size`, `--overlap`, `--test`, `--json`) provide sufficient flexibility
- Avoids deep command nesting

**Alternative Considered**: Subcommand group (`chunk_app`)
- More extensible if multiple chunk operations are added later
- Adds unnecessary complexity for initial implementation
- Inconsistent with other CLI commands in the system

### Decision 2: Input Resolution Strategy

**Choice**: Unified input handler that tries multiple resolution paths
**Resolution Order**:
1. If path exists on filesystem → treat as file/directory
2. If looks like UUID → query metadata store by UUID
3. If matches single document by name → use that document
4. If matches multiple documents → error with list
5. If no match → "not found" error

**Rationale**:
- Matches existing CLI patterns (e.g., `doc info` uses same resolution)
- Reduces cognitive load - users can use natural identifiers
- Provides clear error messages for ambiguity
- Consistent with repository-scoped operations

**Alternative Considered**: Separate commands for file vs repository
- Creates artificial distinction users don't think in terms of
- More commands to remember
- Doesn't scale if more input types are added

### Decision 3: Dynamic Configuration Override

**Choice**: Accept chunking parameters as CLI options that override default config
**Implementation**:
```python
chunk_size = config.chunking.chunk_size if not size_option else size_option
chunk_overlap = config.chunking.chunk_overlap if not overlap_option else overlap_option
```

**Rationale**:
- Allows experimentation without modifying config files
- Aligns with CLI best practices (parameters override defaults)
- Enables A/B testing of different configurations
- Supports the `--test` mode requirement

**Alternative Considered**: Separate config files per test
- File management overhead
- Can't easily compare different parameters side-by-side
- Violates principle of least surprise

### Decision 4: Markdown Chunking Integration

**Choice**: Reuse `chunk_markdown_document()` function from `markdown_chunking.py`
**Integration Points**:
- `parse_markdown_sections()` for semantic structure
- `smart_merge_chunks()` for intelligent merging
- `chunk_markdown_document()` for end-to-end chunking

**Rationale**:
- Existing, tested implementation
- Maintains consistency with ingestion behavior
- Reduces code duplication
- Benefits from future improvements to chunking module

**Alternative Considered**: Implement custom chunking for CLI
- Duplication of logic
- Risk of divergence from ingestion behavior
- Maintenance burden

### Decision 5: Repository Integration

**Choice**: Optional `--repository` parameter to specify target repository
**Behavior**:
- Defaults to `config.default_repository` if not specified
- Requires repository to exist before analysis
- Uses repository's ID for metadata lookups
- Applies repository's vector store collection naming

**Rationale**:
- Matches pattern from `doc` commands
- Provides isolation when working with multiple repositories
- Falls back to sensible default for common case
- Consistent with other repository-scoped operations

### Decision 6: Output Format Strategy

**Choice**: Three-tier output strategy:
1. **Default (Table)**: Human-readable summary with essential info
2. **JSON**: Machine-readable with complete data
3. **Verbose**: Extended details for debugging

**Table Columns**:
- Index: Sequential chunk number
- Type: Semantic type (heading, paragraph, code, list)
- Size: Character count
- Range: Start-end character positions
- Preview: First 100 characters (ellipsis if truncated)

**JSON Structure**:
```json
{
  "document": {...},
  "config": {...},
  "chunks": [...],
  "statistics": {...}
}
```

**Rationale**:
- Progressive disclosure of information
- Different formats for different use cases
- Matches existing CLI output patterns
- JSON enables programmatic processing

## Risks / Trade-offs

### Risk: Configuration Drift Between CLI Analysis and Actual Ingestion
**Issue**: Users might experiment with `--size`/`--overlap` in chunk command and see different behavior during ingestion
**Mitigation**:
- Document that chunk command shows analysis with custom parameters
- Clearly label output with actual parameters used
- Suggest updating config file if satisfied with results

### Risk: Large Documents May Produce Excessive Output
**Issue**: Very large documents could generate hundreds of chunks, overwhelming console
**Mitigation**:
- Default preview shows only first 100 characters
- `--json` format suitable for programmatic handling
- Consider pagination for very large outputs (future enhancement)

### Risk: Inconsistency with Non-Markdown Document Types
**Issue**: Current chunking is optimized for Markdown; plain text uses different strategy
**Mitigation**:
- Detect file type and apply appropriate chunking
- Document fallback behavior clearly
- Show chunking type in output to set expectations

### Risk: Performance for Large Repositories
**Issue**: Document lookup by name requires loading all documents
**Mitigation**:
- Accept UUID to bypass search
- Cache repository document list during execution
- Document name lookup limitation in help text

### Risk: Test Mode Confusion
**Issue**: Users might not understand `--test` is non-persistent
**Mitigation**:
- Clear messaging: "Running in test mode - no changes will be saved"
- Distinct banner or indicator in output
- Explicit documentation

## Migration Plan

**Implementation Order**:
1. Add CLI command scaffolding and argument parsing
2. Implement document resolution logic (UUID, name, path)
3. Integrate Markdown chunking module
4. Add output formatting (table, JSON, verbose)
5. Add error handling and validation
6. Test with various document types and edge cases
7. Documentation and help text

**Rollback Strategy**:
- CLI command addition is non-destructive
- If issues arise, can hide command via environment variable or deprecate
- No database schema changes required
- No impact on existing ingestion pipeline

## Open Questions

1. **Performance Optimization**: Should we add pagination for outputs with 100+ chunks?
2. **Batch Processing**: Future enhancement to analyze multiple documents at once?
3. **Export Functionality**: Should users be able to export chunk analysis to file?
4. **Visual Indicators**: Add progress bars for large document processing?
5. **Diff Mode**: Compare chunking results between different parameter sets?
