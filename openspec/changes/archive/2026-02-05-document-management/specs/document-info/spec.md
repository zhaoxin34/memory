## ADDED Requirements

### Requirement: Display document details by ID
The system SHALL provide a `memory doc info <document-id>` command that displays detailed information about a specific document identified by its UUID or name.

#### Scenario: Info by UUID
- **WHEN** user runs `memory doc info 12345678-1234-5678-1234-567812345678`
- **THEN** system displays complete information for the document with that UUID

#### Scenario: Info by document name
- **WHEN** user runs `memory doc info "README.md"`
- **THEN** system displays information for the document named "README.md" (if unique)

#### Scenario: Info with non-existent UUID
- **WHEN** user runs `memory doc info 00000000-0000-0000-0000-000000000000`
- **THEN** system displays error: "Document not found"

#### Scenario: Info with ambiguous name
- **WHEN** user runs `memory doc info "readme"` and multiple documents match
- **THEN** system lists all matching documents and prompts user to use UUID instead

### Requirement: Display document metadata
The system SHALL display the following metadata: ID, name, document type, source path, repository ID, created timestamp, updated timestamp, and file size.

#### Scenario: Display all metadata fields
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays:
  - ID: document UUID
  - Name: document name
  - Type: document type (e.g., TEXT, MARKDOWN)
  - Source Path: file path
  - Repository: repository name
  - Created: timestamp
  - Updated: timestamp
  - File Size: size in bytes

#### Scenario: Display repository information
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays the repository name and ID that this document belongs to

### Requirement: Display content preview
The system SHALL display a preview of the document content (first N characters, default 500) to give users a sense of the document's content.

#### Scenario: Display content preview
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays the first 500 characters of the document content

#### Scenario: Display full content with flag
- **WHEN** user runs `memory doc info <document-id> --full`
- **THEN** system displays the complete document content

#### Scenario: Display truncated preview for long documents
- **GIVEN** a document with content longer than 500 characters
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays first 500 characters followed by "... (truncated)"

#### Scenario: Display "no preview" for binary documents
- **GIVEN** a binary document (e.g., PDF, image)
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays "Content preview not available for binary documents"

### Requirement: Display chunk statistics
The system SHALL display statistics about the chunks created from this document: total chunk count, average chunk size, size distribution.

#### Scenario: Display chunk statistics
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays:
  - Total Chunks: number of chunks
  - Average Chunk Size: average number of characters per chunk
  - Chunk Size Range: min-max characters

#### Scenario: Display chunk distribution
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays how chunks are distributed (e.g., "Small: 3, Medium: 8, Large: 2")

#### Scenario: Display for document with no chunks
- **GIVEN** a document that has not been processed into chunks yet
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays "No chunks found for this document"

### Requirement: Display associated repository
The system SHALL show which repository the document belongs to and allow optional repository filter.

#### Scenario: Display repository name
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays the repository name and ID

#### Scenario: Info with repository context
- **WHEN** user runs `memory doc info <document-id> --repository project-a`
- **THEN** system confirms the document belongs to project-a and displays its information

#### Scenario: Cross-repository document lookup
- **WHEN** user runs `memory doc info <document-id>` and document exists in repository other than default
- **THEN** system still displays document information correctly (repository filter not required for info command)

### Requirement: Output format options
The system SHALL support both human-readable table format and JSON format.

#### Scenario: Display as formatted table
- **WHEN** user runs `memory doc info <document-id>`
- **THEN** system displays information in a human-readable format with sections and labels

#### Scenario: Display as JSON
- **WHEN** user runs `memory doc info <document-id> --json`
- **THEN** system displays information as JSON with fields:
  - id, name, type, source_path, repository_id
  - created_at, updated_at, file_size
  - content_preview (truncated)
  - chunk_stats (count, avg_size, distribution)

#### Scenario: JSON includes all metadata
- **WHEN** user runs `memory doc info <document-id> --json`
- **THEN** JSON output contains all metadata fields and statistics

### Requirement: Error handling for invalid document IDs
The system SHALL provide clear error messages when a document ID is invalid or document doesn't exist.

#### Scenario: Invalid UUID format
- **WHEN** user runs `memory doc info "not-a-uuid"`
- **THEN** system displays error: "Invalid document ID format. Use UUID or document name."

#### Scenario: Document not found in specified repository
- **WHEN** user runs `memory doc info <document-id> --repository project-a` but document exists in project-b
- **THEN** system displays error: "Document not found in repository 'project-a'"

#### Scenario: Document deleted but ID cached
- **WHEN** user runs `memory doc info <document-id>` but document was deleted
- **THEN** system displays error: "Document not found (may have been deleted)"
