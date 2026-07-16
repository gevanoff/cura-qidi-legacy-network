from __future__ import annotations

from pathlib import Path

from UM.Logger import Logger
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from UM.PluginRegistry import PluginRegistry

from .config import load_config
from .output_device import QidiLegacyOutputDevice


class QidiLegacyNetworkPlugin(OutputDevicePlugin):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._device_ids: list[str] = []

    def start(self) -> None:
        plugin_path = PluginRegistry.getInstance().getPluginPath("QidiLegacyNetwork")
        if not plugin_path:
            Logger.log("e", "Cannot locate the QIDI Legacy Network plugin directory")
            return

        try:
            config = load_config(Path(plugin_path) / "config.json")
        except Exception as exc:
            Logger.log("e", "Cannot load QIDI Legacy Network configuration: %s", exc)
            return

        manager = self.getOutputDeviceManager()
        for start_after_upload in (False, True):
            device = QidiLegacyOutputDevice(
                config,
                start_after_upload=start_after_upload,
            )
            manager.addOutputDevice(device)
            self._device_ids.append(device.getId())

        Logger.log(
            "i",
            "QIDI Legacy Network output devices registered for %s:%s",
            config.host,
            config.port,
        )

    def stop(self) -> None:
        manager = self.getOutputDeviceManager()
        for device_id in self._device_ids:
            manager.removeOutputDevice(device_id)
        self._device_ids.clear()
