import json
from pathlib import Path

import pytest

from scripts.install_cura_plugin import (
    build_zip,
    install_machine_resources,
    install_plugin,
    stage_plugin,
)


def test_stage_plugin_vendors_protocol_and_configuration(tmp_path: Path) -> None:
    plugin_dir = stage_plugin(tmp_path, host="10.10.22.122", port=3000)

    assert (plugin_dir / "plugin.json").is_file()
    assert (plugin_dir / "output_device.py").is_file()
    assert (plugin_dir / "registration.py").is_file()
    assert (plugin_dir / "extension.py").is_file()
    assert (plugin_dir / "qidi_legacy" / "client.py").is_file()
    assert json.loads((plugin_dir / "config.json").read_text()) == {
        "host": "10.10.22.122",
        "port": 3000,
        "timeout": 0.5,
        "retries": 3,
    }


def test_install_machine_resources_uses_cura_resource_directories(tmp_path: Path) -> None:
    installed = install_machine_resources(tmp_path / "5.13")

    expected = {
        tmp_path / "5.13" / "definitions" / "qidi_ifast.def.json",
        tmp_path / "5.13" / "extruders" / "qidi_ifast_extruder_0.def.json",
        tmp_path / "5.13" / "extruders" / "qidi_ifast_extruder_1.def.json",
        tmp_path
        / "5.13"
        / "quality"
        / "qidi_ifast"
        / "qidi_ifast_normal.inst.cfg",
        tmp_path
        / "5.13"
        / "quality"
        / "qidi_ifast"
        / "qidi_ifast_normal_generic_pla.inst.cfg",
    }
    assert set(installed) == expected
    assert all(path.is_file() for path in expected)


def test_install_plugin_uses_cura_plugins_and_resource_directories(tmp_path: Path) -> None:
    cura_config = tmp_path / "5.13"
    installed = install_plugin(cura_config, host="printer.local", port=3000)

    assert installed == cura_config / "plugins" / "QidiLegacyNetwork"
    assert installed.is_dir()
    assert (cura_config / "definitions" / "qidi_ifast.def.json").is_file()
    assert (cura_config / "extruders" / "qidi_ifast_extruder_0.def.json").is_file()
    assert (cura_config / "extruders" / "qidi_ifast_extruder_1.def.json").is_file()
    assert (
        cura_config
        / "quality"
        / "qidi_ifast"
        / "qidi_ifast_normal.inst.cfg"
    ).is_file()
    assert (
        cura_config
        / "quality"
        / "qidi_ifast"
        / "qidi_ifast_normal_generic_pla.inst.cfg"
    ).is_file()


def test_build_zip_contains_single_plugin_root(tmp_path: Path) -> None:
    destination = tmp_path / "QidiLegacyNetwork.zip"
    build_zip(destination, host="10.10.22.122", port=3000)

    import zipfile

    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
    assert "QidiLegacyNetwork/plugin.json" in names
    assert "QidiLegacyNetwork/registration.py" in names
    assert "QidiLegacyNetwork/extension.py" in names
    assert "QidiLegacyNetwork/qidi_legacy/client.py" in names
    assert "QidiLegacyNetwork/config.json" in names
    assert not any(name.startswith("definitions/") for name in names)
    assert not any(name.startswith("quality/") for name in names)


def test_stage_plugin_rejects_invalid_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="host"):
        stage_plugin(tmp_path, host="", port=3000)
    with pytest.raises(ValueError, match="port"):
        stage_plugin(tmp_path, host="printer.local", port=70000)
