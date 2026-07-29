from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class PluginConfig:
    host: str
    port: int = 3000
    timeout: float = 0.5
    retries: int = 3


def build_config(
    host: object,
    port: object = 3000,
    timeout: object = 0.5,
    retries: object = 3,
) -> PluginConfig:
    normalized_host = str(host).strip()
    if not normalized_host:
        raise ValueError("QIDI printer host is missing")
    if any(character.isspace() for character in normalized_host):
        raise ValueError("QIDI printer host must not contain whitespace")
    if "://" in normalized_host or "/" in normalized_host:
        raise ValueError("Enter only the printer hostname or IP address, without a URL or path")

    normalized_port = int(port)
    if not 1 <= normalized_port <= 65535:
        raise ValueError("QIDI printer port must be between 1 and 65535")

    normalized_timeout = float(timeout)
    if normalized_timeout <= 0:
        raise ValueError("QIDI timeout must be positive")

    normalized_retries = int(retries)
    if normalized_retries < 1:
        raise ValueError("QIDI retries must be at least 1")

    return PluginConfig(
        host=normalized_host,
        port=normalized_port,
        timeout=normalized_timeout,
        retries=normalized_retries,
    )


def _from_mapping(data: Mapping[str, object]) -> PluginConfig:
    return build_config(
        data.get("host", ""),
        data.get("port", 3000),
        data.get("timeout", 0.5),
        data.get("retries", 3),
    )


def load_config(path: str | Path) -> PluginConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("QIDI configuration must be a JSON object")
    return _from_mapping(data)


def save_config(path: str | Path, config: PluginConfig) -> None:
    """Atomically persist configuration so Cura never observes a partial JSON file."""

    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = config_path.with_name(f".{config_path.name}.tmp")
    payload = json.dumps(asdict(config), indent=2, sort_keys=True) + "\n"
    temporary_path.write_text(payload, encoding="utf-8", newline="\n")
    temporary_path.replace(config_path)
