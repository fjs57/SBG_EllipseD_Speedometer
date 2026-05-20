from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogPosition1:
    """External position aiding input with full 3×3 covariance matrix (MSG 0x3E)."""

    timestamp_us: int
    status: int
    latitude_deg: float
    longitude_deg: float
    height_m: float
    """Height above the WGS84 ellipsoid in metres."""
    cov_lat_lat_m2: float
    cov_lon_lon_m2: float
    cov_height_height_m2: float
    cov_lat_lon_m2: float
    cov_lat_height_m2: float
    cov_lon_height_m2: float
