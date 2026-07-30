from __future__ import annotations

from UM.Job import Job

from .config import PluginConfig
from .monitor_snapshot import MonitorSnapshot
from .protocol_lock import QIDI_PROTOCOL_LOCK
from .qidi_legacy.client import QidiLegacyClient


class QidiMonitorStatusJob(Job):
    """Fetch one read-only status snapshot without blocking Cura's UI thread."""

    def __init__(self, config: PluginConfig) -> None:
        super().__init__()
        self._config = config

    def run(self) -> None:
        try:
            with QIDI_PROTOCOL_LOCK:
                with QidiLegacyClient(
                    self._config.host,
                    port=self._config.port,
                    timeout=self._config.timeout,
                    retries=self._config.retries,
                ) as client:
                    client.connect()
                    status = client.status()
                    filename = None
                    if status.is_idle is False:
                        try:
                            filename = client.current_filename()
                        except Exception:
                            # Filename reporting varies across legacy firmware. A failed optional
                            # filename query must not discard an otherwise valid status snapshot.
                            filename = None
                    self.setResult(MonitorSnapshot.from_status(status, filename=filename))
        except Exception as exc:
            self.setError(exc)
