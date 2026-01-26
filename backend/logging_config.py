"""Structured logging configuration for LLM Council."""

import logging
import sys
import os
from typing import Any

import structlog


def setup_logging(
    level: str = "INFO",
    json_format: bool = None,
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON format (auto-detected from environment)
    """
    # Auto-detect JSON format for production
    if json_format is None:
        json_format = os.getenv("LOG_FORMAT", "").lower() == "json"

    # Configure structlog processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_format:
        # Production: JSON format
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colored console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def bind_request_context(
    request_id: str,
    user_id: str = None,
    conversation_id: str = None,
    **extra: Any,
) -> None:
    """Bind request context for all subsequent log calls."""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        user_id=user_id,
        conversation_id=conversation_id,
        **extra,
    )


def clear_request_context() -> None:
    """Clear the current request context."""
    structlog.contextvars.clear_contextvars()


def redact_sensitive(data: dict, keys: list = None) -> dict:
    """
    Redact sensitive values from a dictionary for safe logging.

    Args:
        data: Dictionary to redact
        keys: List of key patterns to redact (case-insensitive partial match)

    Returns:
        Dictionary with sensitive values replaced by [REDACTED:key]
    """
    if keys is None:
        keys = ['api_key', 'apikey', 'password', 'token', 'secret', 'authorization', 'key']

    if not isinstance(data, dict):
        return data

    result = {}
    for k, v in data.items():
        if any(sensitive in k.lower() for sensitive in keys):
            result[k] = f"[REDACTED:{k}]"
        elif isinstance(v, dict):
            result[k] = redact_sensitive(v, keys)
        elif isinstance(v, list):
            result[k] = [redact_sensitive(item, keys) if isinstance(item, dict) else item for item in v]
        else:
            result[k] = v
    return result
