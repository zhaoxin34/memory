# Chunk Command Specification

## ADDED Requirements

### Requirement: Chunk command displays document chunking results
The CLI SHALL provide a `chunk` command that analyzes and displays how documents are divided into semantic chunks.

#### Scenario: Analyze imported document by ID
- **WHEN** user runs `memory chunk <document-id>`
- **THEN** system SHALL retrieve the document content and display all chunks with indices, sizes, and content preview

#### Scenario: Analyze document by name
- **WHEN** user runs `memory chunk <document-name>` and multiple documents match
- **THEN** system SHALL display an error message listing all matching documents with their IDs
- **AND** user MUST use document ID for unambiguous identification

#### Scenario: Analyze new document from file path
- **WHEN** user runs `memory chunk <path-to-file>`
- **THEN** system SHALL read the file, chunk it, and display results without importing to repository

#### Scenario: Chunk command shows comprehensive statistics
- **WHEN** chunk analysis completes
- **THEN** system SHALL display:
  - Total number of chunks
  - Average chunk size
  - Distribution of chunk types (heading, paragraph, code, list, etc.)
  - Size range (min/max)

### Requirement: Chunk command supports configurable chunking parameters
The `chunk` command SHALL accept parameters to override default chunking behavior.

#### Scenario: Custom chunk size
- **WHEN** user runs `memory chunk <doc> --size 1500`
- **THEN** system SHALL create chunks with target size of 1500 characters

#### Scenario: Custom chunk overlap
- **WHEN** user runs `memory chunk <doc> --overlap 200`
- **THEN** system SHALL create overlapping chunks with 200 character overlap

#### Scenario: Combined custom parameters
- **WHEN** user runs `memory chunk <doc> --size 1000 --overlap 100`
- **THEN** system SHALL apply both parameters and show affected chunk boundaries

#### Scenario: Test mode for parameter experimentation
- **WHEN** user runs `memory chunk <doc> --test`
- **THEN** system SHALL create a temporary chunking configuration and display results without permanent effects

### Requirement: Chunk command supports multiple output formats
The `chunk` command SHALL provide flexible output options for different use cases.

#### Scenario: Default table output
- **WHEN** user runs `memory chunk <doc>` without additional flags
- **THEN** system SHALL display a formatted table with columns:
  - Chunk Index
  - Type
  - Size (chars)
  - Character Range
  - Content Preview (first 100 chars)

#### Scenario: JSON output for automation
- **WHEN** user runs `memory chunk <doc> --json`
- **THEN** system SHALL output machine-readable JSON containing:
  - Document metadata
  - Array of chunks with all properties
  - Summary statistics

#### Scenario: Verbose output for debugging
- **WHEN** user runs `memory chunk <doc> --verbose`
- **THEN** system SHALL display additional details:
  - Full chunk content
  - Character position mapping
  - Semantic chunking decisions
  - Markdown structure information

### Requirement: Chunk command handles different document types
The `chunk` command SHALL intelligently process various input formats.

#### Scenario: Markdown documents
- **WHEN** user analyzes a .md file
- **THEN** system SHALL respect Markdown structure:
  - Headings create semantic boundaries
  - Code blocks are kept intact
  - Lists are preserved as units
  - Tables are identified and processed appropriately

#### Scenario: Plain text documents
- **WHEN** user analyzes a .txt file
- **THEN** system SHALL fall back to standard paragraph-based chunking

#### Scenario: Multiple files in directory
- **WHEN** user runs `memory chunk <directory> --recursive`
- **THEN** system SHALL process all text files and display results for each

### Requirement: Chunk command integrates with repository system
The `chunk` command SHALL work seamlessly with the repository infrastructure.

#### Scenario: Repository-scoped chunk analysis
- **WHEN** user runs `memory chunk <doc-id> --repository <repo-name>`
- **THEN** system SHALL use the specified repository's configuration and collection

#### Scenario: Display repository information
- **WHEN** chunk analysis completes for repository document
- **THEN** system SHALL show:
  - Repository name
  - Document ID
  - Last ingestion timestamp
  - Current chunking configuration

### Requirement: Chunk command provides error handling and validation
The `chunk` command SHALL gracefully handle error conditions.

#### Scenario: Document not found
- **WHEN** user specifies non-existent document ID
- **THEN** system SHALL display clear error message: "Document '<id>' not found in repository '<name>'"

#### Scenario: Invalid file path
- **WHEN** user provides path to non-existent file
- **THEN** system SHALL display error: "File not found: <path>"

#### Scenario: Non-text file
- **WHEN** user analyzes a binary file (e.g., image, PDF)
- **THEN** system SHALL display warning and skip the file

#### Scenario: Empty document
- **WHEN** user analyzes empty document or file
- **THEN** system SHALL display message: "Document is empty, no chunks created"
