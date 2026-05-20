from enum import IntFlag


class ImuStatus(IntFlag):
    COM_OK             = 0x0001
    STATUS_OK          = 0x0002
    ACCEL_X_OK         = 0x0004
    ACCEL_Y_OK         = 0x0008
    ACCEL_Z_OK         = 0x0010
    GYRO_X_OK          = 0x0020
    GYRO_Y_OK          = 0x0040
    GYRO_Z_OK          = 0x0080
    ACCELS_IN_RANGE    = 0x0100
    GYROS_IN_RANGE     = 0x0200
    GYROS_HIGH_SCALE   = 0x0400
