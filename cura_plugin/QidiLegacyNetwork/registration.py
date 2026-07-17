from __future__ import annotations

from typing import Any, Callable

UPLOAD_DEVICE_ID = "qidi_legacy_upload"
UPLOAD_AND_PRINT_DEVICE_ID = "qidi_legacy_upload_and_print"
DEVICE_IDS = (UPLOAD_DEVICE_ID, UPLOAD_AND_PRINT_DEVICE_ID)

DeviceFactory = Callable[[bool], Any]
LogFunction = Callable[..., None]


def machine_name(stack: Any) -> str:
    getter = getattr(stack, "getName", None)
    if callable(getter):
        try:
            return str(getter())
        except Exception:
            pass
    return type(stack).__name__


def machine_supports_gcode(stack: Any) -> bool:
    """Return whether a Cura machine stack can produce plain G-code.

    Some third-party/custom stacks omit ``file_formats`` metadata. Cura's GCodeWriter
    is still usable for those stacks, so missing metadata is treated as compatible.
    """

    if stack is None:
        return False
    getter = getattr(stack, "getMetaDataEntry", None)
    if not callable(getter):
        return True
    try:
        raw_formats = getter("file_formats")
    except Exception:
        return True
    if not raw_formats:
        return True
    formats = {item.strip() for item in str(raw_formats).split(";") if item.strip()}
    return "text/x-gcode" in formats


class OutputDeviceRegistrar:
    """Synchronize the two QIDI devices with Cura's shared output manager."""

    def __init__(
        self,
        app: Any,
        manager: Any,
        device_factory: DeviceFactory,
        log: LogFunction,
    ) -> None:
        self._app = app
        self._manager = manager
        self._device_factory = device_factory
        self._log = log

    def remove(self) -> None:
        for device_id in DEVICE_IDS:
            if self._manager.getOutputDevice(device_id) is not None:
                self._manager.removeOutputDevice(device_id)

    def sync(self, *, activate_upload: bool = True) -> bool:
        stack = self._app.getGlobalContainerStack()
        if stack is None:
            self._log("d", "QIDI output-device registration deferred: no active machine stack")
            return False
        if not machine_supports_gcode(stack):
            self.remove()
            self._log(
                "w",
                "QIDI output devices not registered: active machine %s does not advertise text/x-gcode",
                machine_name(stack),
            )
            return False

        # Remove and recreate the devices deliberately. This emits a fresh
        # outputDevicesChanged signal after Cura has finished constructing its UI and
        # active machine stack, avoiding devices registered too early in startup.
        self.remove()
        self._manager.addOutputDevice(self._device_factory(False))
        self._manager.addOutputDevice(self._device_factory(True))

        if activate_upload:
            self._manager.setActiveDevice(UPLOAD_DEVICE_ID)

        manager_ids = list(self._manager.getOutputDeviceIds())
        active = self._manager.getActiveDevice()
        active_id = active.getId() if active is not None else "<none>"
        success = all(device_id in manager_ids for device_id in DEVICE_IDS)
        self._log(
            "i",
            "QIDI output-device sync for machine %s: expected=%s manager=%s active=%s success=%s",
            machine_name(stack),
            list(DEVICE_IDS),
            manager_ids,
            active_id,
            success,
        )
        return success
