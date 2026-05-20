from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class LogGps1Raw:
    """Raw GNSS receiver 1 binary data passthrough (MSG 0x1F).

    The payload is forwarded untouched; the application is responsible
    for decoding the proprietary receiver format.
    """

    raw_data: bytes


@dataclass(frozen=True, slots=True)
class LogGps2Raw:
    """Raw GNSS receiver 2 binary data passthrough (MSG 0x26)."""

    raw_data: bytes


@dataclass(frozen=True, slots=True)
class SignalInfo:
    """Per-signal tracking data within a satellite record."""

    signal_id: int
    flags: int
    snr_db: int


@dataclass(frozen=True, slots=True)
class SatInfo:
    """Per-satellite tracking data."""

    satellite_id: int
    elevation_deg: int
    """Elevation in degrees [-90, +90]."""
    azimuth_deg: int
    """Azimuth in degrees [0, 359]."""
    flags: int
    signals: tuple[SignalInfo, ...]


@dataclass(frozen=True, slots=True)
class LogGps1Sat:
    """GPS receiver 1 satellite tracking information (MSG 0x32)."""

    timestamp_us: int
    satellites: tuple[SatInfo, ...]


@dataclass(frozen=True, slots=True)
class LogGps2Sat:
    """GPS receiver 2 satellite tracking information (MSG 0x33)."""

    timestamp_us: int
    satellites: tuple[SatInfo, ...]
