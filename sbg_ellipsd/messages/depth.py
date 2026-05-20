from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogDepth:
    """Hydrostatic depth/pressure sensor data (MSG 0x2F)."""

    timestamp_us: int
    status: int
    pressure_pa: float
    """Hydrostatic pressure in Pascal."""
    depth_m: float
    """Depth in metres (down positive)."""
