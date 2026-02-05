## ADDED Requirements

### Requirement: Delete document by ID
The system SHALL provide a `memory doc delete <document-id>` command that deletes a specific document and all its associated data (chunks and embeddings).

#### Scenario: Delete by UUID
- **WHEN** user runs `memory doc delete 12345678-1234-5678-1234-567812345678`
- **THEN** system deletes the document with that UUID and displays success message

#### Scenario: Delete by document name
- **WHEN** user runs `memory doc delete "README.md"` and only one document matches
- **THEN** system deletes the matching document and displays success message

#### Scenario: Delete with confirmation
- **WHEN** user runs `memory doc delete <document-id>` (without --force)
- **THEN** system prompts: "Are you sure you want to delete document '<document-name>'? This will remove the document, all chunks, and all embeddings. (y/N)"

#### Scenario: Delete with forced flag
- **WHEN** user runs `memory doc delete <document-id> --force`
- **THEN** system immediately deletes the document without confirmation prompt

### Requirement: Cascade delete all associated data
The system SHALL delete not only the document record but also all related chunks and embeddings in a single operation.

#### Scenario: Cascade delete removes document and chunks
- **WHEN** user deletes a document
- **THEN** system removes:
  - Document record from metadata store
  - All chunks associated with this document
  - All embeddings in vector store for this document's chunks

#### Scenario: Cascade delete from vector store
- **WHEN** user deletes a document
- **THEN** system calls `VectorStore.delete_by_document_id()` to remove all embeddings

#### Scenario: Cascade delete from metadata store
- **WHEN** user deletes a document
- **THEN** system calls `MetadataStore.delete_document()` to remove document and chunks

#### Scenario: Cascade delete with transaction
- **GIVEN** storage backend supports transactions
- **WHEN** user deletes a document
- **THEN** system uses transaction to ensure atomic deletion (all or nothing)

### Requirement: Delete multiple documents
The system SHALL allow users to delete multiple documents in a single command by specifying multiple document IDs.

#### Scenario: Delete multiple documents with confirmation
- **WHEN** user runs `memory doc delete <doc-id-1> <doc-id-2> <doc-id-3>`
- **THEN** system prompts: "Are you sure you want to delete 3 documents? This cannot be undone. (y/N)"

#### Scenario: Delete multiple documents with force
- **WHEN** user runs `memory doc delete <doc-id-1> <doc-id-2> --force`
- **THEN** system immediately deletes both documents without confirmation

#### Scenario: Delete multiple documents with mixed IDs
- **WHEN** user runs `memory doc delete 12345678-1234-5678-1234-567812345678 "README.md" --force`
- **THEN** system deletes both the document with UUID and the document named "README.md"

### Requirement: Repository-scoped deletion
The system SHALL ensure that deletion only affects documents in the specified repository when `--repository` is provided.

#### Scenario: Delete from specific repository
- **WHEN** user runs `memory doc delete <doc-id> --repository project-a`
- **THEN** system only deletes the document if it belongs to project-a

#### Scenario: Delete cross-repository attempt
- **WHEN** user runs `memory doc delete <doc-id> --repository project-a` but document belongs to project-b
- **THEN** system displays error: "Document not found in repository 'project-a'"

#### Scenario: Delete without repository flag
- **WHEN** user runs `memory doc delete <doc-id>` without --repository
- **THEN** system finds document in any repository and deletes it

### Requirement: Error handling for invalid or non-existent documents
The system SHALL provide clear error messages when attempting to delete documents that don't exist or have invalid IDs.

#### Scenario: Delete non-existent UUID
- **WHEN** user runs `memory doc delete 00000000-0000-0000-0000-000000000000`
- **THEN** system displays error: "Document not found"

#### Scenario: Delete with ambiguous name
- **WHEN** user runs `memory doc delete "readme"` and multiple documents match
- **THEN** system lists all matching documents and displays error: "Multiple documents match. Use UUID for unique deletion."

#### Scenario: Delete already deleted document
- **WHEN** user runs `memory doc delete <doc-id>` but document was already deleted
- **THEN** system displays error: "Document not found (may have been already deleted)"

#### Scenario: Delete with invalid UUID format
- **WHEN** user runs `memory doc delete "invalid-uuid"`
- **THEN** system displays error: "Invalid document ID format. Use UUID or exact document name."

### Requirement: Success and failure reporting
The system SHALL provide clear feedback on the success or failure of delete operations, including partial success scenarios.

#### Scenario: Successful deletion message
- **WHEN** user successfully deletes a document
- **THEN** system displays: "Successfully deleted document '<document-name>' (<chunk-count> chunks and <embedding-count> embeddings removed)"

#### Scenario: Partial success with multiple documents
- **GIVEN** user deletes 3 documents where 2 exist and 1 doesn't
- **WHEN** user runs `memory doc delete <doc-id-1> <doc-id-2> <doc-id-3> --force`
- **THEN** system displays:
  - "Successfully deleted 2 documents"
  - "Failed: Document <doc-id-3> not found"

#### Scenario: All deletions fail
- **GIVEN** user attempts to delete 3 documents that don't exist
- **WHEN** user runs `memory doc delete <doc-id-1> <doc-id-2> <doc-id-3> --force`
- **THEN** system displays: "Failed: No documents found"

#### Scenario: Rollback on failure
- **GIVEN** cascade delete fails halfway through
- **WHEN** user attempts to delete document
- **THEN** system rolls back any partial deletions and displays error: "Deletion failed. No changes were made."

### Requirement: Dry-run mode
The system SHALL support a `--dry-run` flag that shows what would be deleted without actually performing the deletion.

#### Scenario: Dry-run shows documents to delete
- **WHEN** user runs `memory doc delete <doc-id-1> <doc-id-2> --dry-run`
- **THEN** system displays what would be deleted:
  - "Would delete document 'README.md' (12 chunks, 12 embeddings)"
  - "Would delete document 'API.md' (45 chunks, 45 embeddings)"
  - "No changes will be made. Use --force to actually delete."

#### Scenario: Dry-run with non-existent document
- **WHEN** user runs `memory doc delete <non-existent-id> --dry-run`
- **THEN** system displays: "Document not found. Nothing to delete."

#### Scenario: Dry-run doesn't require confirmation
- **WHEN** user runs `memory doc delete <doc-id> --dry-run`
- **THEN** system displays the plan without prompting for confirmation
