"""Shared utility helpers for the backend."""

import uuid

from fastapi import HTTPException


def parse_uuid(value: str, name: str = "id") -> uuid.UUID:
    """Parse a string as a UUID, raising HTTP 400 on failure.

    Parameters
    ----------
    value : str
        The raw string that should represent a valid UUID.
    name : str, optional
        A human-readable label used in the error message (e.g. "board_id").

    Returns
    -------
    uuid.UUID

    Raises
    ------
    HTTPException
        400 Bad Request when *value* is not a valid UUID.
    """
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail=f"Invalid {name} format")
