from __future__ import annotations

from UM.Extension import Extension
from UM.Message import Message


class QidiLegacyNetworkExtension(Extension):
    """Small Cura menu surface for diagnostics and manual device refresh."""

    def __init__(self, plugin) -> None:
        super().__init__()
        self._plugin = plugin
        self.setMenuName("QIDI Legacy Network")
        self.addMenuItem("Refresh Output Devices", self._refresh_output_devices)
        self.addMenuItem("Show Connection", self._show_connection)

    def _refresh_output_devices(self) -> None:
        success = self._plugin.refresh_now()
        if success:
            text = "QIDI upload actions were registered and Upload to QIDI was selected."
            message_type = Message.MessageType.POSITIVE
        else:
            text = (
                "QIDI output devices could not be registered. Check cura.log for "
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
            f"Configured printer: {self._plugin.configuration_summary()}",
            title="QIDI Legacy Network",
        ).show()
