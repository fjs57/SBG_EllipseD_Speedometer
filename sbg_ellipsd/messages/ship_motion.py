from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogShipMotion:
    """Marine heave, surge, sway and motion outputs (MSG 0x09).

    On ELLIPSE devices only ``heave_m``, ``accel_z_ms2``, ``vel_z_ms`` and
    ``heave_period_s`` are populated; all other fields are zero.
    """

    timestamp_us: int
    heave_period_s: float
    """Dominant heave period in seconds."""
    surge_m: float
    """Longitudinal displacement in metres (forward positive)."""
    sway_m: float
    """Lateral displacement in metres (right positive)."""
    heave_m: float
    """Vertical displacement in metres (down positive)."""
    accel_x_ms2: float
    accel_y_ms2: float
    accel_z_ms2: float
    vel_x_ms: float
    vel_y_ms: float
    vel_z_ms: float
    status: int
    """Ship motion validity flags — interpret with
    :class:`~sbg_ellipsd.enums.ShipMotionStatus`."""


@dataclass(frozen=True, slots=True)
class LogShipMotionHp:
    """High-performance INS ship motion with 150-second delayed heave (MSG 0x20)."""

    timestamp_us: int
    heave_period_s: float
    surge_m: float
    sway_m: float
    heave_m: float
    """150-second delayed heave in metres."""
    accel_x_ms2: float
    accel_y_ms2: float
    accel_z_ms2: float
    vel_x_ms: float
    vel_y_ms: float
    vel_z_ms: float
    """Delayed vertical velocity in m/s."""
    status: int
