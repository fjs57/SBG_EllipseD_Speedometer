from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogDiag:
    """Device diagnostic message — error, warning, info or debug (MSG 0x30)."""

    timestamp_us: int
    diag_type: int
    """Message severity — interpret with :class:`~sbg_ellipsd.enums.DiagType`."""
    error_code: int
    message: str
    """Decoded ASCII message string."""
