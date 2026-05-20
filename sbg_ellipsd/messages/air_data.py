from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogAirData:
    """Air data — barometric altitude, differential pressure and airspeed (MSG 0x24)."""

    timestamp_us: int
    """Time in microseconds (µs from power-up) or milliseconds (GPS ToW)."""

    status: int
    """Validity and time-type flags."""

    pressure_abs_pa: float
    """Absolute barometric pressure in Pascal."""

    altitude_m: float
    """Barometric altitude in metres."""

    pressure_diff_pa: float
    """Pitot differential pressure in Pascal."""

    true_airspeed_ms: float
    """True airspeed in m/s."""

    air_temperature_c: float
    """Outside air temperature in °C."""
