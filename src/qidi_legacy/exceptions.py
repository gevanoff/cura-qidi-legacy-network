class QidiError(Exception):
    """Base exception for legacy QIDI operations."""


class QidiConnectionError(QidiError):
    """Raised when the printer does not respond or disconnects."""


class QidiProtocolError(QidiError):
    """Raised when the printer returns a malformed or unexpected response."""


class QidiUploadError(QidiError):
    """Raised when a G-code upload fails."""
