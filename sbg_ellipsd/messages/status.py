from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogStatus:
    """Device health, communication and aiding reception status (MSG 0x01)."""

    timestamp_us: int
    """Time since device power-up in microseconds."""

    general_status: int
    """Device health flags — interpret with :class:`~sbg_ellipsd.enums.GeneralStatus`."""

    com_status_2: int
    """Ethernet interface status — interpret with :class:`~sbg_ellipsd.enums.ComStatus2`."""

    com_status: int
    """Serial/CAN port status — interpret with :class:`~sbg_ellipsd.enums.ComStatus`."""

    aiding_status: int
    """External aiding reception flags — interpret with :class:`~sbg_ellipsd.enums.AidingStatus`."""

    uptime_s: int
    """System uptime in seconds."""

    cpu_usage_pct: int
    """CPU usage in percent (0–100)."""
