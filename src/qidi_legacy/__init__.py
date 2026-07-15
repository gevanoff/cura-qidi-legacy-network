"""Legacy QIDI network protocol support."""

from .client import QidiLegacyClient
from .exceptions import QidiConnectionError, QidiProtocolError, QidiUploadError
from .models import HandshakeInfo, PrinterStatus

__all__ = [
    "HandshakeInfo",
    "PrinterStatus",
    "QidiConnectionError",
    "QidiLegacyClient",
    "QidiProtocolError",
    "QidiUploadError",
]
