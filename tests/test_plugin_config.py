from __future__ import annotations

import json

import pytest

from cura_plugin.QidiLegacyNetwork.config import build_config, load_config, save_config


def test_build_config_normalizes_address_and_port() -> None:
    config = build_config(" 10.10.22.189 ", "3000")

    assert config.host == "10.10.22.189"
    assert config.port == 3000


@pytest.mark.parametrize(
    ("host", "message"),
    [
        ("", "host is missing"),
        ("10.10.22. 189", "must not contain whitespace"),
        ("http://10.10.22.189", "without a URL or path"),
        ("10.10.22.189/status", "without a URL or path"),
    ],
)
def test_build_config_rejects_invalid_hosts(host: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_config(host)


@pytest.mark.parametrize("port", [0, 65536])
def test_build_config_rejects_invalid_ports(port: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 65535"):
        build_config("10.10.22.189", port)


def test_save_config_round_trips_and_replaces_existing_file(tmp_path) -> None:
    path = tmp_path / "plugin" / "config.json"
    path.parent.mkdir()
    path.write_text('{"host": "old-address"}\n', encoding="utf-8")

    expected = build_config("qidi-wired.local", 3000, timeout=0.75, retries=2)
    save_config(path, expected)

    assert load_config(path) == expected
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "host": "qidi-wired.local",
        "port": 3000,
        "retries": 2,
        "timeout": 0.75,
    }
    assert not (path.parent / ".config.json.tmp").exists()


def test_load_config_requires_json_object(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        load_config(path)
