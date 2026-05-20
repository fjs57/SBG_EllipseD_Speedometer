"""sbg_ellipsd — Python driver for the SBG Systems ELLIPS-D INS.

Typical usage::

    from sbg_ellipsd import EllipsDInterface

    ins = EllipsDInterface("COM3", 115200)
    ins.add_listener_log_ekf_nav(lambda m: print(m.latitude_deg, m.longitude_deg))

    with ins:
        input("Press Enter to stop…")

All message dataclasses and enums are re-exported from this namespace for
convenience.
"""

from .interface import EllipsDInterface
from .messages import (
    LogStatus, LogUtcTime,
    LogImuShort, LogImuData,
    LogMag, LogMagCalib,
    LogEkfEuler, LogEkfQuat, LogEkfNav, LogEkfVelBody,
    LogEkfRotAccelBody, LogEkfRotAccelNed, LogEkfAirData,
    LogShipMotion, LogShipMotionHp,
    LogGps1Vel, LogGps1Pos, LogGps1Hdt,
    LogGps2Vel, LogGps2Pos, LogGps2Hdt,
    LogGps1Raw, LogGps2Raw, LogGps1Sat, LogGps2Sat,
    SatInfo, SignalInfo,
    LogEventA, LogEventB, LogEventC, LogEventD, LogEventE,
    LogEventOutA, LogEventOutB,
    LogDvlBottomTrack, LogDvlWaterTrack,
    LogAirData, LogUsbl, LogOdoVel, LogDepth,
    LogPosition1, LogVelocity1,
    LogPtpStatus, LogDiag, LogSessionInfo, LogRtcmRaw,
    LogVibMonFft, LogVibMonReport,
)
from .enums import (
    GeneralStatus, SolutionMode, DiagType,
    ComStatus, ComStatus2,
    AidingStatus,
    EkfSolutionFlags,
    GpsSolStatus, GpsPosType, GpsVelType, GpsHdtStatus, GpsPosSignals,
    ImuStatus,
    MagStatus, MagCalibMode,
    ShipMotionStatus,
    EventStatus,
    UtcStatus, ClockSource,
)

__all__ = [
    "EllipsDInterface",
    # Messages
    "LogStatus", "LogUtcTime",
    "LogImuShort", "LogImuData",
    "LogMag", "LogMagCalib",
    "LogEkfEuler", "LogEkfQuat", "LogEkfNav", "LogEkfVelBody",
    "LogEkfRotAccelBody", "LogEkfRotAccelNed", "LogEkfAirData",
    "LogShipMotion", "LogShipMotionHp",
    "LogGps1Vel", "LogGps1Pos", "LogGps1Hdt",
    "LogGps2Vel", "LogGps2Pos", "LogGps2Hdt",
    "LogGps1Raw", "LogGps2Raw", "LogGps1Sat", "LogGps2Sat",
    "SatInfo", "SignalInfo",
    "LogEventA", "LogEventB", "LogEventC", "LogEventD", "LogEventE",
    "LogEventOutA", "LogEventOutB",
    "LogDvlBottomTrack", "LogDvlWaterTrack",
    "LogAirData", "LogUsbl", "LogOdoVel", "LogDepth",
    "LogPosition1", "LogVelocity1",
    "LogPtpStatus", "LogDiag", "LogSessionInfo", "LogRtcmRaw",
    "LogVibMonFft", "LogVibMonReport",
    # Enums
    "GeneralStatus", "SolutionMode", "DiagType",
    "ComStatus", "ComStatus2",
    "AidingStatus",
    "EkfSolutionFlags",
    "GpsSolStatus", "GpsPosType", "GpsVelType", "GpsHdtStatus", "GpsPosSignals",
    "ImuStatus",
    "MagStatus", "MagCalibMode",
    "ShipMotionStatus",
    "EventStatus",
    "UtcStatus", "ClockSource",
]
