from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "cura_plugin" / "QidiLegacyNetwork"
EXTENSION = PLUGIN_ROOT / "extension.py"
PLUGIN = PLUGIN_ROOT / "plugin.py"
MONITOR = PLUGIN_ROOT / "Monitor.qml"


def test_extension_uses_one_communication_menu_item() -> None:
    source = EXTENSION.read_text(encoding="utf-8")

    assert 'self.addMenuItem("Cura Communication…", self._configure_communication)' in source
    assert 'self.addMenuItem("Pause Cura Communication for External Tools"' not in source
    assert 'self.addMenuItem("Resume Cura Communication"' not in source


def test_communication_dialog_exposes_checked_enabled_state() -> None:
    source = EXTENSION.read_text(encoding="utf-8")

    assert 'QCheckBox("Cura monitoring and uploads enabled")' in source
    assert "self._enabled.setChecked(plugin.communication_enabled())" in source
    assert "self._plugin.set_communication_enabled(self._enabled.isChecked())" in source
    assert 'Current state: {summary}' in source


def test_plugin_reads_manual_pause_as_the_persistent_checkbox_state() -> None:
    source = PLUGIN.read_text(encoding="utf-8")

    assert "def communication_enabled(self) -> bool:" in source
    assert 'getattr(device, "manually_paused", False)' in source
    assert "def set_communication_enabled(self, enabled: bool) -> str:" in source


def test_monitor_points_to_current_communication_dialog() -> None:
    source = MONITOR.read_text(encoding="utf-8")

    assert "QIDI Legacy Network > Cura Communication…" in source
    assert "clear Cura monitoring and uploads enabled" in source
    assert "Pause Cura Communication for External Tools" not in source
