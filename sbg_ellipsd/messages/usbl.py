from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogUsbl:
    """Ultra-short baseline underwater positioning (MSG 0x25).

    Note: USBL aiding is currently not used by the INS filter.
    """

    timestamp_us: int
    status: int
    latitude_deg: float
    longitude_deg: float
    depth_m: float
    """Depth below mean sea level in metres (down positive)."""
    latitude_std_m: float
    longitude_std_m: float
    depth_std_m: float
    information_age_us: int
    """Age of the USBL measurement in microseconds."""
