from enum import IntEnum, IntFlag


class GpsSolStatus(IntEnum):
    """Solution status — bits [0-5] of the STATUS_TYPE field."""
    SOL_COMPUTED      = 0
    INSUFFICIENT_OBS  = 1
    INTERNAL_ERROR    = 2
    HEIGHT_LIMIT      = 3


class GpsPosType(IntEnum):
    """Position fix type — bits [6-11] of the STATUS_TYPE field."""
    NO_SOLUTION  = 0
    UNKNOWN      = 1
    SINGLE       = 2
    PSRDIFF      = 3
    SBAS         = 4
    OMNISTAR     = 5
    RTK_FLOAT    = 6
    RTK_INT      = 7
    PPP_FLOAT    = 8
    PPP_INT      = 9


class GpsVelType(IntEnum):
    """Velocity type — bits [6-11] of the STATUS_TYPE field."""
    NO_SOLUTION  = 0
    UNKNOWN      = 1
    DOPPLER      = 2
    DIFFERENTIAL = 3


class GpsHdtStatus(IntFlag):
    """Heading solution status flags (STATUS field of HDT messages)."""
    HDT_VALID       = 0x0001
    BASELINE_VALID  = 0x0002
    HEADING_OK      = 0x0004
    PITCH_OK        = 0x0008


class GpsPosSignals(IntFlag):
    """Tracked signal constellations — bits [12-29] of STATUS_TYPE."""
    GPS_L1     = 0x00001000
    GPS_L2     = 0x00002000
    GPS_L5     = 0x00004000
    GLONASS_L1 = 0x00008000
    GLONASS_L2 = 0x00010000
    BEIDOU_B1  = 0x00020000
    BEIDOU_B2  = 0x00040000
    GALILEO_E1 = 0x00080000
    GALILEO_E5 = 0x00100000
