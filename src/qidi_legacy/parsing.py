from __future__ import annotations

import re

from .models import HandshakeInfo, PrinterStatus


def _float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_tokens(message: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for item in message.strip().split():
        key, separator, value = item.partition(":")
        if separator and key:
            tokens[key] = value
    return tokens


def parse_handshake(message: str) -> HandshakeInfo:
    tokens = parse_tokens(message)
    machine_type = None
    x_max = y_max = z_max = None
    dimensions = tokens.get("T", "").split("/")
    if len(dimensions) >= 4:
        machine_type = dimensions[0]
        x_max = _float(dimensions[1])
        y_max = _float(dimensions[2])
        z_max = _float(dimensions[3])

    encoding = tokens.get("U", "utf-8").strip("'\"") or "utf-8"
    return HandshakeInfo(
        raw=message,
        x_mm_per_step=_float(tokens.get("X", "")),
        y_mm_per_step=_float(tokens.get("Y", "")),
        z_mm_per_step=_float(tokens.get("Z", "")),
        e_mm_per_step=_float(tokens.get("E", "")),
        machine_type=machine_type,
        x_max=x_max,
        y_max=y_max,
        z_max=z_max,
        encoding=encoding,
    )


def parse_firmware(message: str) -> str:
    stripped = message.strip()
    match = re.search(r"(?:^|\s)ok\s+(.+)$", stripped, flags=re.IGNORECASE)
    return match.group(1).strip() if match else stripped


def _temperature(value: str) -> tuple[float | None, float | None]:
    current, separator, target = value.partition("/")
    if not separator:
        return _float(value), None
    return _float(current), _float(target)


def parse_status(message: str) -> PrinterStatus:
    tokens = parse_tokens(message)
    bed_current, bed_target = _temperature(tokens.get("B", ""))
    e1_current, e1_target = _temperature(tokens.get("E1", ""))
    e2_current, e2_target = _temperature(tokens.get("E2", ""))

    bytes_printed = bytes_total = None
    is_idle = None
    progress = tokens.get("D", "").split("/")
    if len(progress) >= 2:
        bytes_printed = _int(progress[0])
        bytes_total = _int(progress[1])
    if len(progress) >= 3:
        is_idle = progress[2] == "1"

    known = {"B", "E1", "E2", "D", "F", "X", "Y", "Z", "T"}
    return PrinterStatus(
        raw=message,
        bed_current=bed_current,
        bed_target=bed_target,
        extruder_current=(e1_current, e2_current),
        extruder_target=(e1_target, e2_target),
        bytes_printed=bytes_printed,
        bytes_total=bytes_total,
        is_idle=is_idle,
        fan=_int(tokens.get("F", "").split("/")[0]),
        x=_float(tokens.get("X", "")),
        y=_float(tokens.get("Y", "")),
        z=_float(tokens.get("Z", "")),
        elapsed_seconds=_int(tokens.get("T", "")),
        extra={key: value for key, value in tokens.items() if key not in known},
    )
