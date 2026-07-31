from pathlib import Path


MONITOR_QML = (
    Path(__file__).resolve().parents[1]
    / "cura_plugin"
    / "QidiLegacyNetwork"
    / "Monitor.qml"
)


def test_monitor_qml_exports_component_for_cura_loader() -> None:
    text = MONITOR_QML.read_text(encoding="utf-8")
    body_lines = [
        line
        for line in text.splitlines()
        if not line.startswith("import ") and line.strip()
    ]

    assert body_lines[0] == "Component"
    assert body_lines[1] == "{"
    assert body_lines[2].strip() == "Item"
