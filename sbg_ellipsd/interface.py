from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any

import serial
import serial.serialutil

from .protocol import constants as _c
from .protocol.constants import CLASS_LOG
from .protocol.framer import FrameReader
from .protocol.parser import FrameParser
from .messages.status import LogStatus
from .messages.utc_time import LogUtcTime
from .messages.imu import LogImuShort, LogImuData
from .messages.magnetometer import LogMag, LogMagCalib
from .messages.ekf import (
    LogEkfEuler, LogEkfQuat, LogEkfNav, LogEkfVelBody,
    LogEkfRotAccelBody, LogEkfRotAccelNed, LogEkfAirData,
)
from .messages.ship_motion import LogShipMotion, LogShipMotionHp
from .messages.gps import LogGps1Vel, LogGps1Pos, LogGps1Hdt, LogGps2Vel, LogGps2Pos, LogGps2Hdt
from .messages.gps_raw import LogGps1Raw, LogGps2Raw, LogGps1Sat, LogGps2Sat
from .messages.events import (
    LogEventA, LogEventB, LogEventC, LogEventD, LogEventE,
    LogEventOutA, LogEventOutB,
)
from .messages.dvl import LogDvlBottomTrack, LogDvlWaterTrack
from .messages.air_data import LogAirData
from .messages.usbl import LogUsbl
from .messages.odometer import LogOdoVel
from .messages.depth import LogDepth
from .messages.position import LogPosition1
from .messages.velocity import LogVelocity1
from .messages.ptp import LogPtpStatus
from .messages.diagnostics import LogDiag
from .messages.session_info import LogSessionInfo
from .messages.rtcm import LogRtcmRaw
from .messages.vibration import LogVibMonFft, LogVibMonReport

_log = logging.getLogger(__name__)


