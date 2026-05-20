from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogMag:
    """Magnetometer and accelerometer raw measurements (MSG 0x04)."""

    timestamp_us: int
    """Time in microseconds (µs from power-up) or milliseconds (GPS ToW)."""

    status: int
    """Magnetometer status flags — interpret with :class:`~sbg_ellipsd.enums.MagStatus`."""

    mag_x: float
    """X-axis normalised magnetic field (arbitrary units)."""

    mag_y: float
    """Y-axis normalised magnetic field (arbitrary units)."""

    mag_z: float
    """Z-axis normalised magnetic field (arbitrary units)."""

    accel_x_ms2: float
    """X-axis acceleration in m/s²."""

    accel_y_ms2: float
    """Y-axis acceleration in m/s²."""

    accel_z_ms2: float
    """Z-axis acceleration in m/s²."""


@dataclass(frozen=True, slots=True)
class LogMagCalib:
    """Magnetic calibration raw buffer (MSG 0x05)."""

    timestamp_us: int
    buffer: bytes
    """16-byte raw calibration data blob."""
