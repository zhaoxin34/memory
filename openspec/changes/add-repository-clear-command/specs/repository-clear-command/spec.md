## ADDED Requirements

### Requirement: CLI clear command removes all documents from repository
The system SHALL provide a `memory repo clear <repository-name>` command that removes all documents, chunks, and embeddings from the specified repository while preserving the repository configuration.

#### Scenario: Clear repository with existing documents
- **WHEN** user executes `memory repo clear my-repo` where the repository contains documents
- **THEN** system SHALL remove all documents, chunks, and embeddings from the repository
- **AND** system SHALL preserve the repository metadata and configuration
- **AND** system SHALL display the count of documents deleted
- **AND** system SHALL prompt for user confirmation before proceeding

#### Scenario: Clear repository with no documents
- **WHEN** user executes `memory repo clear empty-repo` where the repository contains no documents
- **THEN** system SHALL display a message indicating no documents were found
- **AND** system SHALL exit with success status

#### Scenario: Clear non-existent repository
- **WHEN** user executes `memory repo clear non-existent-repo`
- **THEN** system SHALL display an error message: "Repository 'non-existent-repo' not found"
- **AND** system SHALL exit with non-zero status code
- **AND** no changes SHALL be made to any repository

### Requirement: Dry-run mode previews deletion without making changes
The system SHALL provide a `--dry-run` flag that shows what would be deleted without actually performing the deletion.

#### Scenario: Dry-run shows document count
- **WHEN** user executes `memory repo clear my-repo --dry-run` on a repository with 5 documents
- **THEN** system SHALL display: "DRY RUN: Would clear 5 documents from 'my-repo'"
- **AND** system SHALL display: "No changes were made."
- **AND** system SHALL exit with success status
- **AND** no documents SHALL be deleted

#### Scenario: Dry-run skips confirmation
- **WHEN** user executes `memory repo clear my-repo --dry-run`
- **THEN** system SHALL NOT prompt for confirmation
- **AND** system SHALL complete immediately

### Requirement: Confirmation prompt prevents accidental deletion
The system SHALL require explicit user confirmation by default to prevent accidental data loss.

#### Scenario: User confirms deletion
- **WHEN** user executes `memory repo clear my-repo` and system displays confirmation prompt
- **AND** user responds with "yes"
- **THEN** system SHALL proceed with deletion
- **AND** system SHALL display success message

#### Scenario: User cancels deletion
- **WHEN** user executes `memory repo clear my-repo` and system displays confirmation prompt
- **AND** user responds with "no"
- **THEN** system SHALL display: "Operation cancelled."
- **AND** system SHALL exit without making changes
- **AND** all documents SHALL remain in the repository

### Requirement: Yes flag bypasses confirmation prompt
The system SHALL provide a `--yes` or `-y` flag that skips the confirmation prompt for automation and scripting.

#### Scenario: Yes flag skips confirmation
- **WHEN** user executes `memory repo clear my-repo --yes`
- **THEN** system SHALL NOT prompt for confirmation
- **AND** system SHALL proceed directly with deletion
- **AND** system SHALL display success message

### Requirement: Clear operation returns deletion count
The system SHALL return the count of documents deleted as part of the success output.

#### Scenario: Display deletion count
- **WHEN** system completes clearing a repository that contained 10 documents
- **THEN** system SHALL display: "✓ Successfully cleared 10 documents"
- **AND** system SHALL display: "  Repository 'my-repo' is now empty"

### Requirement: Repository metadata preserved after clear
The system SHALL preserve all repository configuration and metadata when clearing documents.

#### Scenario: Repository remains usable after clear
- **WHEN** user clears a repository and then lists repositories
- **THEN** system SHALL show the repository in the list
- **AND** user SHALL be able to ingest new documents into the cleared repository
- **AND** repository configuration SHALL remain unchanged

#### Scenario: Repository info unchanged after clear
- **WHEN** user clears a repository and then views repository info
- **THEN** system SHALL display the same repository name and metadata as before
- **AND** document count SHALL be zero
- **AND** repository ID SHALL remain the same

### Requirement: Storage layer deletes all repository data
The system SHALL implement delete_by_repository() methods in both MetadataStore and VectorStore to remove all associated data.

#### Scenario: MetadataStore deletes all documents
- **WHEN** MetadataStore.delete_by_repository() is called with a repository ID
- **THEN** system SHALL delete all documents with that repository_id
- **AND** system SHALL cascade delete all chunks associated with those documents
- **AND** system SHALL cascade delete all embeddings associated with those chunks
- **AND** system SHALL return the count of documents deleted

#### Scenario: VectorStore deletes all embeddings
- **WHEN** VectorStore.delete_by_repository() is called with a repository ID
- **THEN** system SHALL delete all embeddings with that repository_id
- **AND** system SHALL remove or drop the collection for that repository
- **AND** system SHALL return the count of embeddings deleted

### Requirement: Atomic operation ensures consistency
The system SHALL perform the clear operation atomically to ensure consistency between MetadataStore and VectorStore.

#### Scenario: Failure during clear operation
- **WHEN** error occurs during clear operation after some deletions
- **THEN** system SHALL rollback any changes made
- **AND** system SHALL leave the repository in its original state
- **AND** system SHALL display an error message
- **AND** system SHALL exit with non-zero status code

#### Scenario: Partial deletion prevented
- **WHEN** clear operation is in progress
- **THEN** system SHALL prevent other operations on the repository
- **AND** system SHALL maintain consistency between metadata and vector stores

### Requirement: Error handling for storage failures
The system SHALL handle storage errors gracefully with appropriate error messages.

#### Scenario: Storage error during deletion
- **WHEN** storage backend returns an error during deletion
- **THEN** system SHALL catch the StorageError
- **AND** system SHALL display: "✗ Error clearing repository: <error details>"
- **AND** system SHALL exit with non-zero status code

### Requirement: Integration with existing repository commands
The system SHALL integrate seamlessly with existing repository management commands.

#### Scenario: Clear command works with repository listing
- **WHEN** user clears a repository and then lists all repositories
- **THEN** system SHALL include the cleared repository in the list
- **AND** repository SHALL be marked as empty (zero documents)

#### Scenario: Clear command works with repository info
- **WHEN** user clears a repository and then runs repository info
- **THEN** system SHALL show repository details with document count of zero
- **AND** all other repository metadata SHALL remain intact
