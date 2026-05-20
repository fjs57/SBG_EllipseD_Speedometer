from enum import IntEnum, IntFlag


class GeneralStatus(IntFlag):
    MAIN_POWER_OK  = 0x0001
    IMU_POWER_OK   = 0x0002
    GPS_POWER_OK   = 0x0004
    SETTINGS_OK    = 0x0008
    TEMPERATURE_OK = 0x0010
    DATALOGGER_OK  = 0x0020
    CPU_OK         = 0x0040


class SolutionMode(IntEnum):
    UNINITIALIZED = 0
    VERTICAL_GYRO = 1
    AHRS          = 2
    NAV_VELOCITY  = 3
    NAV_POSITION  = 4


class DiagType(IntEnum):
    ERROR   = 0
    WARNING = 1
    INFO    = 2
    DEBUG   = 3
