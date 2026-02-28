# ingestion-progress Specification

## Purpose
TBD - created by archiving change add-ingestion-progress. Update Purpose after archive.
## Requirements
### Requirement: Batch import progress display

When ingesting multiple files (more than 1), the system SHALL display a progress indicator showing the current status.

#### Scenario: Multiple files show progress bar
- **WHEN** the user runs `memory ingest` with multiple files or a directory with multiple files
- **THEN** the system SHALL display a progress bar with percentage complete
- **AND** the progress bar SHALL show the current file being processed

#### Scenario: Progress updates after each file
- **WHEN** a file is successfully ingested
- **THEN** the progress bar SHALL advance to reflect the completed count
- **AND** the current file name SHALL be shown in the progress description

### Requirement: Single file import no progress bar

When ingesting a single file, the system SHALL NOT display a progress bar, maintaining clean output.

#### Scenario: Single file clean output
- **WHEN** the user runs `memory ingest` with exactly one file
- **THEN** the system SHALL NOT display a progress bar
- **AND** the existing concise output format SHALL be used

### Requirement: Progress bar completes on finish

When all files are processed, the progress bar SHALL show 100% complete.

#### Scenario: Progress completes successfully
- **WHEN** all files in the batch have been processed
- **THEN** the progress bar SHALL show 100% complete
- **AND** the final status message SHALL be displayed

#### Scenario: Progress bar closes on completion
- **WHEN** ingestion is complete (success or failure)
- **THEN** the progress bar SHALL be properly closed
- **AND** no progress artifacts SHALL remain in the output

### Requirement: Error handling during progress

When an error occurs during batch ingestion, the system SHALL handle the progress bar gracefully.

#### Scenario: Error does not leave progress artifacts
- **WHEN** an error occurs during file processing
- **THEN** the progress bar SHALL be closed properly
- **AND** the error message SHALL be displayed after the progress bar

