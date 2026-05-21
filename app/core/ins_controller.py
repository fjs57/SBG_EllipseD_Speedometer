"""Bridge between :class:`~sbg_ellipsd.EllipsDInterface` and the Qt event loop.

All SBG callbacks run on the serial reader thread.  This class re-emits the
relevant data as Qt signals, which Qt delivers safely to the main thread via
the queued-connection mechanism.

Body-frame convention (X = forward, Y = right, Z = down):
  Forward speed = ``LogEkfVelBody.velocity_x_ms``
"""

from __future__ import annotations

import logging

from PyQt5.QtCore import QObject, pyqtSignal

from sbg_ellipsd import EllipsDInterface
from sbg_ellipsd.messages.ekf import LogEkfVelBody, LogEkfNav
from sbg_ellipsd.messages.diagnostics import LogDiag

_log = logging.getLogger(__name__)

# TRACE level (level 5, below DEBUG)
_TRACE = 5


class INSController(QObject):
    """Thin adapter: SBG callbacks → PyQt5 signals."""

    # Emitted at the EKF body-velocity update rate (typically 25–200 Hz)
    speed_updated = pyqtSignal(float)
    """Forward speed in m/s (body-frame X component, always ≥ 0)."""

    # Emitted at the EKF navigation update rate (typically 1–25 Hz)
    nav_updated = pyqtSignal(float, float, float, int)
    """(latitude_deg, longitude_deg, altitude_m, solution_status_raw)"""

    diag_received = pyqtSignal(str, int)
    """(message_text, diag_type_int) — forwarded from LOG_DIAG."""

    # Fired on every received SBG frame (any type) for the activity indicator
    message_received = pyqtSignal()

    def __init__(self, port: str, baudrate: int, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._ins = EllipsDInterface(port, baudrate)
        self._speed_ms: float = 0.0
        self._lat: float = 0.0
        self._lon: float = 0.0
        self._alt: float = 0.0
        self._solution_status: int = 0
        self._setup_listeners()

    # ── Public interface ──────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open the serial port and start the reader thread."""
        _log.info("Connecting to %s ...", self._ins._port)
        self._ins.connect()

    def disconnect(self) -> None:
        """Stop the reader thread and close the serial port."""
        _log.info("Disconnecting.")
        self._ins.disconnect()

    @property
    def is_connected(self) -> bool:
        return self._ins.is_connected

    @property
    def speed_ms(self) -> float:
        return self._speed_ms

    @property
    def latitude_deg(self) -> float:
        return self._lat

    @property
    def longitude_deg(self) -> float:
        return self._lon

    @property
    def altitude_m(self) -> float:
        return self._alt

    @property
    def solution_status(self) -> int:
        return self._solution_status

    # ── Private callbacks (called on the reader thread) ───────────────────────

    def _setup_listeners(self) -> None:
        # Body-frame velocity → speed display (high rate)
        self._ins.add_listener_log_ekf_vel_body(self._on_vel_body)
        # NED navigation solution → GPS panel (lower rate)
        self._ins.add_listener_log_ekf_nav(self._on_ekf_nav)
        # Diagnostic messages → status bar / console
        self._ins.add_listener_log_diag(self._on_diag)

    def _on_vel_body(self, msg: LogEkfVelBody) -> None:
        # Body frame: X = forward.  Negative = reversing; sign is preserved so
        # the data logger can record it.  The gauge and plot take abs() themselves.
        speed = msg.velocity_x_ms
        self._speed_ms = speed
        _log.log(_TRACE, "VEL_BODY  vx=%.4f  vy=%.4f  vz=%.4f m/s",
                 msg.velocity_x_ms, msg.velocity_y_ms, msg.velocity_z_ms)
        self.speed_updated.emit(speed)
        self.message_received.emit()

    def _on_ekf_nav(self, msg: LogEkfNav) -> None:
        self._lat = msg.latitude_deg
        self._lon = msg.longitude_deg
        self._alt = msg.altitude_m
        self._solution_status = msg.solution_status
        mode = msg.solution_status & 0x0F
        _log.log(_TRACE,
                 "EKF_NAV  lat=%.7f  lon=%.7f  alt=%.2f m  mode=%d",
                 msg.latitude_deg, msg.longitude_deg, msg.altitude_m, mode)
        self.nav_updated.emit(msg.latitude_deg, msg.longitude_deg,
                              msg.altitude_m, msg.solution_status)
        self.message_received.emit()

    def _on_diag(self, msg: LogDiag) -> None:
        level_map = {0: logging.ERROR, 1: logging.WARNING,
                     2: logging.INFO,  3: logging.DEBUG}
        py_level = level_map.get(msg.diag_type, logging.INFO)
        _log.log(py_level, "[INS DIAG] %s", msg.message)
        self.diag_received.emit(msg.message, msg.diag_type)
        self.message_received.emit()
