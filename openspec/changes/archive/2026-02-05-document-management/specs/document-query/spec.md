## ADDED Requirements

### Requirement: Query documents with pagination
The system SHALL provide a `memory doc query` command that displays documents with pagination support. The command MUST accept `--page` and `--page-size` parameters to control which documents are displayed.

#### Scenario: Query first page
- **WHEN** user runs `memory doc query --page 1 --page-size 10`
- **THEN** system displays up to 10 documents starting from the beginning of the result set

#### Scenario: Query specific page
- **WHEN** user runs `memory doc query --page 3 --page-size 20`
- **THEN** system displays documents 41-60 from the result set (if available)

#### Scenario: Query with default pagination
- **WHEN** user runs `memory doc query` without pagination parameters
- **THEN** system displays first page with default page size of 20 documents

### Requirement: Fuzzy search by document name
The system SHALL allow users to search for documents by name using a `--search` parameter. The search SHALL be case-insensitive and match substrings.

#### Scenario: Search by exact name
- **WHEN** user runs `memory doc query --search "README"`
- **THEN** system displays only documents whose name contains "README"

#### Scenario: Search by partial name
- **WHEN** user runs `memory doc query --search "read"`
- **THEN** system displays documents with names containing "read", "Read", "README", etc.

#### Scenario: Search case-insensitive
- **WHEN** user runs `memory doc query --search "API"`
- **THEN** system displays documents with names containing "api", "Api", "API", "ApI", etc.

#### Scenario: Search with no matches
- **WHEN** user runs `memory doc query --search "NonexistentDocument"`
- **THEN** system displays a message indicating no documents were found

### Requirement: Filter by repository
The system SHALL allow users to filter documents by repository using `--repository` parameter.

#### Scenario: Query documents in specific repository
- **WHEN** user runs `memory doc query --repository project-a`
- **THEN** system displays only documents belonging to repository "project-a"

#### Scenario: Query documents in default repository
- **WHEN** user runs `memory doc query` without `--repository`
- **THEN** system displays documents from the default repository

### Requirement: Sort query results
The system SHALL allow users to sort query results using `--sort` parameter with options: created_at, updated_at, name.

#### Scenario: Sort by created_at ascending
- **WHEN** user runs `memory doc query --sort created_at`
- **THEN** system displays documents sorted by creation date (oldest first)

#### Scenario: Sort by created_at descending
- **WHEN** user runs `memory doc query --sort created_at --desc`
- **THEN** system displays documents sorted by creation date (newest first)

#### Scenario: Sort by name alphabetically
- **WHEN** user runs `memory doc query --sort name`
- **THEN** system displays documents sorted alphabetically by name

#### Scenario: Sort by updated_at
- **WHEN** user runs `memory doc query --sort updated_at`
- **THEN** system displays documents sorted by last update date

### Requirement: Display document metadata
The system SHALL display the following metadata for each document in query results: ID, name, source path, chunk count, and created date.

#### Scenario: Display formatted table
- **WHEN** user runs `memory doc query`
- **THEN** system displays a formatted table with columns: ID, Name, Source Path, Chunks, Created

#### Scenario: Display JSON format
- **WHEN** user runs `memory doc query --json`
- **THEN** system displays results as JSON with fields: id, name, source_path, chunk_count, created_at

#### Scenario: Display with chunk count
- **WHEN** user runs `memory doc query`
- **THEN** system displays the number of chunks for each document

### Requirement: Combine multiple filters
The system SHALL allow users to combine search, repository filter, pagination, and sorting in a single command.

#### Scenario: Combine search and repository filter
- **WHEN** user runs `memory doc query --search "api" --repository project-a --page 1 --page-size 10 --sort name`
- **THEN** system displays documents from project-a repository whose names contain "api", sorted alphabetically, showing first 10 results

#### Scenario: Complex query with all options
- **WHEN** user runs `memory doc query --search "doc" --repository my-project --sort updated_at --desc --page 2 --page-size 15 --json`
- **THEN** system displays matching documents in JSON format, sorted by most recently updated, showing page 2 with 15 items per page

### Requirement: Handle empty repository
The system SHALL display an appropriate message when querying a repository with no documents.

#### Scenario: Query empty repository
- **WHEN** user runs `memory doc query --repository empty-repo`
- **THEN** system displays message: "No documents found in repository 'empty-repo'"

#### Scenario: Query empty result set
- **WHEN** user runs `memory doc query --search "nonexistent"`
- **THEN** system displays message: "No documents found matching search criteria"
