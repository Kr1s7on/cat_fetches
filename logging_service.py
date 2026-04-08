"""
Structured logging service for production observability and AWS CloudWatch integration.
"""

import json
import logging
import sys
from typing import Dict, Any
from datetime import datetime

from config import settings


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging compatible with AWS CloudWatch."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields from the record
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add environment context
        log_data["environment"] = settings.app_env

        return json.dumps(log_data, separators=(',', ':'))


def setup_logging() -> logging.Logger:
    """
    Set up structured logging for the application.

    Returns:
        Configured logger instance
    """
    # Create root logger
    logger = logging.getLogger("cat_fetches")

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Set logging level based on environment
    if settings.app_env == "production":
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    # Create handler for stdout (works with AWS CloudWatch)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    logger.addHandler(handler)

    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False

    return logger


def log_error(logger: logging.Logger, message: str, error_id: str, **kwargs) -> None:
    """
    Log error with structured data.

    Args:
        logger: Logger instance
        message: Error message
        error_id: Unique error identifier for monitoring
        **kwargs: Additional structured data
    """
    extra_data = {"error_id": error_id, **kwargs}
    logger.error(message, extra={"extra_data": extra_data})


def log_warning(logger: logging.Logger, message: str, warning_id: str, **kwargs) -> None:
    """
    Log warning with structured data.

    Args:
        logger: Logger instance
        message: Warning message
        warning_id: Unique warning identifier for monitoring
        **kwargs: Additional structured data
    """
    extra_data = {"warning_id": warning_id, **kwargs}
    logger.warning(message, extra={"extra_data": extra_data})


def log_info(logger: logging.Logger, message: str, **kwargs) -> None:
    """
    Log info with structured data.

    Args:
        logger: Logger instance
        message: Info message
        **kwargs: Additional structured data
    """
    if kwargs:
        extra_data = kwargs
        logger.info(message, extra={"extra_data": extra_data})
    else:
        logger.info(message)


# Error ID constants for consistent monitoring
class ErrorIds:
    """Error ID constants for monitoring and alerting."""

    # News Service Errors
    NEWS_API_HTTP_ERROR = "NEWS_001"
    NEWS_API_TIMEOUT = "NEWS_002"
    NEWS_API_CONNECTION_ERROR = "NEWS_003"
    NEWS_API_SSL_ERROR = "NEWS_004"
    NEWS_API_AUTH_ERROR = "NEWS_005"
    NEWS_API_RATE_LIMIT = "NEWS_006"

    # Article Processing Errors
    ARTICLE_PARSE_FAILED = "NEWS_007"
    ARTICLE_VALIDATION_FAILED = "NEWS_008"
    NO_VALID_ARTICLES = "NEWS_009"

    # Configuration Errors
    CONFIG_MISSING_ENV_VAR = "CONFIG_001"
    CONFIG_INVALID_PORT = "CONFIG_002"
    CONFIG_LOAD_FAILED = "CONFIG_003"

    # Input Validation Errors
    INPUT_INVALID_TOPIC = "INPUT_001"
    INPUT_TOPIC_TOO_LONG = "INPUT_002"
    INPUT_EMPTY_TOPIC = "INPUT_003"


# Initialize logger for use across the application
logger = setup_logging()