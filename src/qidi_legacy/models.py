from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class HandshakeInfo:
    raw: str
    x_mm_per_step: float | None = None
    y_mm_per_step: float | None = None
    z_mm_per_step: float | None = None
    e_mm_per_step: float | None = None
    machine_type: str | None = None
    x_max: float | None = None
    y_max: float | None = None
    z_max: float | None = None
    encoding: str = "utf-8"


@dataclass(frozen=True, slots=True)
class PrinterStatus:
    raw: str
    bed_current: float | None = None
    bed_target: float | None = None
    extruder_current: tuple[float | None, float | None] = (None, None)
    extruder_target: tuple[float | None, float | None] = (None, None)
    bytes_printed: int | None = None
    bytes_total: int | None = None
    is_idle: bool | None = None
    fan: int | None = None
    x: float | None = None
    y: float | None = None
    z: float | None = None
    elapsed_seconds: int | None = None
    extra: dict[str, str] = field(default_factory=dict)
