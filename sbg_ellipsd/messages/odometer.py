from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogOdoVel:
    """Odometer velocity along the body X-axis (MSG 0x13)."""

    timestamp_us: int
    status: int
    velocity_ms: float
    """Velocity in m/s; negative values indicate reverse motion."""
