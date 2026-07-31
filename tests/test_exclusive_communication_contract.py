from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "cura_plugin" / "QidiLegacyNetwork"


def test_plugin_constructs_exclusive_output_device() -> None:
    source = (PLUGIN_ROOT / "plugin.py").read_text(encoding="utf-8")

    assert "from .exclusive_output_device import ExclusiveQidiLegacyOutputDevice" in source
    assert "lambda start_after_upload: ExclusiveQidiLegacyOutputDevice(" in source


def test_output_device_suspends_polling_around_entire_upload() -> None:
    source = (PLUGIN_ROOT / "exclusive_output_device.py").read_text(encoding="utf-8")

    update_start = source.index("    def _update(self) -> None:")
    update_end = source.index("    def _on_monitor_finished", update_start)
    update_body = source[update_start:update_end]
    assert "if not self._communication_state.polling_allowed:" in update_body

    request_start = source.index("    def requestWrite")
    request_end = source.index("    def _on_finished", request_start)
    request_body = source[request_start:request_end]
    assert request_body.index("begin_upload()") < request_body.index("super().requestWrite")

    finished_body = source[source.index("    def _on_finished"):]
    assert "finish_upload()" in finished_body
    assert "self._update()" in finished_body


def test_monitor_exposes_exclusive_access_state() -> None:
    qml = (PLUGIN_ROOT / "Monitor.qml").read_text(encoding="utf-8")

    assert "OutputDevice.communicationStateText" in qml
    assert "OutputDevice.communicationNoticeText" in qml
    assert "OutputDevice.communicationPaused" in qml
