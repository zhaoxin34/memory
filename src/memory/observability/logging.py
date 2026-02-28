"""Structured logging configuration using structlog.

Why this exists:
- Provides consistent, structured logging across the system
- Enables easy filtering and analysis of logs
- Supports context injection for tracing operations
- Supports file output with rotation

How to use:
    from memory.observability.logging import get_logger

    logger = get_logger(__name__)
    logger.info("operation_started", operation="indexing", doc_count=10)

For audit logging:
    from memory.observability.logging import get_audit_logger

    audit = get_audit_logger()
    audit.record(command="memory ingest", args=["file.md"], exit_code=0, duration_ms=100)
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import structlog
from structlog.types import EventDict, Processor

from memory.config.schema import LoggingConfig


class FileLoggerFactory:
    """Factory for creating file-based loggers."""

    def __init__(self, log_file: Path, level: str = "INFO"):
        """Initialize file logger factory.

        Args:
            log_file: Path to the log file
            level: Log level
        """
        self.log_file = log_file
        self.level = getattr(logging, level.upper())

        # Ensure directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler with rotation
        self._handler = logging.FileHandler(self.log_file, encoding="utf-8")
        self._handler.setLevel(self.level)

        # Set formatter
        formatter = logging.Formatter("%(message)s")
        self._handler.setFormatter(formatter)

    def __call__(self, name: str) -> logging.Logger:
        """Create a logger that writes to file.

        Args:
            name: Logger name

        Returns:
            Logger instance
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.level)
        logger.addHandler(self._handler)
        logger.propagate = False
        return logger


class TimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Timed rotating file handler with automatic cleanup."""

    def __init__(self, filename: str, max_days: int = 30, **kwargs):
        """Initialize handler with max days for cleanup.

        Args:
            filename: Log file path
            max_days: Maximum number of days to retain logs
            **kwargs: Additional arguments for TimedRotatingFileHandler
        """
        super().__init__(filename, when="midnight", interval=1, **kwargs)
        self.max_days = max_days

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a record and check for cleanup."""
        super().emit(record)
        self._cleanup_old_files()

    def _cleanup_old_files(self) -> None:
        """Remove log files older than max_days."""
        if not self.stream:
            return

        base_path = self.baseFilename
        if not os.path.exists(base_path):
            return

        base_dir = os.path.dirname(base_path)
        base_name = os.path.basename(base_path)

        # Find and remove old log files
        cutoff_time = datetime.now(timezone.utc).timestamp() - (self.max_days * 86400)

        for filename in os.listdir(base_dir):
            if filename.startswith(base_name + "."):
                file_path = os.path.join(base_dir, filename)
                try:
                    if os.path.getmtime(file_path) < cutoff_time:
                        os.remove(file_path)
                except OSError:
                    pass


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log events."""
    event_dict["app"] = "memory"
    return event_dict


def configure_logging(
    level: str = "INFO",
    json_logs: bool = False,
    log_dir: Optional[Path] = None,
    max_days: int = 30,
    enable_file: bool = True,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: If True, output logs as JSON; otherwise use console format
        log_dir: Directory for log files (if None, file logging is disabled)
        max_days: Number of days to retain log files
        enable_file: Whether to enable file logging
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Build processor chain
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_app_context,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    # Determine logger factory
    if enable_file and log_dir:
        # Ensure log directory exists
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "system.log"

            # Get root logger and configure handlers
            root_logger = logging.getLogger()
            root_logger.setLevel(getattr(logging, level.upper()))

            # Remove existing file handlers to avoid duplicates
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    root_logger.removeHandler(handler)

            # Use rotating file handler for root logger
            file_handler = TimedRotatingFileHandler(
                str(log_file),
                max_days=max_days,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, level.upper()))

            # Add file handler to root logger
            root_logger.addHandler(file_handler)

            # Use standard library logger factory
            logger_factory = structlog.stdlib.LoggerFactory()

            # Update wrapper class to use standard library logging
            wrapper_class = structlog.make_filtering_bound_logger(
                getattr(logging, level.upper())
            )

            structlog.configure(
                processors=processors,
                wrapper_class=wrapper_class,
                context_class=dict,
                logger_factory=logger_factory,
                cache_logger_on_first_use=True,
            )

            # Also configure the root logger handler for console output
            if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root_logger.handlers):
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(logging.Formatter("%(message)s"))
                root_logger.addHandler(console_handler)

            return  # Early return after configuring
        except (OSError, PermissionError) as e:
            # Fallback to console-only if file logging fails
            logging.warning(f"Failed to enable file logging: {e}. Using console-only mode.")
            # Fall through to console-only mode

    # Console-only mode (default)
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Audit logger singleton
_audit_logger: Optional["AuditLogger"] = None


class AuditLogger:
    """CLI audit logger that writes JSON Lines to file."""

    def __init__(self, log_file: Path, max_days: int = 30):
        """Initialize audit logger.

        Args:
            log_file: Path to audit log file
            max_days: Number of days to retain logs
        """
        self.log_file = log_file
        self.max_days = max_days

        # Ensure directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating handler
        self._handler = TimedRotatingFileHandler(
            str(self.log_file),
            max_days=max_days,
            encoding="utf-8",
        )

    def record(
        self,
        command: str,
        args: list[str],
        exit_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        user: Optional[str] = None,
    ) -> None:
        """Record an audit log entry.

        Args:
            command: Command name
            args: Command arguments
            exit_code: Exit code (None for command start)
            duration_ms: Duration in milliseconds (None for command start)
            user: Username
        """
        import getpass

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "args": args,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "user": user or getpass.getuser(),
        }

        # Write as JSON line
        try:
            self._handler.emit(
                logging.makeLogRecord(
                    {
                        "levelno": logging.INFO,
                        "msg": json.dumps(entry),
                        "name": "audit",
                    }
                )
            )
        except Exception:
            # Silently fail - audit logging should not crash the app
            pass


def get_audit_logger(
    log_dir: Optional[Path] = None,
    max_days: int = 30,
) -> AuditLogger:
    """Get or create the audit logger instance.

    Args:
        log_dir: Directory for audit log files
        max_days: Number of days to retain logs

    Returns:
        AuditLogger instance
    """
    global _audit_logger

    if _audit_logger is None:
        if log_dir is None:
            log_dir = Path.home() / ".memory" / "logs"

        log_file = log_dir / "cli-audit.log"
        _audit_logger = AuditLogger(log_file, max_days)

    return _audit_logger


def configure_from_config(config: LoggingConfig) -> None:
    """Configure logging from a LoggingConfig object.

    Args:
        config: Logging configuration
    """
    configure_logging(
        level=config.level.value,
        log_dir=config.log_dir if config.enable_file else None,
        max_days=config.max_days,
        enable_file=config.enable_file,
    )
