from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .qidi_legacy.models import PrinterStatus


@dataclass(frozen=True, slots=True)
class MonitorSnapshot:
    """Read-only values presented by the Cura Monitor tab."""

    printer_state: str
    filename: str | None
    progress_percent: float | None
    bytes_printed: int | None
    bytes_total: int | None
    bed_current: float | None
    bed_target: float | None
    extruder_current: tuple[float | None, float | None]
    extruder_target: tuple[float | None, float | None]
    x: float | None
    y: float | None
    z: float | None
    elapsed_seconds: int | None

    @classmethod
    def from_status(
        cls,
        status: "PrinterStatus",
        *,
        filename: str | None = None,
    ) -> "MonitorSnapshot":
        if status.is_idle is True:
            printer_state = "Idle"
        elif status.is_idle is False:
            printer_state = "Printing"
        else:
            printer_state = "Unknown"

        progress_percent = None
        if (
            status.bytes_printed is not None
            and status.bytes_total is not None
            and status.bytes_total > 0
        ):
            progress_percent = min(
                100.0,
                max(0.0, status.bytes_printed * 100.0 / status.bytes_total),
            )

        return cls(
            printer_state=printer_state,
            filename=filename,
            progress_percent=progress_percent,
            bytes_printed=status.bytes_printed,
            bytes_total=status.bytes_total,
            bed_current=status.bed_current,
            bed_target=status.bed_target,
            extruder_current=status.extruder_current,
            extruder_target=status.extruder_target,
            x=status.x,
            y=status.y,
            z=status.z,
            elapsed_seconds=status.elapsed_seconds,
        )
