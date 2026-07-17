from cura_plugin.QidiLegacyNetwork.registration import (
    DEVICE_IDS,
    UPLOAD_AND_PRINT_DEVICE_ID,
    UPLOAD_DEVICE_ID,
    OutputDeviceRegistrar,
    machine_supports_gcode,
)


class FakeStack:
    def __init__(self, formats="text/x-gcode") -> None:
        self.formats = formats

    def getName(self):
        return "QIDI i-Fast Temporary"

    def getMetaDataEntry(self, key):
        assert key == "file_formats"
        return self.formats


class FakeApp:
    def __init__(self, stack=None) -> None:
        self.stack = stack

    def getGlobalContainerStack(self):
        return self.stack


class FakeDevice:
    def __init__(self, device_id) -> None:
        self._device_id = device_id

    def getId(self):
        return self._device_id


class FakeManager:
    def __init__(self) -> None:
        self.devices = {}
        self.active = None

    def getOutputDevice(self, device_id):
        return self.devices.get(device_id)

    def getOutputDeviceIds(self):
        return self.devices.keys()

    def addOutputDevice(self, device):
        self.devices[device.getId()] = device

    def removeOutputDevice(self, device_id):
        self.devices.pop(device_id, None)
        return True

    def setActiveDevice(self, device_id):
        self.active = self.devices.get(device_id)

    def getActiveDevice(self):
        return self.active


def device_factory(start_after_upload):
    device_id = UPLOAD_AND_PRINT_DEVICE_ID if start_after_upload else UPLOAD_DEVICE_ID
    return FakeDevice(device_id)


def test_registration_waits_for_active_machine_stack() -> None:
    manager = FakeManager()
    logs = []
    registrar = OutputDeviceRegistrar(
        FakeApp(),
        manager,
        device_factory,
        lambda *args: logs.append(args),
    )

    assert registrar.sync() is False
    assert manager.devices == {}


def test_registration_recreates_devices_and_activates_upload() -> None:
    manager = FakeManager()
    manager.devices[UPLOAD_DEVICE_ID] = FakeDevice(UPLOAD_DEVICE_ID)
    logs = []

    def log(*args):
        logs.append(args)

    registrar = OutputDeviceRegistrar(
        FakeApp(FakeStack("application/x-3mf;text/x-gcode")),
        manager,
        device_factory,
        log,
    )

    assert registrar.sync() is True
    assert tuple(manager.devices) == DEVICE_IDS
    assert manager.getActiveDevice().getId() == UPLOAD_DEVICE_ID
    assert any("success=%s" in entry[1] and entry[-1] is True for entry in logs)


def test_registration_removes_devices_for_non_gcode_machine() -> None:
    manager = FakeManager()
    manager.devices[UPLOAD_DEVICE_ID] = FakeDevice(UPLOAD_DEVICE_ID)
    registrar = OutputDeviceRegistrar(
        FakeApp(FakeStack("application/x-3mf")),
        manager,
        device_factory,
        lambda *_args: None,
    )

    assert registrar.sync() is False
    assert manager.devices == {}


def test_missing_file_format_metadata_is_compatible() -> None:
    assert machine_supports_gcode(FakeStack("")) is True
