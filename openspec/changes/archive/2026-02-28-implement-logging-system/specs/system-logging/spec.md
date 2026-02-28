## ADDED Requirements

### Requirement: System logs SHALL be written to files
The system SHALL write all debug, info, warning, and error logs to files in addition to console output, enabling post-incident analysis and debugging.

#### Scenario: Log file creation on first write
- **WHEN** the application starts and logging is enabled
- **THEN** the system creates the log directory if it does not exist
- **AND** creates the log file for the current day

#### Scenario: Log messages are persisted
- **WHEN** the application logs a message at any level (debug, info, warning, error)
- **THEN** the message is written to both console and file
- **AND** includes timestamp, level, logger name, and message content

### Requirement: Log files SHALL rotate daily
The system SHALL automatically rotate log files daily to prevent unbounded disk usage.

#### Scenario: Daily log rotation
- **WHEN** a new day begins (midnight)
- **THEN** the current log file is closed
- **AND** a new log file is created for the current day
- **AND** old log files remain accessible with date suffix

#### Scenario: Old logs are cleaned up
- **WHEN** the number of retained log days exceeds the configured maximum
- **THEN** the oldest log files are automatically deleted
- **AND** only logs within the retention period remain

### Requirement: Log configuration is controllable
The system SHALL allow configuration of log level, output directory, and retention period through the configuration system.

#### Scenario: Configure log level
- **WHEN** the user sets `logging.level` in configuration
- **THEN** only messages at or above the configured level are logged

#### Scenario: Configure log directory
- **WHEN** the user sets `logging.log_dir` in configuration
- **THEN** all log files are written to the specified directory

#### Scenario: Configure retention period
- **WHEN** the user sets `logging.max_days` in configuration
- **THEN** log files older than the configured number of days are automatically deleted

### Requirement: Logging does not crash the application
The system SHALL handle logging errors gracefully without crashing the application.

#### Scenario: Log directory unwritable
- **WHEN** the log directory cannot be written to (permission denied, disk full)
- **THEN** the application logs a warning message
- **AND** continues running with console-only logging
