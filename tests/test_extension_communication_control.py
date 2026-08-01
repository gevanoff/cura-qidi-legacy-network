from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTENSION = ROOT / "cura_plugin" / "QidiLegacyNetwork" / "extension.py"


def test_extension_uses_one_communication_menu_item() -> None:
    source = EXTENSION.read_text(encoding="utf-8")

    assert 'self.addMenuItem("Cura Communication…", self._configure_communication)' in source
    assert 'self.addMenuItem("Pause Cura Communication for External Tools"' not in source
    assert 'self.addMenuItem("Resume Cura Communication"' not in source


def test_communication_dialog_exposes_checked_enabled_state() -> None:
    source = EXTENSION.read_text(encoding="utf-8")

    assert 'QCheckBox("Cura monitoring and uploads enabled")' in source
    assert "self._plugin.pause_communication()" in source
    assert "self._plugin.resume_communication()" in source
    assert 'Current state: {summary}' in source
