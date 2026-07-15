"""Initial Cura 5 output-device plugin shell.

This module avoids importing the standalone protocol package until Cura loads the plugin,
which keeps the protocol testable without a Cura installation.
"""

from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from UM.Logger import Logger


class QidiLegacyNetworkPlugin(OutputDevicePlugin):
    def __init__(self, app):
        super().__init__()
        self._app = app
        Logger.log("i", "QIDI Legacy Network plugin loaded")

    def start(self):
        Logger.log("i", "QIDI Legacy Network protocol layer is ready; output device pending hardware probe")

    def stop(self):
        pass
