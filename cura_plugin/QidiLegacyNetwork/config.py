from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PluginConfig:
    host: str
    port: int = 3000
    timeout: float = 0.5
    retries: int = 3


def load_config(path: str | Path) -> PluginConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))

    host = str(data.get("host", "")).strip()
    if not host:
        raise ValueError("QIDI printer host is missing")
    if any(character.isspace() for character in host):
        raise ValueError("QIDI printer host must not contain whitespace")

    port = int(data.get("port", 3000))
    if not 1 <= port <= 65535:
        raise ValueError("QIDI printer port must be between 1 and 65535")

    timeout = float(data.get("timeout", 0.5))
    if timeout <= 0:
        raise ValueError("QIDI timeout must be positive")

    retries = int(data.get("retries", 3))
    if retries < 1:
        raise ValueError("QIDI retries must be at least 1")

    return PluginConfig(host=host, port=port, timeout=timeout, retries=retries)
