from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)
from UM.Extension import Extension
from UM.Message import Message


class _PrinterAddressDialog(QDialog):
    def __init__(self, plugin) -> None:
        super().__init__()
        self._plugin = plugin
        self.setWindowTitle("QIDI Legacy Network — Printer Address")
        self.setModal(True)
        self.setMinimumWidth(440)

        config = plugin.configuration()
        self._host = QLineEdit(config.host)
        self._host.setPlaceholderText("Printer hostname or IP address")
        self._host.selectAll()

        self._port = QSpinBox()
        self._port.setRange(1, 65535)
        self._port.setValue(config.port)

        explanation = QLabel(
            "Enter the printer's wired Ethernet address when available. On the i-Fast, "
            "select the plug symbol and check or re-check Start Operation. The legacy UDP "
            "service requires exclusive access: pause Cura communication before using QIDI "
            "Print, qidi-legacy, or another client. Network uploads receive a remote byte-count "
            "check only; use direct USB for important jobs."
        )
        explanation.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Printer address:", self._host)
        form.addRow("UDP port:", self._port)

        self._error = QLabel()
        self._error.setWordWrap(True)
        self._error.setStyleSheet("color: #d32f2f;")
        self._error.hide()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(explanation)
        layout.addLayout(form)
        layout.addWidget(self._error)
        layout.addWidget(buttons)

    def _show_error(self, text: str) -> None:
        self._error.setText(text)
        self._error.show()

    def _save(self) -> None:
        try:
            config = self._plugin.update_configuration(
                self._host.text(),
                self._port.value(),
            )
        except Exception as exc:
            self._show_error(str(exc) or type(exc).__name__)
            return

        Message(
            f"QIDI upload action now uses {config.host}:{config.port}.",
            title="QIDI Printer Address Updated",
            message_type=Message.MessageType.POSITIVE,
        ).show()
        self.accept()


class QidiLegacyNetworkExtension(Extension):
    """Cura menu surface for printer configuration and diagnostics."""

    def __init__(self, plugin) -> None:
        super().__init__()
        self._plugin = plugin
        self._configuration_dialog: _PrinterAddressDialog | None = None
        self.setMenuName("QIDI Legacy Network")
        self.addMenuItem(
            "Pause Cura Communication for External Tools",
            self._pause_communication,
        )
        self.addMenuItem("Resume Cura Communication", self._resume_communication)
        self.addMenuItem("Configure Printer Address…", self._configure_printer)
        self.addMenuItem("Refresh Output Devices", self._refresh_output_devices)
        self.addMenuItem("Show Connection", self._show_connection)

    @staticmethod
    def _show_action_result(text: str, *, title: str, error: bool = False) -> None:
        Message(
            text,
            lifetime=0 if error else 30,
            dismissable=True,
            use_inactivity_timer=not error,
            title=title,
            message_type=(
                Message.MessageType.ERROR if error else Message.MessageType.POSITIVE
            ),
        ).show()

    def _pause_communication(self) -> None:
        try:
            text = self._plugin.pause_communication()
        except Exception as exc:
            self._show_action_result(
                str(exc) or type(exc).__name__,
                title="QIDI Communication Pause Failed",
                error=True,
            )
            return
        self._show_action_result(text, title="QIDI Communication Paused")

    def _resume_communication(self) -> None:
        try:
            text = self._plugin.resume_communication()
        except Exception as exc:
            self._show_action_result(
                str(exc) or type(exc).__name__,
                title="QIDI Communication Resume Failed",
                error=True,
            )
            return
        self._show_action_result(text, title="QIDI Communication Resumed")

    def _configure_printer(self) -> None:
        try:
            self._configuration_dialog = _PrinterAddressDialog(self._plugin)
        except Exception as exc:
            Message(
                str(exc) or type(exc).__name__,
                lifetime=0,
                dismissable=True,
                use_inactivity_timer=False,
                title="QIDI Configuration Unavailable",
                message_type=Message.MessageType.ERROR,
            ).show()
            return
        self._configuration_dialog.finished.connect(self._configuration_dialog_closed)
        self._configuration_dialog.show()
        self._configuration_dialog.raise_()
        self._configuration_dialog.activateWindow()

    def _configuration_dialog_closed(self, _result: int) -> None:
        self._configuration_dialog = None

    def _refresh_output_devices(self) -> None:
        success = self._plugin.refresh_now()
        if success:
            text = (
                "Upload to QIDI was registered and selected. The historical automatic-start "
                "action was removed for integrity safety."
            )
            message_type = Message.MessageType.POSITIVE
        else:
            text = (
                "The QIDI upload device could not be registered. Check cura.log for "
                "QIDI output-device sync details."
            )
            message_type = Message.MessageType.ERROR
        Message(
            text,
            title="QIDI Legacy Network",
            message_type=message_type,
        ).show()

    def _show_connection(self) -> None:
        Message(
            (
                f"Configured printer: {self._plugin.configuration_summary()}\n"
                f"Cura communication: {self._plugin.communication_summary()}"
            ),
            title="QIDI Legacy Network",
        ).show()
