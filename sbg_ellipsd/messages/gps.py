from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogGps1Vel:
    """GPS receiver 1 velocity solution (MSG 0x0D).

    Use :class:`~sbg_ellipsd.enums.GpsSolStatus` for bits [0-5] and
    :class:`~sbg_ellipsd.enums.GpsVelType` for bits [6-11] of ``status_type``.
    """

    timestamp_us: int
    status_type: int
    time_of_week_ms: int
    velocity_n_ms: float
    velocity_e_ms: float
    velocity_d_ms: float
    velocity_n_std_ms: float
    velocity_e_std_ms: float
    velocity_d_std_ms: float
    course_deg: float
    """True ground track in degrees."""
    course_std_deg: float


@dataclass(frozen=True, slots=True)
class LogGps1Pos:
    """GPS receiver 1 position solution (MSG 0x0E).

    Use :class:`~sbg_ellipsd.enums.GpsSolStatus` for bits [0-5] and
    :class:`~sbg_ellipsd.enums.GpsPosType` for bits [6-11] of ``status_type``.
    """

    timestamp_us: int
    status_type: int
    time_of_week_ms: int
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    undulation_m: float
    latitude_std_m: float
    longitude_std_m: float
    altitude_std_m: float
    num_sv_used: int
    """Number of satellites used in the solution (255 = not available)."""
    base_station_id: int
    """DGPS/RTK base station ID (65535 = not available)."""
    differential_age_s: float
    """Age of differential corrections in seconds."""
    num_sv_tracked: int
    """Number of tracked satellites (255 = not available)."""
    status_ext: int
    """Extended status — interference/spoofing indicators."""
    nr_diagnostic_reboots: int
    receiver_uptime_s: int


@dataclass(frozen=True, slots=True)
class LogGps1Hdt:
    """GPS receiver 1 dual-antenna heading (MSG 0x0F)."""

    timestamp_us: int
    status: int
    """Heading flags — interpret with :class:`~sbg_ellipsd.enums.GpsHdtStatus`."""
    time_of_week_ms: int
    true_heading_deg: float
    true_heading_std_deg: float
    pitch_deg: float
    pitch_std_deg: float
    baseline_m: float
    num_sv_tracked: int
    num_sv_used: int


@dataclass(frozen=True, slots=True)
class LogGps2Vel:
    """GPS receiver 2 velocity solution (MSG 0x10) — identical structure to LogGps1Vel."""

    timestamp_us: int
    status_type: int
    time_of_week_ms: int
    velocity_n_ms: float
    velocity_e_ms: float
    velocity_d_ms: float
    velocity_n_std_ms: float
    velocity_e_std_ms: float
    velocity_d_std_ms: float
    course_deg: float
    course_std_deg: float


@dataclass(frozen=True, slots=True)
class LogGps2Pos:
    """GPS receiver 2 position solution (MSG 0x11) — identical structure to LogGps1Pos."""

    timestamp_us: int
    status_type: int
    time_of_week_ms: int
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    undulation_m: float
    latitude_std_m: float
    longitude_std_m: float
    altitude_std_m: float
    num_sv_used: int
    base_station_id: int
    differential_age_s: float
    num_sv_tracked: int
    status_ext: int
    nr_diagnostic_reboots: int
    receiver_uptime_s: int


@dataclass(frozen=True, slots=True)
class LogGps2Hdt:
    """GPS receiver 2 dual-antenna heading (MSG 0x12) — identical structure to LogGps1Hdt."""

    timestamp_us: int
    status: int
    time_of_week_ms: int
    true_heading_deg: float
    true_heading_std_deg: float
    pitch_deg: float
    pitch_std_deg: float
    baseline_m: float
    num_sv_tracked: int
    num_sv_used: int
