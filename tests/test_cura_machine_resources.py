import configparser
import json
from pathlib import Path

RESOURCE_ROOT = Path(__file__).resolve().parents[1] / "cura_resources"


def _load(relative_path: str) -> dict:
    return json.loads((RESOURCE_ROOT / relative_path).read_text(encoding="utf-8"))


def _load_quality(relative_path: str) -> configparser.ConfigParser:
    profile = configparser.ConfigParser(interpolation=None)
    profile.read(RESOURCE_ROOT / relative_path, encoding="utf-8")
    return profile


def test_machine_definition_declares_two_extruders_and_dual_build_volume() -> None:
    definition = _load("definitions/qidi_ifast.def.json")

    assert definition["version"] == 2
    assert definition["inherits"] == "fdmprinter"
    assert definition["metadata"]["supports_network_connection"] is True
    assert definition["metadata"]["has_machine_quality"] is True
    assert definition["metadata"]["preferred_quality_type"] == "normal"
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


def test_normal_quality_profile_defines_conservative_first_layer_baseline() -> None:
    profile = _load_quality("quality/qidi_ifast/qidi_ifast_normal.inst.cfg")

    assert profile["general"]["definition"] == "qidi_ifast"
    assert profile["metadata"].getboolean("global_quality") is True
    assert profile["metadata"]["quality_type"] == "normal"
    assert profile["metadata"].getint("setting_version") == 27

    values = profile["values"]
    assert values.getfloat("layer_height") == 0.20
    assert values.getfloat("layer_height_0") == 0.24
    assert values.getfloat("speed_layer_0") == 18
    assert values.getfloat("skirt_brim_speed") == 18
    assert values.getfloat("initial_layer_line_width_factor") == 120
    assert values["adhesion_type"] == "brim"
    assert values.getfloat("brim_width") == 8
    assert values.getfloat("cool_fan_speed_0") == 0


def test_generic_pla_overlay_pins_first_layer_temperatures() -> None:
    profile = _load_quality(
        "quality/qidi_ifast/qidi_ifast_normal_generic_pla.inst.cfg"
    )

    assert profile["general"]["definition"] == "qidi_ifast"
    assert profile["general"]["name"] == "0.20 mm Normal"
    assert profile["metadata"]["material"] == "generic_pla"
    assert profile["metadata"]["quality_type"] == "normal"
    assert profile["metadata"].getint("setting_version") == 27

    values = profile["values"]
    assert values.getfloat("material_print_temperature") == 200
    assert values.getfloat("material_print_temperature_layer_0") == 200
    assert values.getfloat("material_bed_temperature") == 60
    assert values.getfloat("material_bed_temperature_layer_0") == 65


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
