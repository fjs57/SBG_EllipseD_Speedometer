"""CSV data logger — writes speed, GPS position and decoded INS solution status.

Files are stored in the ``log/`` directory by default (see
:data:`~app.config.LOG_DIR`).  The directory is created automatically on the
first :meth:`DataLogger.start` call if it does not yet exist.
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path

from app.config import LOG_DIR

_log = logging.getLogger(__name__)


def _resolve_log_dir() -> Path:
    """Return the absolute path of the log directory.

    When running as a PyInstaller bundle (``sys.frozen`` is set) the directory
    is placed next to the ``.exe`` so that it is always in a user-writable
    location regardless of where the user launched the application from.

    In development mode the directory is relative to the current working
    directory (project root).
    """
    import sys as _sys
    if getattr(_sys, "frozen", False):
        base = Path(_sys.executable).resolve().parent
    else:
        base = Path.cwd()
    return base / LOG_DIR


_LOG_DIR = _resolve_log_dir()

# ── Solution-status decoding ──────────────────────────────────────────────────

_SOLUTION_MODES: dict[int, str] = {
    0: "UNINITIALIZED",
    1: "VERTICAL_GYRO",
    2: "AHRS",
    3: "NAV_VELOCITY",
    4: "NAV_POSITION",
}

# (column_name, bit_mask) for every flag field
_STATUS_FLAGS: tuple[tuple[str, int], ...] = (
    # Validity
    ("attitude_valid",   0x00000010),
    ("heading_valid",    0x00000020),
    ("velocity_valid",   0x00000040),
    ("position_valid",   0x00000080),
    ("align_valid",      0x08000000),
    # Active aiding sources
    ("vert_ref_used",    0x00000100),
    ("mag_ref_used",     0x00000200),
    ("gps1_vel_used",    0x00000400),
    ("gps1_pos_used",    0x00000800),
    ("gps1_hdt_used",    0x00002000),
    ("gps2_vel_used",    0x00004000),
    ("gps2_pos_used",    0x00008000),
    ("gps2_hdt_used",    0x00020000),
    ("odo_used",         0x00040000),
    ("dvl_bt_used",      0x00080000),
    ("dvl_wt_used",      0x00100000),
    ("vel1_used",        0x00200000),
    ("usbl_used",        0x01000000),
    ("airspeed_used",    0x02000000),
    ("zupt_used",        0x04000000),
    ("zaru_used",        0x20000000),
    ("pos1_used",        0x40000000),
)


def _decode_solution(status: int) -> list[str]:
    """Return one CSV cell per decoded field (mode text + one 0/1 per flag)."""
    mode = _SOLUTION_MODES.get(status & 0x0F, f"UNKNOWN_{status & 0x0F}")
    flags = [str(int(bool(status & mask))) for _, mask in _STATUS_FLAGS]
    return [mode] + flags


# ── CSV header ────────────────────────────────────────────────────────────────

_HEADER: list[str] = [
    "timestamp_iso",
    "elapsed_s",
    "speed_ms",
    "speed_kmh",
    "latitude_deg",
    "longitude_deg",
    "altitude_m",
    # Decoded solution_status fields — one column per field
    "solution_mode",
    *[name for name, _ in _STATUS_FLAGS],
]


# ── Logger class ──────────────────────────────────────────────────────────────

class DataLogger:
    """Append-mode CSV logger.

    Usage::

        logger = DataLogger()
        path = logger.start("run_01")      # returns the resolved file path
        logger.record(speed_ms, lat, lon, alt, sol_status)
        logger.stop()
    """

    def __init__(self) -> None:
        self._file = None
        self._writer: csv.writer | None = None
        self._active = False
        self._start_time: datetime | None = None
        self._file_path: Path | None = None

    # ── Public interface ──────────────────────────────────────────────────────

    def start(self, name: str) -> str:
        """Open (or create) the log file.

        Args:
            name: Base filename (with or without extension, with or without a
                  directory component).  If *name* has no directory part the
                  file is placed in :data:`~app.config.LOG_DIR` (``log/``).
                  The ``.csv`` extension is appended automatically when absent.

        Returns:
            The absolute path of the file that was opened.
        """
        if self._active:
            self.stop()

        path = Path(name)
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")

        if not path.parent.name or path.parent == Path("."):
            path = _LOG_DIR / path.name

        path.parent.mkdir(parents=True, exist_ok=True)

        self._file = open(path, "w", newline="", encoding="utf-8")  # noqa: SIM115
        self._writer = csv.writer(self._file)
        self._writer.writerow(_HEADER)
        self._start_time = datetime.now()
        self._file_path = path.resolve()
        self._active = True

        _log.info("Logging started -> %s", self._file_path)
        return str(self._file_path)

    def record(
        self,
        speed_ms: float,
        latitude_deg: float,
        longitude_deg: float,
        altitude_m: float,
        solution_status: int,
    ) -> None:
        """Append one data row; silently ignored when the logger is stopped."""
        if not self._active or self._writer is None:
            return

        now = datetime.now()
        elapsed = (now - self._start_time).total_seconds()

        self._writer.writerow([
            now.isoformat(timespec="milliseconds"),
            f"{elapsed:.3f}",
            f"{speed_ms:.4f}",
            f"{speed_ms * 3.6:.4f}",
            f"{latitude_deg:.7f}",
            f"{longitude_deg:.7f}",
            f"{altitude_m:.3f}",
            *_decode_solution(solution_status),
        ])
        self._file.flush()

    def stop(self) -> str | None:
        """Close the log file.

        Returns:
            The path of the file that was closed, or ``None`` if inactive.
        """
        if not self._active:
            return None
        path = str(self._file_path)
        self._file.close()
        self._active = False
        self._file = None
        self._writer = None
        _log.info("Logging stopped -> %s", path)
        return path

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def file_path(self) -> str | None:
        return str(self._file_path) if self._file_path else None
