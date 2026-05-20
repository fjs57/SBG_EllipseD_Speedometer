from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogDvlBottomTrack:
    """Doppler velocity log — bottom tracking mode (MSG 0x1D)."""

    timestamp_us: int
    status: int
    velocity_x_ms: float
    """DVL body-frame X velocity in m/s."""
    velocity_y_ms: float
    velocity_z_ms: float
    velocity_x_std_ms: float
    velocity_y_std_ms: float
    velocity_z_std_ms: float


@dataclass(frozen=True, slots=True)
class LogDvlWaterTrack:
    """Doppler velocity log — water tracking mode (MSG 0x1E)."""

    timestamp_us: int
    status: int
    velocity_x_ms: float
    velocity_y_ms: float
    velocity_z_ms: float
    velocity_x_std_ms: float
    velocity_y_std_ms: float
    velocity_z_std_ms: float
