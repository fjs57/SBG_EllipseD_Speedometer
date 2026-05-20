from enum import IntEnum, IntFlag


class UtcStatus(IntFlag):
    CLOCK_STABLE      = 0x0001
    CLOCK_CONVERGED   = 0x0002
    CLOCK_INTERNAL    = 0x0004
    UTC_VALID         = 0x0008
    TOW_VALID         = 0x0010
    WEEK_VALID        = 0x0020
    UTC_SET_BY_USER   = 0x0040
    BIAS_VALID        = 0x0080
    PTP_VALID         = 0x0100


class ClockSource(IntEnum):
    INTERNAL = 0
    GPS      = 1
    PTP      = 2
    GNSS     = 3
