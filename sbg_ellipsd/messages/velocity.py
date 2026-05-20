from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogVelocity1:
    """Generic external velocity aiding input/output (MSG 0x3A)."""

    timestamp_us: int
    """Time in microseconds (µs from power-up) or milliseconds (GPS ToW)."""

    status: int
    """Time-type and component validity flags."""

    velocity_0_ms: float
    """Body-frame X velocity component in m/s."""
    velocity_1_ms: float
    velocity_2_ms: float
    velocity_0_std_ms: float
    velocity_1_std_ms: float
    velocity_2_std_ms: float
