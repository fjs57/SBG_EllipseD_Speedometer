from enum import IntEnum, IntFlag


class MagStatus(IntFlag):
    MAG_X_OK          = 0x0001
    MAG_Y_OK          = 0x0002
    MAG_Z_OK          = 0x0004
    MAG_IN_RANGE      = 0x0008
    MAG_CALIB_VALID   = 0x0010
    MAG_USED_FOR_HDT  = 0x0020
    ACCEL_X_OK        = 0x0040
    ACCEL_Y_OK        = 0x0080
    ACCEL_Z_OK        = 0x0100
    ACCEL_IN_RANGE    = 0x0200
    # Bits [10-11]: calibration mode
    # Bits [12-13]: time source


class MagCalibMode(IntEnum):
    NONE     = 0
    TWO_D    = 1
    THREE_D  = 2
