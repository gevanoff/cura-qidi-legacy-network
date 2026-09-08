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
    # Cura's UI label is "Marlin", but enum defaults must use the internal option key.
    assert overrides["machine_gcode_flavor"]["default_value"] == "RepRap (Marlin/Sprinter)"


def test_extruder_definitions_match_ifast_tool_sides_and_latch_positions() -> None:
    first = _load("extruders/qidi_ifast_extruder_0.def.json")
    second = _load("extruders/qidi_ifast_extruder_1.def.json")

    assert first["name"] == "Extruder 1 (T0, right)"
    assert second["name"] == "Extruder 2 (T1, left)"
    assert first["metadata"] == {"machine": "qidi_ifast", "position": "0"}
    assert second["metadata"] == {"machine": "qidi_ifast", "position": "1"}
    assert first["overrides"]["extruder_nr"]["default_value"] == 0
    assert second["overrides"]["extruder_nr"]["default_value"] == 1

    # CuraEngine emits an actual travel to the old tool's end position before
    # the T command. On the i-Fast that wall contact mechanically lowers the
    # tool being selected next: T0 -> X0 selects T1, T1 -> X330 selects T0.
    assert first["overrides"]["machine_extruder_end_pos_abs"]["default_value"] is True
    assert second["overrides"]["machine_extruder_end_pos_abs"]["default_value"] is True
    assert first["overrides"]["machine_extruder_end_pos_x"]["value"] == 0
    assert second["overrides"]["machine_extruder_end_pos_x"]["value"] == 330

    # Current CuraEngine treats the new tool's start position as bookkeeping,
    # not an emitted move, so it must describe the wall position actually
    # reached by the previous tool's end travel.
    assert first["overrides"]["machine_extruder_start_pos_abs"]["default_value"] is True
    assert second["overrides"]["machine_extruder_start_pos_abs"]["default_value"] is True
    assert first["overrides"]["machine_extruder_start_pos_x"]["value"] == 330
    assert second["overrides"]["machine_extruder_start_pos_x"]["value"] == 0

    for extruder in (first, second):
        overrides = extruder["overrides"]
        assert overrides["machine_nozzle_size"]["default_value"] == 0.4
        assert overrides["material_diameter"]["default_value"] == 1.75
        assert overrides["machine_extruder_offset_x"]["default_value"] == 0.0
        assert overrides["machine_extruder_offset_y"]["default_value"] == 0.0


def test_global_quality_profile_contains_only_machine_wide_reliable_baseline() -> None:
    profile = _load_quality("quality/qidi_ifast/qidi_ifast_normal.inst.cfg")

    assert profile["general"]["definition"] == "qidi_ifast"
    assert profile["general"]["name"] == "0.20 mm Reliable"
    assert profile["metadata"].getboolean("global_quality") is True
    assert profile["metadata"]["quality_type"] == "normal"
    assert profile["metadata"].getint("setting_version") == 27

    values = profile["values"]
    assert values.getfloat("layer_height") == 0.20
    assert values.getfloat("layer_height_0") == 0.30
    assert values["adhesion_type"] == "brim"
    assert values.getfloat("brim_gap") == 0
    assert values.getfloat("brim_width") == 10

    # These controls are evaluated on each ExtruderStack and therefore belong
    # in the material-matched non-global quality container, not here.
    extruder_scoped_keys = {
        "cool_fan_speed_0",
        "initial_layer_line_width_factor",
        "material_flow_layer_0",
        "retraction_enable",
        "retraction_hop_enabled",
        "skirt_brim_speed",
        "speed_layer_0",
        "speed_print",
        "speed_travel",
        "travel_retract_before_outer_wall",
    }
    assert extruder_scoped_keys.isdisjoint(values)


def test_global_quality_profile_defines_conservative_support_baseline() -> None:
    profile = _load_quality("quality/qidi_ifast/qidi_ifast_normal.inst.cfg")
    values = profile["values"]

    assert values.getfloat("support_infill_rate") == 15
    assert values["support_pattern"] == "zigzag"
    assert values.getint("support_wall_count") == 1
    assert values.getboolean("support_interface_enable") is True
    assert values.getfloat("support_interface_density") == 80
    assert values.getfloat("support_interface_height") == 0.6
    assert values["support_interface_pattern"] == "zigzag"
    assert "support_enable" not in values
    assert "support_infill_extruder_nr" not in values
    assert "support_interface_extruder_nr" not in values
    assert "support_top_distance" not in values


