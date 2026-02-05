# Design: Ingest Overwrite Implementation

## Context

The current `memory ingest` command fails when attempting to import a document with a source path that already exists in the repository. This creates friction for users who need to update documents, work in iterative workflows, or use the system in automated environments.

The system needs to support overwriting existing documents while maintaining data integrity and providing clear feedback. This requires changes across multiple layers: CLI, pipeline, metadata store, and vector store.

## Goals / Non-Goals

**Goals:**
- Add `--force` flag to `ingest` command for overwriting existing documents
- Implement cascade deletion of chunks and embeddings when overwriting
- Provide clear user feedback distinguishing overwrite vs new document creation
- Maintain repository isolation during overwrite operations
- Ensure atomicity where possible to prevent data corruption

**Non-Goals:**
- Implementing partial updates or diff-based updates
- Adding merge capabilities for documents with conflicts
- Creating a version history for overwritten documents
- Supporting selective overwrite (e.g., only update metadata, keep chunks)
- Adding undo/rollback functionality for overwrite operations

## Decisions

### Decision 1: Flag Name: `--force` vs `--overwrite`

**Choice**: Use `--force` as the flag name
**Rationale**:
- More concise and widely recognized in CLI tools
- Consistent with Git's `--force` flag behavior
- Shorter to type
- Clear semantic meaning (force the operation despite conflicts)

**Alternative Considered**: `--overwrite`
- More descriptive but longer
- Less commonly used in CLI tools
- Could be confused with file system operations

### Decision 2: Document Matching Strategy

**Choice**: Match documents by `source_path` AND `repository_id`
**Rationale**:
- Ensures repository isolation (won't overwrite documents in other repositories)
- Source path is the natural identifier for document identity
- Matches how users think about "same document, updated content"

**Alternatives Considered**:
- Match by document ID: Too low-level, users don't know document IDs
- Match by title: Titles can change, less stable than file paths
- Match by content hash: No user-friendly way to specify

### Decision 3: Cascade Deletion Order

**Choice**: Delete from vector store first, then metadata store
**Rationale**:
- Vector store operations may be more expensive/longer-running
- If metadata deletion fails, it's easier to recover than losing vector consistency
- Allows for potential rollback if metadata operation fails

**Alternatives Considered**:
- Delete from metadata first: Risk of orphaned embeddings
- Delete in parallel: Could lead to inconsistent state

### Decision 4: Implementation Location

**Choice**: Implement overwrite logic in IngestionPipeline
**Rationale**:
- Centralizes the ingestion logic
- Pipeline already manages the document lifecycle
- Easier to maintain transaction-like behavior
- Reusable if ingest is called from other contexts

**Alternatives Considered**:
- CLI layer: Would duplicate logic if pipeline used elsewhere
- Metadata store: Mixes business logic with data access
- Separate overwrite service: Over-engineering for this use case

### Decision 5: Error Handling Strategy

**Choice**: Fail-fast with rollback attempts on partial failures
**Implementation**:
1. Check if document exists (if --force)
2. Delete existing document (vector store → metadata store)
3. Import new document
4. If step 3 fails, attempt to restore original document

**Rationale**:
- Prevents data corruption from partial overwrites
- Users get immediate feedback on failures
- Rollback is best-effort (may not always be possible)

**Alternatives Considered**:
- Optimistic locking: Too complex for this use case
- Two-phase commit: Over-engineering for local operations
- Always rollback: May hide underlying issues

### Decision 6: User Feedback Messaging

**Choice**: Distinct messages for overwrite vs new document
**Messages**:
- Overwrite: "Overwritten document: {name} (ID: {old_id} → {new_id})"
- New: "Created new document: {name} (ID: {id})"

**Rationale**:
- Users need to know what happened
- Important for batch operations to track changes
- Helps with auditing and debugging

**Alternatives Considered**:
- Same message for both: Doesn't distinguish between operations
- Technical details only: Not user-friendly
- Summary only: Loses important per-document information

## Risks / Trade-offs

### Risk: Data Loss from Accidental Overwrites
**Issue**: Users might accidentally overwrite documents with `--force` flag
**Mitigation**:
- Clear warning in help text: "WARNING: This will overwrite existing documents"
- Confirmation prompt for batch operations (could be added in future)
- Documentation emphasizes the destructive nature

### Risk: Vector Store Inconsistency
**Issue**: Partial failures could leave vector store and metadata store out of sync
**Mitigation**:
- Delete vector embeddings first
- Best-effort rollback on failures
- Clear error messages when inconsistencies detected

### Risk: Performance Impact on Large Documents
**Issue**: Deleting and re-adding large documents is expensive
**Mitigation**:
- Users can selectively use --force when needed
- No performance impact when flag not used
- Consider adding diff-based updates in future (out of scope)

### Risk: Race Conditions in Multi-Process Usage
**Issue**: Two processes might try to overwrite same document simultaneously
**Mitigation**:
- Current design assumes single-user/single-process usage
- Document in limitations that concurrent overwrites may cause issues
- Future enhancement could add locking mechanisms

### Risk: Rollback Complexity
**Issue**: Rolling back a failed overwrite is complex and may not always succeed
**Mitigation**:
- Treat rollback as best-effort, not guaranteed
- Log rollback attempts for debugging
- Provide clear error messages when rollback fails

## Migration Plan

**Implementation Order**:
1. Add `--force` flag to CLI ingest command
2. Implement document existence check in pipeline
3. Add cascade deletion logic (vector store → metadata store)
4. Implement rollback mechanism for failures
5. Update user feedback messages
6. Test with various scenarios

**Rollback Strategy**:
- CLI flag addition is non-destructive
- If issues arise, can deprecate flag or make it opt-in via config
- No database schema changes required
- No impact on existing ingest behavior (without --force flag)

## Open Questions

1. **Batch Confirmation**: Should we add a confirmation prompt for batch overwrite operations?
2. **Progress Tracking**: Should we show progress for deletion operations during overwrite?
3. **Statistics**: Should we track and display statistics about overwritten vs new documents?
4. **Rollback Reliability**: How robust should the rollback mechanism be?
5. **Future Enhancements**: Should we consider adding diff-based updates in the future?
