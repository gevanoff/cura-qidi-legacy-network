from __future__ import annotations

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

    Keep this subclass free of additional Qt signals and properties. Cura's output device already
    has a Qt meta-object, and extending that meta-object in a development plugin can fail while Cura
    is importing extensions. Communication state is exposed to the Python extension menu instead.
    """

    # The base constructor calls self._update(). A class-level sentinel lets that early call return
    # without assigning Python attributes before the wrapped Qt base object has been initialized.
    _communication_state: QidiCommunicationState | None = None

    def __init__(self, *args, initially_paused: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        state = QidiCommunicationState()
        if initially_paused:
            state.pause_for_external_access()
        self._communication_state = state

        if initially_paused:
            # Do not issue even one initial status request when replacing a device while an
            # external client has exclusive access.
            self.setConnectionState(ConnectionState.Closed)
            self.monitorChanged.emit()
        else:
            self._update()

    def _state(self) -> QidiCommunicationState:
        state = self._communication_state
        if state is None:
            raise RuntimeError("QIDI communication state is not initialized")
        return state

    @property
    def upload_active(self) -> bool:
        state = self._communication_state
        return bool(state is not None and state.upload_active)

    @property
    def manually_paused(self) -> bool:
        state = self._communication_state
        return bool(state is not None and state.manual_pause)

    def pause_communication(self) -> str:
        state = self._state()
        state.pause_for_external_access()
        self._monitor_error = ""
        self.monitorChanged.emit()
        if state.upload_active:
            return (
                "The current Cura upload still has exclusive access. External tools must remain "
                "closed until the upload finishes and Cura reports that communication is paused."
            )
        if self._monitor_job is not None:
            return (
                "Cura will stop QIDI communication after the current status request finishes. "
                "Wait a few seconds before using another client."
            )
        self.setConnectionState(ConnectionState.Closed)
        return (
            "Cura QIDI communication is paused. QIDI Print, qidi-legacy, or another client may "
            "now use the printer exclusively."
        )

    def resume_communication(self) -> str:
        state = self._state()
        state.resume_after_external_access()
        self.monitorChanged.emit()
        if state.upload_active:
            return "The upload still has exclusive access; monitoring will resume when it finishes."
        self.setConnectionState(ConnectionState.Connecting)
        self._update()
        return "Cura QIDI communication resumed."

    def communication_summary(self) -> str:
        state = self._communication_state
        return "Starting" if state is None else state.state_text

    def _update(self) -> None:
        state = self._communication_state
        if state is None or not state.polling_allowed:
            return
        super()._update()

    def _on_monitor_finished(self, job: QidiMonitorStatusJob) -> None:
        if job is not self._monitor_job:
            return
        state = self._communication_state
        if state is None or not state.polling_allowed:
            # The request may have started just before a manual pause or upload. Discard its
            # result and, critically, do not schedule another request.
            self._monitor_job = None
            if state is not None and state.manual_pause and not state.upload_active:
                self.setConnectionState(ConnectionState.Closed)
            self.monitorChanged.emit()
            return
        super()._on_monitor_finished(job)

    def requestWrite(self, *args, **kwargs) -> None:
        state = self._state()
        if state.manual_pause:
            raise OutputDeviceError.WriteRequestFailedError(
                "Cura QIDI communication is paused for an external client. Resume communication "
                "before starting an upload."
            )
        if state.upload_active:
            raise OutputDeviceError.DeviceBusyError()

        try:
            state.begin_upload()
        except RuntimeError as exc:
            # Keep all state-machine failures inside Cura's normal output-device error path.
            raise OutputDeviceError.WriteRequestFailedError(str(exc)) from exc

        self.setConnectionState(ConnectionState.Busy)
        self.monitorChanged.emit()
        Logger.log(
            "i",
            "QIDI upload granted exclusive Cura communication access; status polling paused",
        )
        try:
            super().requestWrite(*args, **kwargs)
        except Exception:
            state.finish_upload()
            self.setConnectionState(ConnectionState.Connecting)
            self.monitorChanged.emit()
            self._update()
            raise

    def _on_finished(self, job) -> None:
        state = self._state()
        try:
            super()._on_finished(job)
        finally:
            state.finish_upload()
            Logger.log(
                "i",
                "QIDI upload released exclusive Cura communication access",
            )
            if state.manual_pause:
                self.setConnectionState(ConnectionState.Closed)
            else:
                self.setConnectionState(ConnectionState.Connecting)
            self.monitorChanged.emit()
            self._update()
