import json
from pathlib import Path

import pytest

from scripts.install_cura_plugin import build_zip, install_plugin, stage_plugin


def test_stage_plugin_vendors_protocol_and_configuration(tmp_path: Path) -> None:
    plugin_dir = stage_plugin(tmp_path, host="10.10.22.122", port=3000)

    assert (plugin_dir / "plugin.json").is_file()
    assert (plugin_dir / "output_device.py").is_file()
    assert (plugin_dir / "qidi_legacy" / "client.py").is_file()
    assert json.loads((plugin_dir / "config.json").read_text()) == {
        "host": "10.10.22.122",
        "port": 3000,
        "timeout": 0.5,
        "retries": 3,
    }


def test_install_plugin_uses_cura_plugins_directory(tmp_path: Path) -> None:
    installed = install_plugin(tmp_path / "5.13", host="printer.local", port=3000)
    assert installed == tmp_path / "5.13" / "plugins" / "QidiLegacyNetwork"
    assert installed.is_dir()


def test_build_zip_contains_single_plugin_root(tmp_path: Path) -> None:
    destination = tmp_path / "QidiLegacyNetwork.zip"
    build_zip(destination, host="10.10.22.122", port=3000)

    import zipfile

    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
    assert "QidiLegacyNetwork/plugin.json" in names
    assert "QidiLegacyNetwork/qidi_legacy/client.py" in names
    assert "QidiLegacyNetwork/config.json" in names


def test_stage_plugin_rejects_invalid_configuration(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="host"):
        stage_plugin(tmp_path, host="", port=3000)
    with pytest.raises(ValueError, match="port"):
        stage_plugin(tmp_path, host="printer.local", port=70000)
