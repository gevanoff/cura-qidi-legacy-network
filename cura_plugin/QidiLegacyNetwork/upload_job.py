from __future__ import annotations

from pathlib import Path

from UM.Job import Job

from .config import PluginConfig
from .qidi_legacy.client import QidiLegacyClient


class QidiUploadJob(Job):
    def __init__(
        self,
        local_path: str | Path,
        remote_filename: str,
        config: PluginConfig,
        *,
        start_after_upload: bool,
    ) -> None:
        super().__init__()
        self._local_path = Path(local_path)
        self._remote_filename = remote_filename
        self._config = config
        self._start_after_upload = start_after_upload

    def _on_progress(self, done: int, total: int) -> None:
        percent = 100 if total <= 0 else min(100, max(0, int(done * 100 / total)))
        self.progress.emit(self, percent)

    def run(self) -> None:
        try:
            with QidiLegacyClient(
                self._config.host,
                port=self._config.port,
                timeout=self._config.timeout,
                retries=self._config.retries,
            ) as client:
                client.connect()
                remote = client.upload_file(
                    self._local_path,
                    remote_filename=self._remote_filename,
                    progress=self._on_progress,
                )
                start_response = None
                if self._start_after_upload:
                    start_response = client.start_print(remote)
                self.setResult(
                    {
                        "remote_filename": remote,
                        "started": self._start_after_upload,
                        "start_response": start_response,
                    }
                )
        except Exception as exc:
            self.setError(exc)
