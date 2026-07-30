from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import pyqtProperty, pyqtSignal
from cura.PrinterOutput.PrinterOutputDevice import (
    ConnectionState,
    ConnectionType,
    PrinterOutputDevice,
)
from UM.Logger import Logger
from UM.Message import Message
from UM.OutputDevice import OutputDeviceError
from UM.PluginRegistry import PluginRegistry

from .config import PluginConfig
from .monitor_job import QidiMonitorStatusJob
from .monitor_snapshot import MonitorSnapshot
from .notifications import notify_upload_result
from .upload_job import QidiUploadJob

_FORBIDDEN_FILENAME_CHARS = re.compile(r'["\'´`<>()\[\]?*\\,;:&%#$!/]+')


class QidiLegacyOutputDevice(PrinterOutputDevice):
    monitorChanged = pyqtSignal()

    def __init__(self, config: PluginConfig, *, start_after_upload: bool) -> None:
        action = "upload_and_print" if start_after_upload else "upload"
        super().__init__(
            f"qidi_legacy_{action}",
            connection_type=ConnectionType.NetworkConnection,
        )

        self._config = config
        self._start_after_upload = start_after_upload
        self._writing = False
        self._temp_path: Optional[Path] = None
        self._source_sha256: Optional[str] = None
        self._job: Optional[QidiUploadJob] = None
        self._message: Optional[Message] = None
        self._result_message: Optional[Message] = None

        self._monitoring_enabled = True
        self._monitor_job: Optional[QidiMonitorStatusJob] = None
        self._monitor_snapshot: Optional[MonitorSnapshot] = None
        self._monitor_error = ""
        self._last_update = "Never"
        self._monitor_view_qml_path = str(Path(__file__).with_name("Monitor.qml"))
        self.setConnectionText(f"QIDI legacy UDP at {config.host}:{config.port}")
        self._setAcceptsCommands(False)

        if start_after_upload:
            self.setName("QIDI Legacy Network — Upload and Print (Disabled)")
            self.setShortDescription("Upload and Print (Disabled)")
            self.setDescription("Automatic network print start is disabled for integrity safety")
            self.setIconName("print")
            self.setPriority(4)
        else:
            self.setName("QIDI Legacy Network — Upload")
            self.setShortDescription("Upload to QIDI")
            self.setDescription(f"Upload G-code to {config.host} without starting it")
            self.setIconName("save")
            self.setPriority(5)

        super().connect()
        self._update()

    @staticmethod
    def _remote_filename(file_name: Optional[str]) -> str:
        name = Path(file_name or "cura_job").name
        if name.lower().endswith(".gcode"):
            name = name[:-6]
        name = _FORBIDDEN_FILENAME_CHARS.sub("_", name)
        name = re.sub(r"\s+", "_", name).strip("._")
        return f"{name or 'cura_job'}.gcode"

    @staticmethod
    def _temperature_text(current: float | None, target: float | None) -> str:
        if current is None and target is None:
            return "—"
        if current is None:
            return f"— / {target:.1f} °C"
        if target is None:
            return f"{current:.1f} °C"
        return f"{current:.1f} / {target:.1f} °C"

    @staticmethod
    def _elapsed_text(seconds: int | None) -> str:
        if seconds is None or seconds < 0:
            return "—"
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:d}:{minutes:02d}:{seconds:02d}"

    @pyqtProperty(str, constant=True)
    def addressText(self) -> str:
        return f"{self._config.host}:{self._config.port}"

    @pyqtProperty(str, notify=monitorChanged)
    def connectionStatusText(self) -> str:
        labels = {
            ConnectionState.Closed: "Disconnected",
            ConnectionState.Connecting: "Connecting",
            ConnectionState.Connected: "Connected",
            ConnectionState.Busy: "Busy",
            ConnectionState.Error: "Unavailable",
        }
        return labels.get(self.connectionState, "Unknown")

    @pyqtProperty(str, notify=monitorChanged)
    def printerStateText(self) -> str:
        if self._monitor_snapshot is None:
            return "Unknown"
        return self._monitor_snapshot.printer_state

    @pyqtProperty(str, notify=monitorChanged)
    def filenameText(self) -> str:
        if self._monitor_snapshot is None or not self._monitor_snapshot.filename:
            return "—"
        return self._monitor_snapshot.filename

    @pyqtProperty(str, notify=monitorChanged)
    def bedTemperatureText(self) -> str:
        snapshot = self._monitor_snapshot
        if snapshot is None:
            return "—"
        return self._temperature_text(snapshot.bed_current, snapshot.bed_target)

    @pyqtProperty(str, notify=monitorChanged)
    def extruder1TemperatureText(self) -> str:
        snapshot = self._monitor_snapshot
        if snapshot is None:
            return "—"
        return self._temperature_text(
            snapshot.extruder_current[0],
            snapshot.extruder_target[0],
        )

    @pyqtProperty(str, notify=monitorChanged)
    def extruder2TemperatureText(self) -> str:
        snapshot = self._monitor_snapshot
        if snapshot is None:
            return "—"
        return self._temperature_text(
            snapshot.extruder_current[1],
            snapshot.extruder_target[1],
        )

    @pyqtProperty(str, notify=monitorChanged)
    def positionText(self) -> str:
        snapshot = self._monitor_snapshot
        if snapshot is None or all(value is None for value in (snapshot.x, snapshot.y, snapshot.z)):
            return "—"

        def value_text(value: float | None) -> str:
            return "—" if value is None else f"{value:.2f}"

        return (
            f"X {value_text(snapshot.x)}  "
            f"Y {value_text(snapshot.y)}  "
            f"Z {value_text(snapshot.z)}"
        )

    @pyqtProperty(str, notify=monitorChanged)
    def elapsedText(self) -> str:
        if self._monitor_snapshot is None:
            return "—"
        return self._elapsed_text(self._monitor_snapshot.elapsed_seconds)

    @pyqtProperty(str, notify=monitorChanged)
    def lastUpdateText(self) -> str:
        return self._last_update

    @pyqtProperty(str, notify=monitorChanged)
    def monitorErrorText(self) -> str:
        if not self._monitor_error:
            return ""
        return f"Status polling failed: {self._monitor_error}"

    @pyqtProperty(bool, notify=monitorChanged)
    def hasProgress(self) -> bool:
        return (
            self._monitor_snapshot is not None
            and self._monitor_snapshot.progress_percent is not None
        )

    @pyqtProperty(float, notify=monitorChanged)
    def progressPercent(self) -> float:
        if self._monitor_snapshot is None or self._monitor_snapshot.progress_percent is None:
            return 0.0
        return self._monitor_snapshot.progress_percent

    @pyqtProperty(str, notify=monitorChanged)
    def progressText(self) -> str:
        snapshot = self._monitor_snapshot
        if snapshot is None or snapshot.progress_percent is None:
            return "—"
        byte_text = ""
        if snapshot.bytes_printed is not None and snapshot.bytes_total is not None:
            byte_text = f" ({snapshot.bytes_printed:,} / {snapshot.bytes_total:,} bytes)"
        return f"{snapshot.progress_percent:.1f}%{byte_text}"

    def _update(self) -> None:
        if not self._monitoring_enabled or self._monitor_job is not None:
            return
        self._monitor_job = QidiMonitorStatusJob(self._config)
        self._monitor_job.finished.connect(self._on_monitor_finished)
        self._monitor_job.start()

    def _on_monitor_finished(self, job: QidiMonitorStatusJob) -> None:
        if job is not self._monitor_job:
            return
        self._monitor_job = None
        if not self._monitoring_enabled:
            return

        error = job.getError()
        if error is not None:
            self._monitor_error = str(error) or type(error).__name__
            self.setConnectionState(ConnectionState.Error)
            self.monitorChanged.emit()
            return

        result = job.getResult()
        if not isinstance(result, MonitorSnapshot):
            self._monitor_error = "The status worker returned an invalid result."
            self.setConnectionState(ConnectionState.Error)
            self.monitorChanged.emit()
            return

        self._monitor_snapshot = result
        self._monitor_error = ""
        self._last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.setConnectionState(ConnectionState.Connected)
        self.monitorChanged.emit()

    def close(self) -> None:
        self._monitoring_enabled = False
        super().close()

    def requestWrite(
        self,
        nodes,
        file_name=None,
        limit_mimetypes=False,
        file_handler=None,
        filter_by_machine=False,
        **kwargs,
    ) -> None:
        if self._writing:
            raise OutputDeviceError.DeviceBusyError()

        if self._result_message is not None:
            self._result_message.hide()
            self._result_message = None

        self.writeStarted.emit(self)

        stream = StringIO()
        writer = PluginRegistry.getInstance().getPluginObject("GCodeWriter")
        if writer is None:
            self.writeError.emit(self)
            raise OutputDeviceError.WriteRequestFailedError("Cura G-code writer is unavailable")
        if not writer.write(stream, None):
            self.writeError.emit(self)
            raise OutputDeviceError.WriteRequestFailedError("Cura could not generate G-code")

        remote_filename = self._remote_filename(file_name)
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".gcode",
                prefix="cura-qidi-",
                delete=False,
                newline="",
            ) as temp_file:
                temp_file.write(stream.getvalue())
                self._temp_path = Path(temp_file.name)
            source_bytes = self._temp_path.read_bytes()
            self._source_sha256 = hashlib.sha256(source_bytes).hexdigest()
            Logger.log(
                "i",
                "Prepared QIDI upload source %s: %s bytes sha256=%s",
                self._temp_path,
                len(source_bytes),
                self._source_sha256,
            )
        except OSError as exc:
            self.writeError.emit(self)
            raise OutputDeviceError.WriteRequestFailedError(
                f"Could not create temporary G-code file: {exc}"
            ) from exc

        self._message = Message(
            f"Uploading <filename>{remote_filename}</filename> to {self._config.host}",
            lifetime=0,
            dismissable=False,
            progress=0,
            title="QIDI Legacy Network",
        )
        self._message.show()

        self._job = QidiUploadJob(
            self._temp_path,
            remote_filename,
            self._config,
            start_after_upload=self._start_after_upload,
        )
        self._job.progress.connect(self._on_progress)
        self._job.finished.connect(self._on_finished)
        self._writing = True
        self._job.start()

    def _on_progress(self, job: QidiUploadJob, progress: int) -> None:
        self.writeProgress.emit(self, progress)
        if self._message is not None:
            self._message.setProgress(progress)

    def _cleanup_temp_file(self) -> None:
        if self._temp_path is None:
            return
        try:
            os.remove(self._temp_path)
        except FileNotFoundError:
            pass
        except OSError as exc:
            Logger.log("w", "Could not remove temporary QIDI G-code file: %s", exc)
        self._temp_path = None

    @staticmethod
    def _friendly_error(error: Exception) -> str:
        text = str(error)
        lowered = text.casefold()
        if "automatic network print start is disabled" in lowered:
            return (
                f"{text}\n\nUse Upload to QIDI only, or save directly to removable USB media. "
                "Automatic start cannot be made safe with remote byte-count verification alone."
            )
        if "create file" in lowered:
            return (
                "The printer could not create the destination file. Confirm that USB storage "
                "is inserted, mounted, and writable on the QIDI printer."
            )
        if "remote size verification failed" in lowered:
            return (
                f"{text}\n\nThe file was saved, but its remote byte count does not match "
                "Cura's generated G-code. The print was not started."
            )
        if "uploaded file was not found" in lowered or "m20" in lowered:
            return (
                f"{text}\n\nThe file could not be checked in the printer's M20 listing. "
                "The print was not started."
            )
        if "upload block acknowledgement timed out" in lowered:
            return (
                f"{text}\n\nThe printer stopped acknowledging file blocks during the sustained "
                "upload. The partial file was closed and the print was not started. This usually "
                "indicates a lost UDP reply or delayed printer/USB write activity rather than "
                "invalid G-code.\n\nWi-Fi has proven unreliable for large transfers on the tested "
                "i-Fast. Wired Ethernet reduces timeouts but has also produced silent same-size "
                "content corruption. Save important G-code directly to a USB flash drive and "
                "start it from the printer touchscreen."
            )
        if "no reply" in lowered or "udp request failed" in lowered:
            return (
                f"{text}\n\nWindows sent the UDP request but did not receive the printer's "
                "reply. Close QIDI Print and any qidi-legacy status monitor, then confirm the "
                "selected printer interface and IP address."
            )
        if "timed out" in lowered or "timeout" in lowered:
            return (
                "The printer did not respond in time. Confirm the IP address and network "
                "connection, then retry."
            )
        return text or type(error).__name__

    def _on_finished(self, job: QidiUploadJob) -> None:
        source_sha256 = self._source_sha256
        self._cleanup_temp_file()
        self._source_sha256 = None
        self._writing = False
        self.writeFinished.emit(self)

        if self._message is not None:
            self._message.hide()
            self._message = None

        error = job.getError()
        if error is not None:
            Logger.log("e", "QIDI upload failed: %s", error)
            notify_upload_result(success=False)
            self._result_message = Message(
                self._friendly_error(error),
                lifetime=0,
                dismissable=True,
                use_inactivity_timer=False,
                title="QIDI Upload Failed",
                message_type=Message.MessageType.ERROR,
            )
            self._result_message.show()
            self.writeError.emit(self)
        else:
            result = job.getResult() or {}
            remote = result.get("remote_filename", "the file")
            digest_note = f" Source SHA-256: {source_sha256}." if source_sha256 else ""
            text = (
                f"Uploaded <filename>{remote}</filename>; the printer reports the expected byte "
                "count. Content integrity was not verified, and the print was not started. "
                "Use direct removable USB media for important jobs."
                f"{digest_note}"
            )
            Logger.log(
                "w",
                "QIDI upload completed with size-only verification: remote=%s source_sha256=%s",
                remote,
                source_sha256 or "<unavailable>",
            )
            notify_upload_result(success=True)
            self._result_message = Message(
                text,
                title="QIDI Upload Completed — Size Check Only",
                message_type=Message.MessageType.POSITIVE,
            )
            self._result_message.show()
            self.writeSuccess.emit(self)

        self._job = None
        self._update()
