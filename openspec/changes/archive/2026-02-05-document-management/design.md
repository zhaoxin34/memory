## Context

The Memory system currently supports document ingestion at the repository level but lacks granular document management capabilities. Users can import documents into repositories but cannot query, view details, or delete individual documents without resorting to external tools or manual database operations.

This change adds three new CLI commands: `doc query`, `doc info`, and `doc delete` to provide complete document lifecycle management. The implementation leverages existing infrastructure including MetadataStore and VectorStore interfaces.

## Goals / Non-Goals

**Goals:**
- Provide intuitive CLI commands for document-level management
- Support pagination and fuzzy search for large document collections
- Ensure cascade delete properly removes all associated data
- Maintain consistency with existing CLI patterns (e.g., `repo delete`)
- Work seamlessly with all storage implementations (memory, sqlite, chroma)

**Non-Goals:**
- Modifying the underlying storage layer or adding new storage types
- Adding authentication or authorization features
- Supporting bulk document operations beyond delete (bulk update/export will be future work)
- Modifying existing ingestion or search pipelines

## Decisions

### 1. CLI Command Structure

**Decision:** Implement as a `doc` subcommand group with three subcommands: `query`, `info`, `delete`

**Rationale:**
- Follows existing patterns: `memory repo <command>` structure
- Clear hierarchy: `memory doc <subcommand>`
- Avoids cluttering the main command namespace

**Alternatives Considered:**
- Three separate top-level commands (`memory query-doc`, `memory doc-info`, `memory delete-doc`): Rejected - less intuitive and breaks consistency
- Subcommands of existing `repo` command: Rejected - `repo` commands manage repositories, not documents

### 2. Query Implementation Strategy

**Decision:** Use existing `MetadataStore.list_documents()` with custom filtering and pagination

**Rationale:**
- No need to create new data access patterns
- Leverage existing pagination support in `list_documents()`
- Simple fuzzy search by name using SQL LIKE or Python string matching
- Storage-agnostic approach works across all implementations

**Alternatives Considered:**
- Create dedicated query service: Overkill for this use case, adds unnecessary complexity
- Direct storage queries: Breaks abstraction, storage-specific code in CLI

### 3. Delete Confirmation Flow

**Decision:** Interactive confirmation by default, skip with `--force` flag

**Rationale:**
- Prevents accidental deletion of important documents
- Consistent with `repo delete` behavior
- `--force` flag enables scripting and automation use cases

**Alternatives Considered:**
- Always require confirmation: Too verbose for automation
- Never confirm: Too dangerous

### 4. Document ID Specification

**Decision:** Accept both UUID and short name for `delete` and `info` commands

**Rationale:**
- UUIDs are unique and guaranteed to work
- Document names are user-friendly but may not be unique
- Allow both to maximize usability

**Implementation:**
- Try UUID lookup first
- Fall back to name-based lookup (warn if multiple matches)
- For delete: require exact match (UUID or unique name)

**Alternatives Considered:**
- UUID only: Too cumbersome for users
- Name only: Ambiguous and potentially unsafe

### 5. Output Format for `doc query`

**Decision:** Table format with key metadata columns, support JSON with `--json` flag

**Rationale:**
- Human-readable by default
- Structured data when needed for scripting
- Consistent with other CLI commands

**Format:**
```
ID                                    Name              Source Path          Chunks  Created
────────────────────────────────────────────────────────────────────────────────
doc-uuid-1    README.md             ./README.md         12    2024-01-15
doc-uuid-2    API Reference         ./docs/api.md       45    2024-01-16
```

## Risks / Trade-offs

**[Risk]** Document name ambiguity during delete
→ **Mitigation:** Require exact name match or UUID for delete operations. If multiple documents match name, list them and require UUID selection.

**[Risk]** Cascade delete failure could leave inconsistent state
→ **Mitigation:** Use database transactions (where supported) to ensure atomic delete. Log failures and provide retry mechanism.

**[Risk]** Performance degradation with very large repositories (10,000+ documents)
→ **Mitigation:** Pagination is mandatory for query. Consider index optimization if needed.

**[Risk]** Different storage implementations may behave differently
→ **Mitigation:** All storage implementations (memory, sqlite, chroma) use same MetadataStore/VectorStore interfaces, ensuring consistent behavior.

## Migration Plan

This change is purely additive - no existing functionality is modified.

1. Deploy new CLI commands alongside existing commands
2. No database migrations required - uses existing schema
3. Backward compatible - all existing functionality unchanged
4. No rollback needed - simply don't use new commands if issues arise

## Open Questions

None at this time. All design decisions are straightforward and well-supported by existing infrastructure.
