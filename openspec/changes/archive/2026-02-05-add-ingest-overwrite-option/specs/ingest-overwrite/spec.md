# Ingest Overwrite Specification

## ADDED Requirements

### Requirement: Ingest command supports force overwrite option
The `ingest` command SHALL provide a `--force` option that enables overwriting existing documents with the same source path.

#### Scenario: Overwrite existing document
- **WHEN** user runs `memory ingest <path> --force`
- **AND** a document with the same source path already exists in the repository
- **THEN** system SHALL delete the existing document, all its chunks, and all associated embeddings
- **AND** system SHALL import the new document with updated content
- **AND** system SHALL display message indicating document was overwritten

#### Scenario: Overwrite with repository specification
- **WHEN** user runs `memory ingest <path> --force --repository <name>`
- **AND** a document with the same source path exists in the specified repository
- **THEN** system SHALL delete the existing document only from that repository
- **AND** system SHALL import the new document to the specified repository
- **AND** system SHALL display repository name in overwrite confirmation

#### Scenario: Force flag with non-existent document
- **WHEN** user runs `memory ingest <path> --force`
- **AND** no document with the same source path exists
- **THEN** system SHALL import the document as a new document
- **AND** system SHALL display message indicating document was created (not overwritten)

#### Scenario: Batch overwrite with recursive flag
- **WHEN** user runs `memory ingest <directory> --recursive --force`
- **AND** multiple documents already exist in the repository
- **THEN** system SHALL overwrite all existing documents that match source paths
- **AND** system SHALL create new documents for files that don't exist
- **AND** system SHALL display summary of overwritten vs newly created documents

### Requirement: Cascade deletion of associated data
When overwriting a document, the system SHALL delete all associated data.

#### Scenario: Delete chunks when overwriting
- **WHEN** a document is overwritten
- **THEN** system SHALL delete all chunks associated with the old document
- **AND** no orphaned chunks remain in the metadata store

#### Scenario: Delete embeddings when overwriting
- **WHEN** a document is overwritten
- **THEN** system SHALL delete all embeddings associated with the old document's chunks
- **AND** vector store collections remain clean with no dangling references

#### Scenario: Rollback on partial failure
- **WHEN** overwriting a document fails partway through the process
- **THEN** system SHALL attempt to rollback to the original document state
- **AND** system SHALL display error message indicating the failure
- **AND** user may need to manually resolve the issue

### Requirement: Clear feedback for overwrite operations
The system SHALL provide clear, user-friendly feedback about overwrite operations.

#### Scenario: Display overwrite confirmation
- **WHEN** a document is successfully overwritten
- **THEN** system SHALL display message: "Overwritten document: <name> (previous ID: <id>, new ID: <id>)"
- **AND** message SHALL indicate the number of chunks deleted and recreated

#### Scenario: Display new document creation
- **WHEN** a document is imported as new (no existing document)
- **THEN** system SHALL display message: "Created new document: <name> (ID: <id>)"
- **AND** message SHALL indicate the number of chunks created

#### Scenario: Display batch operation summary
- **WHEN** batch ingesting with --force flag completes
- **THEN** system SHALL display summary:
  - Total files processed
  - Documents overwritten
  - Documents newly created
  - Documents skipped (if any)
  - Total errors (if any)
