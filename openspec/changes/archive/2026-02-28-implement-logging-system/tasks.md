## 1. Configuration

- [x] 1.1 Add logging configuration model to `src/memory/config/schema.py`
  - Add `LoggingConfig` with fields: level, log_dir, max_days, enable_file
  - Add `AuditLoggingConfig` with field: enable
  - Integrate into `AppConfig`
- [x] 1.2 Update configuration loading in `src/memory/config/loader.py` if needed

## 2. System Logging

- [x] 2.1 Update `src/memory/observability/logging.py` to support file output
  - Add `FileLoggerFactory` class for file-based logging
  - Modify `configure_logging()` to accept file output parameters
  - Add log directory creation with error handling
- [x] 2.2 Implement log rotation using `TimedRotatingFileHandler`
  - Configure daily rotation at midnight
  - Implement automatic cleanup of old log files based on max_days
- [x] 2.3 Add graceful error handling for file logging failures
  - Fallback to console-only logging if file writing fails
  - Log warning when falling back

## 3. CLI Audit Logging

- [x] 3.1 Add `get_audit_logger()` function to `src/memory/observability/logging.py`
  - Create separate logger for CLI audit logs
  - Use JSON Lines formatter
  - Configure with rotation
- [x] 3.2 Implement audit log record structure
  - Fields: timestamp, command, args, exit_code, duration_ms, user
  - Use ISO 8601 timestamp format
- [x] 3.3 Integrate audit logging into CLI entry point
  - Find CLI entry point (likely in `src/memory/__main__.py` or similar)
  - Add pre-execution and post-execution hooks
  - Record command start and completion

## 4. Testing

- [x] 4.1 Add unit tests for logging configuration
- [x] 4.2 Add unit tests for file logging functionality
- [x] 4.3 Add unit tests for audit logging
- [x] 4.4 Test log rotation behavior
- [x] 4.5 Test graceful degradation when log directory is unwritable
