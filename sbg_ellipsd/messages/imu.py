from dataclasses import dataclass

_ACCEL_SCALE = 1.0 / 1_048_576.0   # LSB → m/s²
_RATE_SCALE  = 1.0 / 67_108_864.0  # LSB → rad/s  (standard scale)
_TEMP_SCALE  = 1.0 / 256.0         # LSB → °C


@dataclass(frozen=True, slots=True)
class LogImuShort:
    """Asynchronous IMU measurements — preferred for post-processing (MSG 0x2C).

    Raw integer counts from the binary payload are pre-scaled to SI units
    during parsing.
    """

    timestamp_us: int
    """Time since device power-up in microseconds."""

    status: int
    """IMU health flags — interpret with :class:`~sbg_ellipsd.enums.ImuStatus`."""

    accel_x_ms2: float
    """Body-frame X acceleration in m/s²."""

    accel_y_ms2: float
    """Body-frame Y acceleration in m/s²."""

    accel_z_ms2: float
    """Body-frame Z acceleration in m/s²."""

    rate_x_rads: float
    """Body-frame X angular rate in rad/s."""

    rate_y_rads: float
    """Body-frame Y angular rate in rad/s."""

    rate_z_rads: float
    """Body-frame Z angular rate in rad/s."""

    temperature_c: float
    """IMU temperature in °C."""


@dataclass(frozen=True, slots=True)
class LogImuData:
    """Synchronous IMU measurements — **deprecated**, prefer LogImuShort (MSG 0x03)."""

    timestamp_us: int
    status: int
    """IMU health flags — interpret with :class:`~sbg_ellipsd.enums.ImuStatus`."""

    accel_x_ms2: float
    accel_y_ms2: float
    accel_z_ms2: float
    rate_x_rads: float
    rate_y_rads: float
    rate_z_rads: float
    temperature_c: float
