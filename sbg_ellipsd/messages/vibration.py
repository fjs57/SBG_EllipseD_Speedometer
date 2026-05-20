from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogVibMonFft:
    """Vibration monitoring FFT spectrum (MSG 0x3B).

    The binary layout depends on the device configuration; raw bytes are
    forwarded for application-level decoding.
    """

    raw_data: bytes


@dataclass(frozen=True, slots=True)
class LogVibMonReport:
    """Vibration monitoring summary report (MSG 0x3C)."""

    raw_data: bytes