class EllipsDInterface:
    """Serial driver for the SBG Systems ELLIPS-D INS.

    Opens a COM port, reads the SBG ECom binary stream in a background thread,
    parses each frame, and dispatches typed dataclass instances to registered
    callbacks.

    Callbacks are invoked **on the reader thread**. If your application uses a
    GUI event loop (Qt, tkinter…) enqueue messages via ``queue.Queue`` inside
    your callback and process them in your main thread.

    Usage::

        ins = EllipsDInterface("COM3", 115200)
        ins.add_listener_log_ekf_nav(lambda m: print(m.latitude_deg, m.longitude_deg))

        with ins:
            input("Press Enter to stop…")
    """

    def __init__(self, port: str, baudrate: int) -> None:
        self._port = port
        self._baudrate = baudrate
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._listeners: dict[int, set[Callable[..., None]]] = {}

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open the serial port and start the background reader thread."""
        if self._serial and self._serial.is_open:
            return
        self._serial = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,
            rtscts=False,    # disable hardware flow control
            xonxoff=False,   # disable software flow control
        )
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._reader_loop, name="sbg-reader", daemon=True,
        )
        self._thread.start()

    def disconnect(self) -> None:
        """Stop the reader thread and close the serial port."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None

    def __enter__(self) -> "EllipsDInterface":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()

    @property
    def is_connected(self) -> bool:
        """``True`` when the serial port is open and the reader thread is alive."""
        return self._serial is not None and self._serial.is_open

    # ── Internal ──────────────────────────────────────────────────────────────

    def _reader_loop(self) -> None:
        assert self._serial is not None
        framer = FrameReader()
        while not self._stop_event.is_set():
            try:
                chunk = self._serial.read(4096)
            except serial.serialutil.SerialException as exc:
                _log.error("Serial read error: %s", exc)
                break
            if chunk:
                framer.feed(chunk)
                for msg_id, msg_class, payload in framer:
                    if msg_class != CLASS_LOG:
                        continue
                    msg = FrameParser.parse(msg_id, payload)
                    if msg is not None:
                        self._dispatch(msg_id, msg)

    def _dispatch(self, msg_id: int, msg: Any) -> None:
        # Snapshot under the lock, then release before calling callbacks.
        # This prevents deadlock if a callback calls add_listener_* itself.
        with self._lock:
            callbacks = frozenset(self._listeners.get(msg_id, ()))
        for cb in callbacks:
            try:
                cb(msg)
            except Exception:
                _log.exception("Listener raised for msg_id=0x%02X", msg_id)

    def _register(self, msg_id: int, callback: Callable[..., None]) -> None:
        with self._lock:
            self._listeners.setdefault(msg_id, set()).add(callback)

    def _unregister(self, msg_id: int, callback: Callable[..., None]) -> None:
        with self._lock:
            self._listeners.get(msg_id, set()).discard(callback)

    # ── Listener registration — one add/remove pair per message type ──────────

    def add_listener_log_status(self, callback: Callable[[LogStatus], None]) -> None:
        self._register(_c.MSG_STATUS, callback)

    def remove_listener_log_status(self, callback: Callable[[LogStatus], None]) -> None:
        self._unregister(_c.MSG_STATUS, callback)

    def add_listener_log_utc_time(self, callback: Callable[[LogUtcTime], None]) -> None:
        self._register(_c.MSG_UTC_TIME, callback)

    def remove_listener_log_utc_time(self, callback: Callable[[LogUtcTime], None]) -> None:
        self._unregister(_c.MSG_UTC_TIME, callback)

    def add_listener_log_imu_data(self, callback: Callable[[LogImuData], None]) -> None:
        self._register(_c.MSG_IMU_DATA, callback)

    def remove_listener_log_imu_data(self, callback: Callable[[LogImuData], None]) -> None:
        self._unregister(_c.MSG_IMU_DATA, callback)

    def add_listener_log_imu_short(self, callback: Callable[[LogImuShort], None]) -> None:
        self._register(_c.MSG_IMU_SHORT, callback)

    def remove_listener_log_imu_short(self, callback: Callable[[LogImuShort], None]) -> None:
        self._unregister(_c.MSG_IMU_SHORT, callback)

    def add_listener_log_mag(self, callback: Callable[[LogMag], None]) -> None:
        self._register(_c.MSG_MAG, callback)

    def remove_listener_log_mag(self, callback: Callable[[LogMag], None]) -> None:
        self._unregister(_c.MSG_MAG, callback)

    def add_listener_log_mag_calib(self, callback: Callable[[LogMagCalib], None]) -> None:
        self._register(_c.MSG_MAG_CALIB, callback)

    def remove_listener_log_mag_calib(self, callback: Callable[[LogMagCalib], None]) -> None:
        self._unregister(_c.MSG_MAG_CALIB, callback)

    def add_listener_log_ekf_euler(self, callback: Callable[[LogEkfEuler], None]) -> None:
        self._register(_c.MSG_EKF_EULER, callback)

    def remove_listener_log_ekf_euler(self, callback: Callable[[LogEkfEuler], None]) -> None:
        self._unregister(_c.MSG_EKF_EULER, callback)

    def add_listener_log_ekf_quat(self, callback: Callable[[LogEkfQuat], None]) -> None:
        self._register(_c.MSG_EKF_QUAT, callback)

    def remove_listener_log_ekf_quat(self, callback: Callable[[LogEkfQuat], None]) -> None:
        self._unregister(_c.MSG_EKF_QUAT, callback)

    def add_listener_log_ekf_nav(self, callback: Callable[[LogEkfNav], None]) -> None:
        self._register(_c.MSG_EKF_NAV, callback)

    def remove_listener_log_ekf_nav(self, callback: Callable[[LogEkfNav], None]) -> None:
        self._unregister(_c.MSG_EKF_NAV, callback)

    def add_listener_log_ekf_vel_body(self, callback: Callable[[LogEkfVelBody], None]) -> None:
        self._register(_c.MSG_EKF_VEL_BODY, callback)

    def remove_listener_log_ekf_vel_body(self, callback: Callable[[LogEkfVelBody], None]) -> None:
        self._unregister(_c.MSG_EKF_VEL_BODY, callback)

    def add_listener_log_ekf_rot_accel_body(self, callback: Callable[[LogEkfRotAccelBody], None]) -> None:
        self._register(_c.MSG_EKF_ROT_ACCEL_BODY, callback)

    def remove_listener_log_ekf_rot_accel_body(self, callback: Callable[[LogEkfRotAccelBody], None]) -> None:
        self._unregister(_c.MSG_EKF_ROT_ACCEL_BODY, callback)

    def add_listener_log_ekf_rot_accel_ned(self, callback: Callable[[LogEkfRotAccelNed], None]) -> None:
        self._register(_c.MSG_EKF_ROT_ACCEL_NED, callback)

    def remove_listener_log_ekf_rot_accel_ned(self, callback: Callable[[LogEkfRotAccelNed], None]) -> None:
        self._unregister(_c.MSG_EKF_ROT_ACCEL_NED, callback)

    def add_listener_log_ekf_air_data(self, callback: Callable[[LogEkfAirData], None]) -> None:
        self._register(_c.MSG_EKF_AIR_DATA, callback)

    def remove_listener_log_ekf_air_data(self, callback: Callable[[LogEkfAirData], None]) -> None:
        self._unregister(_c.MSG_EKF_AIR_DATA, callback)

    def add_listener_log_ship_motion(self, callback: Callable[[LogShipMotion], None]) -> None:
        self._register(_c.MSG_SHIP_MOTION, callback)

    def remove_listener_log_ship_motion(self, callback: Callable[[LogShipMotion], None]) -> None:
        self._unregister(_c.MSG_SHIP_MOTION, callback)

    def add_listener_log_ship_motion_hp(self, callback: Callable[[LogShipMotionHp], None]) -> None:
        self._register(_c.MSG_SHIP_MOTION_HP, callback)

    def remove_listener_log_ship_motion_hp(self, callback: Callable[[LogShipMotionHp], None]) -> None:
        self._unregister(_c.MSG_SHIP_MOTION_HP, callback)

    def add_listener_log_gps1_vel(self, callback: Callable[[LogGps1Vel], None]) -> None:
        self._register(_c.MSG_GPS1_VEL, callback)

    def remove_listener_log_gps1_vel(self, callback: Callable[[LogGps1Vel], None]) -> None:
        self._unregister(_c.MSG_GPS1_VEL, callback)

    def add_listener_log_gps1_pos(self, callback: Callable[[LogGps1Pos], None]) -> None:
        self._register(_c.MSG_GPS1_POS, callback)

    def remove_listener_log_gps1_pos(self, callback: Callable[[LogGps1Pos], None]) -> None:
        self._unregister(_c.MSG_GPS1_POS, callback)

    def add_listener_log_gps1_hdt(self, callback: Callable[[LogGps1Hdt], None]) -> None:
        self._register(_c.MSG_GPS1_HDT, callback)

    def remove_listener_log_gps1_hdt(self, callback: Callable[[LogGps1Hdt], None]) -> None:
        self._unregister(_c.MSG_GPS1_HDT, callback)

    def add_listener_log_gps2_vel(self, callback: Callable[[LogGps2Vel], None]) -> None:
        self._register(_c.MSG_GPS2_VEL, callback)

    def remove_listener_log_gps2_vel(self, callback: Callable[[LogGps2Vel], None]) -> None:
        self._unregister(_c.MSG_GPS2_VEL, callback)

    def add_listener_log_gps2_pos(self, callback: Callable[[LogGps2Pos], None]) -> None:
        self._register(_c.MSG_GPS2_POS, callback)

    def remove_listener_log_gps2_pos(self, callback: Callable[[LogGps2Pos], None]) -> None:
        self._unregister(_c.MSG_GPS2_POS, callback)

    def add_listener_log_gps2_hdt(self, callback: Callable[[LogGps2Hdt], None]) -> None:
        self._register(_c.MSG_GPS2_HDT, callback)

    def remove_listener_log_gps2_hdt(self, callback: Callable[[LogGps2Hdt], None]) -> None:
        self._unregister(_c.MSG_GPS2_HDT, callback)

    def add_listener_log_gps1_raw(self, callback: Callable[[LogGps1Raw], None]) -> None:
        self._register(_c.MSG_GPS1_RAW, callback)

    def remove_listener_log_gps1_raw(self, callback: Callable[[LogGps1Raw], None]) -> None:
        self._unregister(_c.MSG_GPS1_RAW, callback)

    def add_listener_log_gps2_raw(self, callback: Callable[[LogGps2Raw], None]) -> None:
        self._register(_c.MSG_GPS2_RAW, callback)

    def remove_listener_log_gps2_raw(self, callback: Callable[[LogGps2Raw], None]) -> None:
        self._unregister(_c.MSG_GPS2_RAW, callback)

    def add_listener_log_gps1_sat(self, callback: Callable[[LogGps1Sat], None]) -> None:
        self._register(_c.MSG_GPS1_SAT, callback)

    def remove_listener_log_gps1_sat(self, callback: Callable[[LogGps1Sat], None]) -> None:
        self._unregister(_c.MSG_GPS1_SAT, callback)

    def add_listener_log_gps2_sat(self, callback: Callable[[LogGps2Sat], None]) -> None:
        self._register(_c.MSG_GPS2_SAT, callback)

    def remove_listener_log_gps2_sat(self, callback: Callable[[LogGps2Sat], None]) -> None:
        self._unregister(_c.MSG_GPS2_SAT, callback)

    def add_listener_log_odo_vel(self, callback: Callable[[LogOdoVel], None]) -> None:
        self._register(_c.MSG_ODO_VEL, callback)

    def remove_listener_log_odo_vel(self, callback: Callable[[LogOdoVel], None]) -> None:
        self._unregister(_c.MSG_ODO_VEL, callback)

    def add_listener_log_event_a(self, callback: Callable[[LogEventA], None]) -> None:
        self._register(_c.MSG_EVENT_A, callback)

    def remove_listener_log_event_a(self, callback: Callable[[LogEventA], None]) -> None:
        self._unregister(_c.MSG_EVENT_A, callback)

    def add_listener_log_event_b(self, callback: Callable[[LogEventB], None]) -> None:
        self._register(_c.MSG_EVENT_B, callback)

    def remove_listener_log_event_b(self, callback: Callable[[LogEventB], None]) -> None:
        self._unregister(_c.MSG_EVENT_B, callback)

    def add_listener_log_event_c(self, callback: Callable[[LogEventC], None]) -> None:
        self._register(_c.MSG_EVENT_C, callback)

    def remove_listener_log_event_c(self, callback: Callable[[LogEventC], None]) -> None:
        self._unregister(_c.MSG_EVENT_C, callback)

    def add_listener_log_event_d(self, callback: Callable[[LogEventD], None]) -> None:
        self._register(_c.MSG_EVENT_D, callback)

    def remove_listener_log_event_d(self, callback: Callable[[LogEventD], None]) -> None:
        self._unregister(_c.MSG_EVENT_D, callback)

    def add_listener_log_event_e(self, callback: Callable[[LogEventE], None]) -> None:
        self._register(_c.MSG_EVENT_E, callback)

    def remove_listener_log_event_e(self, callback: Callable[[LogEventE], None]) -> None:
        self._unregister(_c.MSG_EVENT_E, callback)

    def add_listener_log_event_out_a(self, callback: Callable[[LogEventOutA], None]) -> None:
        self._register(_c.MSG_EVENT_OUT_A, callback)

    def remove_listener_log_event_out_a(self, callback: Callable[[LogEventOutA], None]) -> None:
        self._unregister(_c.MSG_EVENT_OUT_A, callback)

    def add_listener_log_event_out_b(self, callback: Callable[[LogEventOutB], None]) -> None:
        self._register(_c.MSG_EVENT_OUT_B, callback)

    def remove_listener_log_event_out_b(self, callback: Callable[[LogEventOutB], None]) -> None:
        self._unregister(_c.MSG_EVENT_OUT_B, callback)

    def add_listener_log_dvl_bottom_track(self, callback: Callable[[LogDvlBottomTrack], None]) -> None:
        self._register(_c.MSG_DVL_BOTTOM_TRACK, callback)

    def remove_listener_log_dvl_bottom_track(self, callback: Callable[[LogDvlBottomTrack], None]) -> None:
        self._unregister(_c.MSG_DVL_BOTTOM_TRACK, callback)

    def add_listener_log_dvl_water_track(self, callback: Callable[[LogDvlWaterTrack], None]) -> None:
        self._register(_c.MSG_DVL_WATER_TRACK, callback)

    def remove_listener_log_dvl_water_track(self, callback: Callable[[LogDvlWaterTrack], None]) -> None:
        self._unregister(_c.MSG_DVL_WATER_TRACK, callback)

    def add_listener_log_air_data(self, callback: Callable[[LogAirData], None]) -> None:
        self._register(_c.MSG_AIR_DATA, callback)

    def remove_listener_log_air_data(self, callback: Callable[[LogAirData], None]) -> None:
        self._unregister(_c.MSG_AIR_DATA, callback)

    def add_listener_log_usbl(self, callback: Callable[[LogUsbl], None]) -> None:
        self._register(_c.MSG_USBL, callback)

    def remove_listener_log_usbl(self, callback: Callable[[LogUsbl], None]) -> None:
        self._unregister(_c.MSG_USBL, callback)

    def add_listener_log_depth(self, callback: Callable[[LogDepth], None]) -> None:
        self._register(_c.MSG_DEPTH, callback)

    def remove_listener_log_depth(self, callback: Callable[[LogDepth], None]) -> None:
        self._unregister(_c.MSG_DEPTH, callback)

    def add_listener_log_diag(self, callback: Callable[[LogDiag], None]) -> None:
        self._register(_c.MSG_DIAG, callback)

    def remove_listener_log_diag(self, callback: Callable[[LogDiag], None]) -> None:
        self._unregister(_c.MSG_DIAG, callback)

    def add_listener_log_rtcm_raw(self, callback: Callable[[LogRtcmRaw], None]) -> None:
        self._register(_c.MSG_RTCM_RAW, callback)

    def remove_listener_log_rtcm_raw(self, callback: Callable[[LogRtcmRaw], None]) -> None:
        self._unregister(_c.MSG_RTCM_RAW, callback)

    def add_listener_log_session_info(self, callback: Callable[[LogSessionInfo], None]) -> None:
        self._register(_c.MSG_SESSION_INFO, callback)

    def remove_listener_log_session_info(self, callback: Callable[[LogSessionInfo], None]) -> None:
        self._unregister(_c.MSG_SESSION_INFO, callback)

    def add_listener_log_ptp_status(self, callback: Callable[[LogPtpStatus], None]) -> None:
        self._register(_c.MSG_PTP_STATUS, callback)

    def remove_listener_log_ptp_status(self, callback: Callable[[LogPtpStatus], None]) -> None:
        self._unregister(_c.MSG_PTP_STATUS, callback)

    def add_listener_log_velocity_1(self, callback: Callable[[LogVelocity1], None]) -> None:
        self._register(_c.MSG_VELOCITY_1, callback)

    def remove_listener_log_velocity_1(self, callback: Callable[[LogVelocity1], None]) -> None:
        self._unregister(_c.MSG_VELOCITY_1, callback)

    def add_listener_log_position_1(self, callback: Callable[[LogPosition1], None]) -> None:
        self._register(_c.MSG_POSITION_1, callback)

    def remove_listener_log_position_1(self, callback: Callable[[LogPosition1], None]) -> None:
        self._unregister(_c.MSG_POSITION_1, callback)

    def add_listener_log_vib_mon_fft(self, callback: Callable[[LogVibMonFft], None]) -> None:
        self._register(_c.MSG_VIB_MON_FFT, callback)

    def remove_listener_log_vib_mon_fft(self, callback: Callable[[LogVibMonFft], None]) -> None:
        self._unregister(_c.MSG_VIB_MON_FFT, callback)

    def add_listener_log_vib_mon_report(self, callback: Callable[[LogVibMonReport], None]) -> None:
        self._register(_c.MSG_VIB_MON_REPORT, callback)

    def remove_listener_log_vib_mon_report(self, callback: Callable[[LogVibMonReport], None]) -> None:
        self._unregister(_c.MSG_VIB_MON_REPORT, callback)
