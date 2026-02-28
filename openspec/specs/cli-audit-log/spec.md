# CLI Audit Logging

## Purpose

Record CLI command executions for audit trails and troubleshooting user operations.

## ADDED Requirements

### Requirement: CLI command executions SHALL be logged
The system SHALL log every CLI command execution with sufficient detail for auditing and troubleshooting.

#### Scenario: Log successful command execution
- **WHEN** a CLI command completes successfully (exit code 0)
- **THEN** the system logs an audit record containing:
  - timestamp (ISO 8601 format)
  - command name
  - arguments
  - exit code
  - execution duration in milliseconds

#### Scenario: Log failed command execution
- **WHEN** a CLI command fails (non-zero exit code)
- **THEN** the system logs an audit record with the same fields
- **AND** includes the exit code for later analysis

#### Scenario: Log command start
- **WHEN** a CLI command starts execution
- **THEN** the system logs an audit record with timestamp, command, and args
- **AND** does not include exit_code or duration (set to null)

### Requirement: CLI audit logs SHALL be persisted as JSON Lines
The system SHALL write audit logs in JSON Lines format for easy parsing and analysis.

#### Scenario: JSON Lines format
- **WHEN** an audit log entry is written
- **THEN** it is written as a single line of valid JSON
- **AND** each entry is separated by a newline character

### Requirement: CLI audit logs SHALL rotate daily
The system SHALL automatically rotate audit log files daily.

#### Scenario: Daily audit log rotation
- **WHEN** a new day begins (midnight)
- **THEN** the current audit log file is closed
- **AND** a new audit log file is created for the current day

### Requirement: CLI audit logging is configurable
The system SHALL allow enabling/disabling CLI audit logging through configuration.

#### Scenario: Disable audit logging
- **WHEN** the user sets `logging.audit.enable = false` in configuration
- **THEN** no audit log entries are written

#### Scenario: Enable audit logging
- **WHEN** the user sets `logging.audit.enable = true` (or default)
- **THEN** all CLI command executions are logged

### Requirement: Audit logging does not affect CLI performance
The system SHALL write audit logs with minimal overhead to avoid impacting CLI responsiveness.

#### Scenario: Non-blocking audit logging
- **WHEN** a CLI command completes
- **THEN** the audit log is written asynchronously or with buffering
- **AND** does not significantly increase command execution time
