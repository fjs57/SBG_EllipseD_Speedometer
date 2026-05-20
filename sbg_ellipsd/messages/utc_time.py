from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogUtcTime:
    """UTC time with GPS/internal clock synchronisation data (MSG 0x02)."""

    timestamp_us: int
    """Time since device power-up in microseconds."""

    time_status: int
    """Clock sync and UTC validity flags — interpret with :class:`~sbg_ellipsd.enums.UtcStatus`."""

    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    """Seconds [0–60]; 60 indicates a leap second."""

    nanosecond: int
    """Sub-second precision in nanoseconds."""

    gps_time_of_week_ms: int
    """GPS time of week in milliseconds."""

    clock_bias_std_s: float
    """1-σ standard deviation of clock bias in seconds."""

    clock_scale_factor_error_std_pct: float
    """1-σ standard deviation of clock scale factor error in percent."""

    clock_residual_error_s: float
    """GNSS PPS vs internal clock residual error in seconds."""
