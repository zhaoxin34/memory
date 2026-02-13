## ADDED Requirements

### Requirement: Search output format selection

The search command SHALL support an `--output` parameter to select the output format.

#### Scenario: Default output format
- **WHEN** user runs `memory search "query"` without `--output`
- **THEN** the system SHALL use `text` format as default

#### Scenario: JSON output format
- **WHEN** user runs `memory search "query" --output json`
- **THEN** the system SHALL output results in valid JSON format

#### Scenario: Markdown output format
- **WHEN** user runs `memory search "query" --output markdown`
- **THEN** the system SHALL output results in Markdown table format

#### Scenario: Text output format explicitly
- **WHEN** user runs `memory search "query" --output text`
- **THEN** the system SHALL output results in plain text format

### Requirement: JSON output structure

The JSON output SHALL contain complete search result information for programmatic use.

#### Scenario: JSON contains query metadata
- **WHEN** user selects JSON output format
- **THEN** the output SHALL include `query`, `total_results`, and `results` fields

#### Scenario: JSON result contains all fields
- **WHEN** user selects JSON output format
- **THEN** each result SHALL include: `score`, `document_id`, `document_title`, `chunk_index`, `content`, `source_path`

#### Scenario: JSON handles special characters
- **WHEN** content contains special characters (quotes, newlines)
- **THEN** the JSON SHALL be properly escaped and valid

### Requirement: Markdown output structure

The Markdown output SHALL be human-readable and easy to copy to documentation.

#### Scenario: Markdown shows table
- **WHEN** user selects Markdown output format
- **THEN** the output SHALL include a table with columns: #, Score, Document, Content

#### Scenario: Markdown truncates long content
- **WHEN** content exceeds reasonable length
- **THEN** the Markdown table SHALL truncate with `...` indicator

#### Scenario: Markdown includes source links
- **WHEN** user selects Markdown output format
- **THEN** the output SHALL include a "Sources" section with file links

### Requirement: Output format parameter

The `--output` parameter SHALL be case-insensitive and validated.

#### Scenario: Case insensitive format names
- **WHEN** user runs `memory search "query" --output JSON`
- **THEN** the system SHALL accept the format (case insensitive)

#### Scenario: Invalid format rejected
- **WHEN** user runs `memory search "query" --output invalid`
- **THEN** the system SHALL show an error with valid format options
