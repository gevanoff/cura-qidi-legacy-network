from __future__ import annotations

from typing import Any, Callable

UPLOAD_DEVICE_ID = "qidi_legacy_upload"
UPLOAD_AND_PRINT_DEVICE_ID = "qidi_legacy_upload_and_print"
NETWORK_CONNECTION_TYPE = 2

# Only the upload-only device is exposed. It is also a PrinterOutputDevice, so the same
# long-lived instance supplies Cura's read-only Monitor view.
DEVICE_IDS = (UPLOAD_DEVICE_ID,)
MANAGED_DEVICE_IDS = (UPLOAD_DEVICE_ID, UPLOAD_AND_PRINT_DEVICE_ID)

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


def associate_network_connection(stack: Any) -> None:
    """Mark the active Cura machine as configured for this LAN output device.

    Cura's Monitor empty-state logic reads the machine stack's network metadata separately
    from the registered PrinterOutputDevice. Set both fields so existing i-Fast machine
    instances created before the definition was corrected become monitorable immediately.
    """
    setter = getattr(stack, "setMetaDataEntry", None)
    if callable(setter):
        setter("supports_network_connection", True)

    add_connection = getattr(stack, "addConfiguredConnectionType", None)
    if callable(add_connection):
        add_connection(NETWORK_CONNECTION_TYPE)
    elif callable(setter):
        setter("connection_type", str(NETWORK_CONNECTION_TYPE))


class OutputDeviceRegistrar:
    """Synchronize the safe QIDI upload/monitor device with Cura's output manager."""

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

    def _remove_device(self, device_id: str) -> None:
        device = self._manager.getOutputDevice(device_id)
        if device is None:
            return
        close = getattr(device, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                self._log("w", "Could not close QIDI output device %s", device_id)
        self._manager.removeOutputDevice(device_id)

    def remove(self) -> None:
        for device_id in MANAGED_DEVICE_IDS:
            self._remove_device(device_id)

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

        associate_network_connection(stack)

        # Remove the historical automatic-start device, but preserve the current upload/monitor
        # device across routine Cura state-change signals. Recreating it would repeatedly reset
        # the Monitor view and leave status workers finishing against discarded objects.
        self._remove_device(UPLOAD_AND_PRINT_DEVICE_ID)
        if self._manager.getOutputDevice(UPLOAD_DEVICE_ID) is None:
            self._manager.addOutputDevice(self._device_factory(False))

        if activate_upload:
            self._manager.setActiveDevice(UPLOAD_DEVICE_ID)

        manager_ids = list(self._manager.getOutputDeviceIds())
        active = self._manager.getActiveDevice()
        active_id = active.getId() if active is not None else "<none>"
        success = all(device_id in manager_ids for device_id in DEVICE_IDS) and (
            UPLOAD_AND_PRINT_DEVICE_ID not in manager_ids
        )
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
