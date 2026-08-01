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


def test_open_communication_dialog_is_reused() -> None:
    source = EXTENSION.read_text(encoding="utf-8")

    method_start = source.index("    def _configure_communication(self) -> None:")
    method_end = source.index("    def _communication_dialog_closed", method_start)
    method_body = source[method_start:method_end]

    existing_check = method_body.index("if self._communication_dialog is not None:")
    construct_dialog = method_body.index("dialog = _CommunicationDialog(self._plugin)")
    assert existing_check < construct_dialog
    assert "self._present_dialog(self._communication_dialog)" in method_body
    assert "return" in method_body[existing_check:construct_dialog]


def test_plugin_reads_manual_pause_as_the_persistent_checkbox_state() -> None:
    source = PLUGIN.read_text(encoding="utf-8")

    assert "def communication_enabled(self) -> bool:" in source
    assert 'getattr(device, "manually_paused", False)' in source
    assert "def set_communication_enabled(self, enabled: bool) -> str:" in source


def test_address_change_constructs_replacement_already_paused() -> None:
    source = PLUGIN.read_text(encoding="utf-8")

    make_start = source.index("    def _make_registrar")
    make_end = source.index("    def _ensure_registrar", make_start)
    make_body = source[make_start:make_end]
    assert "initially_paused: bool = False" in make_body
    assert "initially_paused=initially_paused" in make_body

    update_start = source.index("    def update_configuration")
    update_end = source.index("    def stop", update_start)
    update_body = source[update_start:update_end]
    registrar_call = update_body.index("self._registrar = self._make_registrar(")
    sync_call = update_body.index('self._sync_output_devices("configuration changed")')
    assert "initially_paused=restore_manual_pause" in update_body
    assert registrar_call < sync_call
    assert "replacement.pause_communication()" not in update_body


def test_monitor_points_to_current_communication_dialog() -> None:
    source = MONITOR.read_text(encoding="utf-8")

    assert "QIDI Legacy Network > Cura Communication…" in source
    assert "clear Cura monitoring and uploads enabled" in source
    assert "Pause Cura Communication for External Tools" not in source
