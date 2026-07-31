from __future__ import annotations

from PyQt6.QtCore import pyqtProperty
from cura.PrinterOutput.PrinterOutputDevice import ConnectionState
from UM.Logger import Logger
from UM.OutputDevice import OutputDeviceError

from .communication_state import QidiCommunicationState
from .monitor_job import QidiMonitorStatusJob
from .output_device import QidiLegacyOutputDevice


class ExclusiveQidiLegacyOutputDevice(QidiLegacyOutputDevice):
    """QIDI output device that grants one operation exclusive access to the printer.

    The i-Fast's legacy UDP service cannot reliably accept status requests while an upload is
    active. The existing process-wide protocol lock serializes worker jobs; this class also stops
    the polling scheduler before the upload starts and keeps it stopped until the upload finishes.
    """

    def __init__(self, *args, **kwargs) -> None:
        # The base constructor calls self._update(), so initialize the state first.
        self._communication_state = QidiCommunicationState()
        super().__init__(*args, **kwargs)

    @pyqtProperty(str, notify=QidiLegacyOutputDevice.monitorChanged)
    def communicationStateText(self) -> str:
        return self._communication_state.state_text

    @pyqtProperty(str, notify=QidiLegacyOutputDevice.monitorChanged)
    def communicationNoticeText(self) -> str:
        return self._communication_state.notice_text

    @pyqtProperty(bool, notify=QidiLegacyOutputDevice.monitorChanged)
    def communicationPaused(self) -> bool:
        return not self._communication_state.polling_allowed

    @pyqtProperty(str, notify=QidiLegacyOutputDevice.monitorChanged)
    def connectionStatusText(self) -> str:
        if self._communication_state.upload_active:
            return "Uploading — monitoring paused"
        if self._communication_state.manual_pause:
            if self._monitor_job is not None:
                return "Pausing after current request"
            return "Paused for external access"
        return super().connectionStatusText

    @property
    def upload_active(self) -> bool:
        return self._communication_state.upload_active

    @property
    def manually_paused(self) -> bool:
        return self._communication_state.manual_pause

    def pause_communication(self) -> str:
        self._communication_state.pause_for_external_access()
        self._monitor_error = ""
        self.monitorChanged.emit()
        if self._communication_state.upload_active:
            return (
                "The current Cura upload still has exclusive access. External tools must remain "
                "closed until the upload finishes and Monitor shows 'Paused for external access'."
            )
        if self._monitor_job is not None:
            return (
                "Cura will stop QIDI communication after the current status request finishes. "
                "Wait until Monitor shows 'Paused for external access' before using another client."
            )
        self.setConnectionState(ConnectionState.Closed)
        return (
            "Cura QIDI communication is paused. QIDI Print, qidi-legacy, or another client may "
            "now use the printer exclusively."
        )

    def resume_communication(self) -> str:
        self._communication_state.resume_after_external_access()
        self.monitorChanged.emit()
        if self._communication_state.upload_active:
            return "The upload still has exclusive access; monitoring will resume when it finishes."
        self.setConnectionState(ConnectionState.Connecting)
        self._update()
        return "Cura QIDI communication resumed."

    def communication_summary(self) -> str:
        return self._communication_state.state_text

    def _update(self) -> None:
        if not self._communication_state.polling_allowed:
            return
        super()._update()

    def _on_monitor_finished(self, job: QidiMonitorStatusJob) -> None:
        if job is not self._monitor_job:
            return
        if not self._communication_state.polling_allowed:
            # The request may have started just before a manual pause or upload. Discard its
            # result and, critically, do not schedule another request.
            self._monitor_job = None
            if (
                self._communication_state.manual_pause
                and not self._communication_state.upload_active
            ):
                self.setConnectionState(ConnectionState.Closed)
            self.monitorChanged.emit()
            return
        super()._on_monitor_finished(job)

    def requestWrite(self, *args, **kwargs) -> None:
        if self._communication_state.manual_pause:
            raise OutputDeviceError.WriteRequestFailedError(
                "Cura QIDI communication is paused for an external client. Resume communication "
                "before starting an upload."
            )

        self._communication_state.begin_upload()
        self.setConnectionState(ConnectionState.Busy)
        self.monitorChanged.emit()
        Logger.log(
            "i",
            "QIDI upload granted exclusive Cura communication access; status polling paused",
        )
        try:
            super().requestWrite(*args, **kwargs)
        except Exception:
            self._communication_state.finish_upload()
            self.setConnectionState(ConnectionState.Connecting)
            self.monitorChanged.emit()
            self._update()
            raise

    def _on_finished(self, job) -> None:
        try:
            super()._on_finished(job)
        finally:
            self._communication_state.finish_upload()
            Logger.log(
                "i",
                "QIDI upload released exclusive Cura communication access",
            )
            if self._communication_state.manual_pause:
                self.setConnectionState(ConnectionState.Closed)
            else:
                self.setConnectionState(ConnectionState.Connecting)
            self.monitorChanged.emit()
            self._update()
