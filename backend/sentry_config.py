"""Sentry error tracking configuration."""

import os
from typing import Any, Dict, Optional


def init_sentry() -> bool:
    """
    Initialize Sentry error tracking.

    Returns:
        True if Sentry was initialized, False if skipped.
    """
    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        print("Sentry DSN not configured, error tracking disabled")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.httpx import HttpxIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
                HttpxIntegration(),
            ],
            # Performance monitoring
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            # Profiling
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
            # Environment
            environment=os.getenv("ENVIRONMENT", "development"),
            release=os.getenv("APP_VERSION", "unknown"),
            # Server name
            server_name=os.getenv("SERVER_NAME", "llm-council"),
            # Scrub sensitive data
            before_send=_scrub_sensitive_data,
            # Don't send PII
            send_default_pii=False,
        )

        print(f"Sentry initialized for environment: {os.getenv('ENVIRONMENT', 'development')}")
        return True

    except ImportError:
        print("Sentry SDK not installed, run: uv add sentry-sdk[fastapi]")
        return False
    except Exception as e:
        print(f"Failed to initialize Sentry: {e}")
        return False


def _scrub_sensitive_data(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Scrub sensitive data from Sentry events before sending.

    Args:
        event: The Sentry event
        hint: Additional context about the event

    Returns:
        The scrubbed event or None to drop it
    """
    # Scrub Authorization headers
    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        sensitive_headers = ["Authorization", "X-Api-Key", "Cookie"]
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[REDACTED]"

    # Scrub API keys from body
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, str):
            # Simple string replacement for common patterns
            import re
            data = re.sub(r'"api_key"\s*:\s*"[^"]*"', '"api_key": "[REDACTED]"', data)
            data = re.sub(r'"password"\s*:\s*"[^"]*"', '"password": "[REDACTED]"', data)
            event["request"]["data"] = data

    # Scrub environment variables from extra context
    if "extra" in event:
        for key in list(event["extra"].keys()):
            if any(sensitive in key.lower() for sensitive in ["key", "secret", "password", "token"]):
                event["extra"][key] = "[REDACTED]"

    return event


def capture_exception(error: Exception, **context) -> Optional[str]:
    """
    Capture an exception to Sentry with additional context.

    Args:
        error: The exception to capture
        **context: Additional context to attach

    Returns:
        The Sentry event ID or None if not sent
    """
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)

            return sentry_sdk.capture_exception(error)
    except ImportError:
        return None


def set_user(user_id: str, email: Optional[str] = None, **extra) -> None:
    """
    Set the current user for Sentry context.

    Args:
        user_id: User identifier
        email: Optional user email
        **extra: Additional user properties
    """
    try:
        import sentry_sdk

        user_data = {"id": user_id}
        if email:
            user_data["email"] = email
        user_data.update(extra)

        sentry_sdk.set_user(user_data)
    except ImportError:
        pass


def set_context(name: str, data: Dict[str, Any]) -> None:
    """
    Set additional context for Sentry events.

    Args:
        name: Context name (e.g., "conversation", "model")
        data: Context data
    """
    try:
        import sentry_sdk
        sentry_sdk.set_context(name, data)
    except ImportError:
        pass


def add_breadcrumb(message: str, category: str = "default", level: str = "info", **data) -> None:
    """
    Add a breadcrumb for debugging.

    Args:
        message: Breadcrumb message
        category: Category (e.g., "api", "user", "model")
        level: Level (debug, info, warning, error)
        **data: Additional data
    """
    try:
        import sentry_sdk
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data,
        )
    except ImportError:
        pass
