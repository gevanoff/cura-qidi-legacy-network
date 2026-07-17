from __future__ import annotations

import os
import re
import tempfile
from io import StringIO
from pathlib import Path
from typing import Optional

from UM.Logger import Logger
from UM.Message import Message
from UM.OutputDevice import OutputDeviceError
from UM.OutputDevice.OutputDevice import OutputDevice
from UM.PluginRegistry import PluginRegistry

from .config import PluginConfig
from .upload_job import QidiUploadJob

_FORBIDDEN_FILENAME_CHARS = re.compile(r'["\'´`<>()\[\]?*\\,;:&%#$!/]+')


class QidiLegacyOutputDevice(OutputDevice):
    def __init__(self, config: PluginConfig, *, start_after_upload: bool) -> None:
        action = "upload_and_print" if start_after_upload else "upload"
        super().__init__(f"qidi_legacy_{action}")

        self._config = config
        self._start_after_upload = start_after_upload
        self._writing = False
        self._temp_path: Optional[Path] = None
        self._job: Optional[QidiUploadJob] = None
        self._message: Optional[Message] = None

        if start_after_upload:
            self.setName("QIDI Legacy Network — Upload and Print")
            self.setShortDescription("Upload and Print")
            self.setDescription(f"Upload G-code to {config.host} and start printing")
            self.setIconName("print")
            self.setPriority(4)
        else:
            self.setName("QIDI Legacy Network — Upload")
            self.setShortDescription("Upload to QIDI")
            self.setDescription(f"Upload G-code to {config.host} without starting it")
            self.setIconName("save")
            self.setPriority(5)

    @staticmethod
    def _remote_filename(file_name: Optional[str]) -> str:
        name = Path(file_name or "cura_job").name
        if name.lower().endswith(".gcode"):
            name = name[:-6]
        name = _FORBIDDEN_FILENAME_CHARS.sub("_", name)
        name = re.sub(r"\s+", "_", name).strip("._")
        return f"{name or 'cura_job'}.gcode"

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
        except OSError as exc:
            self.writeError.emit(self)
            raise OutputDeviceError.WriteRequestFailedError(
                f"Could not create temporary G-code file: {exc}"
            ) from exc

        action_text = "Uploading and starting" if self._start_after_upload else "Uploading"
        self._message = Message(
            f"{action_text} <filename>{remote_filename}</filename> on {self._config.host}",
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
        if "create file" in lowered:
            return (
                "The printer could not create the destination file. Confirm that USB storage "
                "is inserted, mounted, and writable on the QIDI printer."
            )
        if "no reply" in lowered or "udp request failed" in lowered:
            return (
                f"{text}\n\nWindows sent the UDP request but did not receive the printer's "
                "reply. Close QIDI Print and any qidi-legacy status monitor, then check Windows "
                "Defender Firewall or the selected network interface."
            )
        if "timed out" in lowered or "timeout" in lowered:
            return (
                "The printer did not respond in time. Confirm the IP address and network "
                "connection, then retry."
            )
        return text or type(error).__name__

    def _on_finished(self, job: QidiUploadJob) -> None:
        self._cleanup_temp_file()
        self._writing = False
        self.writeFinished.emit(self)

        if self._message is not None:
            self._message.hide()
            self._message = None

        error = job.getError()
        if error is not None:
            Logger.log("e", "QIDI upload failed: %s", error)
            Message(
                self._friendly_error(error),
                title="QIDI Upload Failed",
                message_type=Message.MessageType.ERROR,
            ).show()
            self.writeError.emit(self)
        else:
            result = job.getResult() or {}
            remote = result.get("remote_filename", "the file")
            started = bool(result.get("started"))
            if started:
                text = f"Uploaded <filename>{remote}</filename> and started the print."
            else:
                text = f"Uploaded <filename>{remote}</filename> to the printer."
            Message(
                text,
                title="QIDI Upload Complete",
                message_type=Message.MessageType.POSITIVE,
            ).show()
            self.writeSuccess.emit(self)

        self._job = None