def test_generic_pla_quality_applies_extruder_scoped_reliability_controls() -> None:
    profile = _load_quality(
        "quality/qidi_ifast/qidi_ifast_normal_generic_pla.inst.cfg"
    )

    assert profile["general"]["definition"] == "qidi_ifast"
    assert profile["general"]["name"] == "0.20 mm Reliable"
    assert "global_quality" not in profile["metadata"]
    assert profile["metadata"]["material"] == "generic_pla"
    assert profile["metadata"]["quality_type"] == "normal"
    assert profile["metadata"].getint("setting_version") == 27

    values = profile["values"]
    assert values.getfloat("material_print_temperature") == 200
    assert values.getfloat("material_print_temperature_layer_0") == 205
    assert values.getfloat("material_bed_temperature") == 60
    assert values.getfloat("material_bed_temperature_layer_0") == 65

    assert values.getfloat("speed_layer_0") == 15
    assert values.getfloat("skirt_brim_speed") == 15
    assert values.getfloat("speed_travel_layer_0") == 40
    assert values.getfloat("initial_layer_line_width_factor") == 120
    assert values.getfloat("material_flow_layer_0") == 100
    assert values.getfloat("skirt_brim_material_flow") == 100
    assert values.getfloat("cool_fan_speed_0") == 0
    assert values.getint("cool_fan_full_layer") == 4
    assert values.getfloat("cool_min_layer_time") == 10
    assert values.getint("speed_slowdown_layers") == 4

    assert values.getboolean("retraction_enable") is True
    assert values["retraction_combing"] == "off"
    assert values.getfloat("retraction_min_travel") == 1.5
    assert values.getboolean("retraction_hop_enabled") is True
    assert values.getboolean("retraction_hop_only_when_collides") is False
    assert values.getfloat("retraction_hop") == 0.2
    assert values.getfloat("speed_z_hop") == 5
    assert values["travel_retract_before_outer_wall"] == "force_retracted"
    assert values.getboolean("infill_before_walls") is False

    assert values.getfloat("speed_print") == 45
    assert values.getfloat("speed_infill") == 45
    assert values.getfloat("speed_wall") == 30
    assert values.getfloat("speed_wall_0") == 25
    assert values.getfloat("speed_topbottom") == 30
    assert values.getfloat("speed_travel") == 100


def test_start_gcode_primes_both_tools_and_restores_initial_latch() -> None:
    definition = _load("definitions/qidi_ifast.def.json")
    start = definition["overrides"]["machine_start_gcode"]["default_value"]
    end = definition["overrides"]["machine_end_gcode"]["default_value"]
    lines = start.splitlines()

    assert lines[:4] == [
        "G21 ; millimeters",
        "G90 ; absolute positioning",
        "M82 ; absolute extrusion",
        "G28",
    ]
    assert "G0 X0 Y0 Z50 F3600" in lines

    # QIDI's reference sequence primes T1/left and then T0/right.
    left_select = lines.index("T1")
    left_sweep = lines.index("G1 X{machine_width} E0 F2400")
    right_select = lines.index("T0")
    right_latch = lines.index("G0 X{machine_width} Y4 F3600")
    right_wipe = lines.index("G1 X5 E0 F2400")
    assert left_select < left_sweep < right_select < right_latch < right_wipe
    assert lines.count("G92 E-19") == 2

    # Cura tracks the slice's initial tool independently of custom start G-code.
    # Restore that tool and its physical wall latch after priming both nozzles.
    restore_select = lines.index("T{initial_extruder_nr}")
    if_marker = lines.index("{if initial_extruder_nr == 0}")
    restore_right = lines.index("G0 X{machine_width} Y4 F3600", right_latch + 1)
    else_marker = lines.index("{else}")
    restore_left = lines.index("G0 X0 Y6 F3600")
    endif_marker = lines.index("{endif}")
    assert right_wipe < restore_select < if_marker < restore_right
    assert restore_right < else_marker < restore_left < endif_marker
    assert lines[-1] == "G92 E0"

    assert "M104 T0 S0" in end
    assert "M104 T1 S0" in end
    assert "G1 X" not in end
    assert "G1 Y" not in end
