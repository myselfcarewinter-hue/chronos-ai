"""Custom exception hierarchy for Chronos AI."""

from typing import Any


class ChronosError(Exception):
    """Base exception for all Chronos AI errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(ChronosError):
    """Resource not found."""


class AuthenticationError(ChronosError):
    """Authentication failed."""


class AuthorizationError(ChronosError):
    """User lacks permission."""


class ValidationError(ChronosError):
    """Input validation failed."""


class GeminiServiceError(ChronosError):
    """Gemini API call failed."""


class CalendarServiceError(ChronosError):
    """Google Calendar operation failed."""


class AgentError(ChronosError):
    """AI agent processing failed."""
