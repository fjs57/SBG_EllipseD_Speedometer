from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogEkfEuler:
    """Euler angles with 1-σ accuracy estimates (MSG 0x06).

    Use :class:`~sbg_ellipsd.enums.SolutionMode` and
    :class:`~sbg_ellipsd.enums.EkfSolutionFlags` to interpret ``solution_status``.
    """

    timestamp_us: int
    roll_rad: float
    pitch_rad: float
    yaw_rad: float
    roll_std_rad: float
    pitch_std_rad: float
    yaw_std_rad: float
    solution_status: int
    magnetic_declination_rad: float
    magnetic_inclination_rad: float


@dataclass(frozen=True, slots=True)
class LogEkfQuat:
    """Orientation as unit quaternion with 1-σ accuracy estimates (MSG 0x07)."""

    timestamp_us: int
    q0: float
    """Scalar (W) component."""
    q1: float
    """X component."""
    q2: float
    """Y component."""
    q3: float
    """Z component."""
    roll_std_rad: float
    pitch_std_rad: float
    yaw_std_rad: float
    solution_status: int
    magnetic_declination_rad: float
    magnetic_inclination_rad: float


@dataclass(frozen=True, slots=True)
class LogEkfNav:
    """Full INS navigation solution — velocity + position (MSG 0x08)."""

    timestamp_us: int
    velocity_n_ms: float
    """North velocity in m/s (NED frame)."""
    velocity_e_ms: float
    """East velocity in m/s."""
    velocity_d_ms: float
    """Down velocity in m/s."""
    velocity_n_std_ms: float
    velocity_e_std_ms: float
    velocity_d_std_ms: float
    latitude_deg: float
    """WGS84 latitude in degrees (North positive)."""
    longitude_deg: float
    """WGS84 longitude in degrees (East positive)."""
    altitude_m: float
    """Altitude above mean sea level in metres."""
    undulation_m: float
    """Geoid-ellipsoid separation in metres."""
    latitude_std_m: float
    longitude_std_m: float
    altitude_std_m: float
    solution_status: int


@dataclass(frozen=True, slots=True)
class LogEkfVelBody:
    """INS velocity expressed in the body frame (MSG 0x36)."""

    timestamp_us: int
    solution_status: int
    velocity_x_ms: float
    """Forward (body X) velocity in m/s."""
    velocity_y_ms: float
    """Rightward (body Y) velocity in m/s."""
    velocity_z_ms: float
    """Downward (body Z) velocity in m/s."""
    velocity_x_std_ms: float
    velocity_y_std_ms: float
    velocity_z_std_ms: float


@dataclass(frozen=True, slots=True)
class LogEkfRotAccelBody:
    """EKF rotation rates and accelerations in the body frame (MSG 0x34)."""

    timestamp_us: int
    solution_status: int
    rate_x_rads: float
    rate_y_rads: float
    rate_z_rads: float
    accel_x_ms2: float
    accel_y_ms2: float
    accel_z_ms2: float


@dataclass(frozen=True, slots=True)
class LogEkfRotAccelNed:
    """EKF rotation rates and accelerations in the NED frame (MSG 0x35)."""

    timestamp_us: int
    solution_status: int
    rate_n_rads: float
    rate_e_rads: float
    rate_d_rads: float
    accel_n_ms2: float
    accel_e_ms2: float
    accel_d_ms2: float


@dataclass(frozen=True, slots=True)
class LogEkfAirData:
    """INS-computed wind velocity from air data aiding (MSG 0x3D)."""

    timestamp_us: int
    status: int
    wind_n_ms: float
    wind_e_ms: float
    wind_d_ms: float
    wind_n_std_ms: float
    wind_e_std_ms: float
    wind_d_std_ms: float
