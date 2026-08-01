from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer
from UM.Logger import Logger
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from UM.PluginRegistry import PluginRegistry

from .config import PluginConfig, build_config, load_config, save_config
from .exclusive_output_device import ExclusiveQidiLegacyOutputDevice
from .registration import OutputDeviceRegistrar, UPLOAD_DEVICE_ID


class QidiLegacyNetworkPlugin(OutputDevicePlugin):
    def __init__(self, app) -> None:
        super().__init__()
        self._app = app
        self._config: PluginConfig | None = None
        self._config_path: Path | None = None
        self._registrar: OutputDeviceRegistrar | None = None
        self._started = False
        self._signals_connected = False

    def _locate_config_path(self) -> Path:
        if self._config_path is not None:
            return self._config_path

        plugin_path = PluginRegistry.getInstance().getPluginPath("QidiLegacyNetwork")
        if not plugin_path:
            raise RuntimeError("Cannot locate the QIDI Legacy Network plugin directory")
        self._config_path = Path(plugin_path) / "config.json"
        return self._config_path

    def _load_configuration(self) -> PluginConfig:
        if self._config is None:
            self._config = load_config(self._locate_config_path())
        return self._config

    def _make_registrar(self, config: PluginConfig) -> OutputDeviceRegistrar:
        return OutputDeviceRegistrar(
            self._app,
            self.getOutputDeviceManager(),
            lambda start_after_upload: ExclusiveQidiLegacyOutputDevice(
                config,
                start_after_upload=start_after_upload,
            ),
            Logger.log,
        )

    def _ensure_registrar(self) -> bool:
        if self._registrar is not None:
            return True

        try:
            config = self._load_configuration()
        except Exception as exc:
            Logger.log("e", "Cannot load QIDI Legacy Network configuration: %s", exc)
            return False

        self._registrar = self._make_registrar(config)
        return True

    def _managed_output_device(self):
        return self.getOutputDeviceManager().getOutputDevice(UPLOAD_DEVICE_ID)

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

    def pause_communication(self) -> str:
        device = self._managed_output_device()
        if device is None:
            self.refresh_now()
            device = self._managed_output_device()
        if device is None or not hasattr(device, "pause_communication"):
            raise RuntimeError("The QIDI output device is not available.")
        return device.pause_communication()

    def resume_communication(self) -> str:
        device = self._managed_output_device()
        if device is None or not hasattr(device, "resume_communication"):
            raise RuntimeError("The QIDI output device is not available.")
        return device.resume_communication()

    def communication_enabled(self) -> bool:
        """Return the persistent user-controlled communication state.

        Upload-exclusive mode temporarily suppresses monitoring but does not itself clear this
        setting. A manual pause does, including when requested during an active upload.
        """

        device = self._managed_output_device()
        if device is None:
            self.refresh_now()
            device = self._managed_output_device()
        if device is None:
            raise RuntimeError("The QIDI output device is not available.")
        return not bool(getattr(device, "manually_paused", False))

    def set_communication_enabled(self, enabled: bool) -> str:
        current = self.communication_enabled()
        if enabled == current:
            if enabled:
                return "Cura monitoring and uploads are already enabled."
            return "Cura monitoring and uploads are already paused for external access."
        if enabled:
            return self.resume_communication()
        return self.pause_communication()

    def communication_summary(self) -> str:
        device = self._managed_output_device()
        if device is None or not hasattr(device, "communication_summary"):
            return "Unavailable"
        return device.communication_summary()

    def configuration(self) -> PluginConfig:
        return self._load_configuration()

    def configuration_summary(self) -> str:
        try:
            config = self.configuration()
        except Exception:
            return "Configuration unavailable"
        return f"{config.host}:{config.port}"

    def update_configuration(self, host: str, port: int) -> PluginConfig:
        """Persist a new address and recreate Cura's output devices immediately."""

        existing_device = self._managed_output_device()
        if existing_device is not None and getattr(existing_device, "upload_active", False):
            raise RuntimeError("The printer address cannot be changed during a QIDI upload.")
        restore_manual_pause = bool(
            existing_device is not None and getattr(existing_device, "manually_paused", False)
        )

        current = self.configuration()
        updated = build_config(
            host,
            port,
            timeout=current.timeout,
            retries=current.retries,
        )
        save_config(self._locate_config_path(), updated)

        if self._registrar is not None:
            self._registrar.remove()
        self._config = updated
        self._registrar = self._make_registrar(updated)
        self._started = True

        if not self._sync_output_devices("configuration changed"):
            raise RuntimeError(
                "The address was saved, but Cura could not refresh the QIDI output devices. "
                "Restart Cura or use Extensions > QIDI Legacy Network > Refresh Output Devices."
            )

        if restore_manual_pause:
            replacement = self._managed_output_device()
            if replacement is not None and hasattr(replacement, "pause_communication"):
                replacement.pause_communication()
        return updated

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
