"""
Centralized logging configuration for Shodh.

Provides structured JSON logging for production and readable console output for development.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional

from src.core.config import get_settings


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Output format:
    {"timestamp": "...", "level": "INFO", "logger": "src.api", "message": "...", "extra": {...}}
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add location info for errors
        if record.levelno >= logging.ERROR:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra fields passed via logger.info("msg", extra={...})
        standard_attrs = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
            'message', 'taskName'
        }
        extra = {k: v for k, v in record.__dict__.items() if k not in standard_attrs}
        if extra:
            log_data["extra"] = extra
        
        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """
    Colored, readable formatter for development console output.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Format: [TIME] LEVEL logger: message
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Shorten logger name for readability
        logger_name = record.name
        if logger_name.startswith("src."):
            logger_name = logger_name[4:]  # Remove "src." prefix
        
        formatted = f"{color}[{timestamp}] {record.levelname:8}{self.RESET} {logger_name}: {record.getMessage()}"
        
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        
        return formatted


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON format; else colored console
        log_file: Optional file path to write logs
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_output:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    root_logger.addHandler(console_handler)
    
    # File handler (always JSON for parsing)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
    
    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    
    root_logger.info(
        "Logging configured",
        extra={"level": level, "json_output": json_output, "log_file": log_file}
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Usage:
        from src.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Processing paper", extra={"paper_id": "2401.12345"})
    """
    return logging.getLogger(name)


# Convenience function for contextual logging
class LogContext:
    """
    Context manager for adding structured context to logs.
    
    Usage:
        with LogContext(paper_id="2401.12345", user_id="123"):
            logger.info("Processing paper")  # Includes paper_id, user_id
    """
    
    _context: Dict[str, Any] = {}
    
    def __init__(self, **kwargs):
        self.new_context = kwargs
        self.old_context = {}
    
    def __enter__(self):
        self.old_context = LogContext._context.copy()
        LogContext._context.update(self.new_context)
        return self
    
    def __exit__(self, *args):
        LogContext._context = self.old_context
    
    @classmethod
    def get_context(cls) -> Dict[str, Any]:
        return cls._context.copy()
