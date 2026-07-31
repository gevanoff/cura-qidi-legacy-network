import json
from pathlib import Path

RESOURCE_ROOT = Path(__file__).resolve().parents[1] / "cura_resources"


def _load(relative_path: str) -> dict:
    return json.loads((RESOURCE_ROOT / relative_path).read_text(encoding="utf-8"))


def test_machine_definition_declares_two_extruders_and_dual_build_volume() -> None:
    definition = _load("definitions/qidi_ifast.def.json")

    assert definition["version"] == 2
    assert definition["inherits"] == "fdmprinter"
    assert definition["metadata"]["supports_network_connection"] is True
    assert definition["metadata"]["machine_extruder_trains"] == {
        "0": "qidi_ifast_extruder_0",
        "1": "qidi_ifast_extruder_1",
    }

    overrides = definition["overrides"]
    assert overrides["machine_width"]["default_value"] == 330
    assert overrides["machine_depth"]["default_value"] == 250
    assert overrides["machine_height"]["default_value"] == 320
    assert overrides["machine_extruder_count"]["default_value"] == 2
    assert overrides["machine_gcode_flavor"]["default_value"] == "Marlin"


def test_extruder_definitions_are_numbered_and_start_with_zero_slicer_offsets() -> None:
    first = _load("extruders/qidi_ifast_extruder_0.def.json")
    second = _load("extruders/qidi_ifast_extruder_1.def.json")

    assert first["metadata"] == {"machine": "qidi_ifast", "position": "0"}
    assert second["metadata"] == {"machine": "qidi_ifast", "position": "1"}
    assert first["overrides"]["extruder_nr"]["default_value"] == 0
    assert second["overrides"]["extruder_nr"]["default_value"] == 1

    for extruder in (first, second):
        overrides = extruder["overrides"]
        assert overrides["machine_nozzle_size"]["default_value"] == 0.4
        assert overrides["material_diameter"]["default_value"] == 1.75
        assert overrides["machine_extruder_offset_x"]["default_value"] == 0.0
        assert overrides["machine_extruder_offset_y"]["default_value"] == 0.0


def test_start_and_end_gcode_do_not_contain_unvalidated_xy_purge_moves() -> None:
    definition = _load("definitions/qidi_ifast.def.json")
    start = definition["overrides"]["machine_start_gcode"]["default_value"]
    end = definition["overrides"]["machine_end_gcode"]["default_value"]

    assert "G28" in start
    assert "M82" in start
    assert "T0" not in start
    assert "T1" not in start
    assert "M104 T0 S0" in end
    assert "M104 T1 S0" in end
    assert "G1 X" not in start
    assert "G1 Y" not in start
    assert "G1 X" not in end
    assert "G1 Y" not in end
