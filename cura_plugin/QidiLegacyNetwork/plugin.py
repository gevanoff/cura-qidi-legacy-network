from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer
from UM.Logger import Logger
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from UM.PluginRegistry import PluginRegistry

from .config import PluginConfig, load_config
from .output_device import QidiLegacyOutputDevice
from .registration import OutputDeviceRegistrar


class QidiLegacyNetworkPlugin(OutputDevicePlugin):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._config: PluginConfig | None = None
        self._registrar: OutputDeviceRegistrar | None = None
        self._started = False
        self._signals_connected = False

    def _ensure_registrar(self) -> bool:
        if self._registrar is not None:
            return True

        plugin_path = PluginRegistry.getInstance().getPluginPath("QidiLegacyNetwork")
        if not plugin_path:
            Logger.log("e", "Cannot locate the QIDI Legacy Network plugin directory")
            return False

        try:
            self._config = load_config(Path(plugin_path) / "config.json")
        except Exception as exc:
            Logger.log("e", "Cannot load QIDI Legacy Network configuration: %s", exc)
            return False

        config = self._config
        self._registrar = OutputDeviceRegistrar(
            self._app,
            self.getOutputDeviceManager(),
            lambda start_after_upload: QidiLegacyOutputDevice(
                config,
                start_after_upload=start_after_upload,
            ),
            Logger.log,
        )
        return True

    def start(self) -> None:
        self._started = True
        if not self._ensure_registrar():
            return

        if not self._signals_connected:
            self._app.globalContainerStackChanged.connect(self._on_application_state_changed)
            main_window_changed = getattr(self._app, "mainWindowChanged", None)
            if main_window_changed is not None:
                main_window_changed.connect(self._on_application_state_changed)
            self._signals_connected = True

        # Cura starts output-device plugins before all UI and active-machine objects
        # are guaranteed to exist. Register once on the next event-loop turn and once
        # more after the startup window has settled. Stack/window signals keep the
        # devices synchronized after that.
        self._schedule_sync("startup", delay_ms=0)
        self._schedule_sync("startup fallback", delay_ms=1500)

    def _on_application_state_changed(self, *_args) -> None:
        self._schedule_sync("Cura application state changed", delay_ms=0)

    def _schedule_sync(self, reason: str, *, delay_ms: int) -> None:
        QTimer.singleShot(delay_ms, lambda: self._sync_output_devices(reason))

    def _sync_output_devices(self, reason: str) -> bool:
        if not self._started or not self._ensure_registrar():
            return False
        try:
            success = self._registrar.sync(activate_upload=True)
        except Exception:
            Logger.logException("e", "QIDI output-device sync failed after %s", reason)
            return False

        if success and self._config is not None:
            Logger.log(
                "i",
                "QIDI Legacy Network ready for %s:%s after %s",
                self._config.host,
                self._config.port,
                reason,
            )
        return success

    def refresh_now(self) -> bool:
        """Refresh devices from the Extensions menu after Cura is fully running."""

        self._started = True
        return self._sync_output_devices("manual refresh")

    def configuration_summary(self) -> str:
        if not self._ensure_registrar() or self._config is None:
            return "Configuration unavailable"
        return f"{self._config.host}:{self._config.port}"

    def stop(self) -> None:
        self._started = False
        if self._signals_connected:
            try:
                self._app.globalContainerStackChanged.disconnect(
                    self._on_application_state_changed
                )
            except Exception:
                pass
            main_window_changed = getattr(self._app, "mainWindowChanged", None)
            if main_window_changed is not None:
                try:
                    main_window_changed.disconnect(self._on_application_state_changed)
                except Exception:
                    pass
            self._signals_connected = False

        if self._registrar is not None:
            self._registrar.remove()
