#!/usr/bin/env python3
"""Test script: registers ALL sbg_ellipsd listeners and logs every received message.

Each listener prints the full content of its dataclass to the console.
A periodic statistics report shows the count and approximate rate of every
message type seen since the last report.

Usage (from the project root with the venv activated)::

    python utils/test_listeners.py COM3
    python utils/test_listeners.py COM3 921600
    python utils/test_listeners.py COM3 921600 --verbose DEBUG
    python utils/test_listeners.py /dev/ttyUSB0 --baudrate 115200 -v TRACE

Arguments::

    port           Serial port name (e.g. COM3, /dev/ttyUSB0)
    baudrate       Baud rate (default: 921600)
    --verbose/-v   Log level: TRACE DEBUG INFO WARNING ERROR FATAL  (default: DEBUG)
    --stats/-s     Statistics report interval in seconds             (default: 5)

Log levels per message category::

    TRACE   High-rate IMU / EKF body-frame outputs (>50 Hz)
    DEBUG   EKF attitude, navigation, GPS          (1–25 Hz)
    INFO    Device status, UTC, GPS position/HDT   (<= 1 Hz)
    WARNING/ERROR  Forwarded directly from LOG_DIAG
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
import threading
from collections import defaultdict
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any

# ── Make sbg_ellipsd importable whether or not it is installed ──────────────
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from sbg_ellipsd import EllipsDInterface
    from sbg_ellipsd.messages.diagnostics import LogDiag
except ImportError as _exc:
    sys.exit(
        f"Cannot import sbg_ellipsd: {_exc}\n"
        "Run from the project root with the venv activated:\n"
        "  .venv/Scripts/activate && python utils/test_listeners.py PORT"
    )

# ── Custom TRACE level (below DEBUG = 10) ───────────────────────────────────
TRACE: int = 5
logging.addLevelName(TRACE, "TRACE")


def _inject_trace_method() -> None:
    """Add ``Logger.trace()`` convenience method."""
    def _trace(self: logging.Logger, msg: str, *args, **kw) -> None:
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kw)
    logging.Logger.trace = _trace  # type: ignore[attr-defined]


# ── Logging setup ────────────────────────────────────────────────────────────

_LEVEL_MAP: dict[str, int] = {
    "TRACE":   TRACE,
    "DEBUG":   logging.DEBUG,
    "INFO":    logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR":   logging.ERROR,
    "FATAL":   logging.CRITICAL,
}


def _setup_logging(level_name: str) -> None:
    _inject_trace_method()
    level = _LEVEL_MAP.get(level_name, logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    ))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)


_log = logging.getLogger("test_listeners")

# ── Message statistics ───────────────────────────────────────────────────────

_counts: dict[str, int] = defaultdict(int)      # total received per tag
_counts_window: dict[str, int] = defaultdict(int)  # received in current window
_window_start: float = time.monotonic()


def _log_stats(header: str = "Stats") -> None:
    """Log a one-line summary of message rates for all received types."""
    global _window_start
    now = time.monotonic()
    elapsed = max(0.001, now - _window_start)

    if not _counts_window:
        _log.info("=== %s: no messages received ===", header)
        return

    parts = []
    for tag in sorted(_counts_window):
        rate = _counts_window[tag] / elapsed
        total = _counts[tag]
        parts.append(f"{tag}: {total} total / {rate:.1f} Hz")

    _log.info("=== %s (%.1f s) ===  %s", header, elapsed, "  |  ".join(parts))

    _counts_window.clear()
    _window_start = now


# ── Generic message formatter ────────────────────────────────────────────────

def _fmt_val(name: str, val: Any) -> str:
    """Format a single dataclass field for display."""
    if isinstance(val, float):
        # Higher precision for coordinates and angles
        if any(k in name for k in ("lat", "lon", "deg", "decl", "incl")):
            return f"{val:.7f}"
        if any(k in name for k in ("std", "accuracy", "cov", "bias", "offset")):
            return f"{val:.5e}"
        return f"{val:.5g}"

    if isinstance(val, bytes):
        hex_preview = val[:6].hex()
        suffix = "…" if len(val) > 6 else ""
        return f"[{len(val)}B: {hex_preview}{suffix}]"

    if isinstance(val, (tuple, list)):
        return f"[{len(val)} items]"

    if isinstance(val, str):
        s = val.replace("\n", "\\n")
        return repr(s[:80] + "…" if len(s) > 80 else s)

    if isinstance(val, int) and "status" in name:
        return f"0x{val:08X}"

    return str(val)


def _format_msg(msg: Any) -> str:
    """Return all fields of *msg* as a compact key=value string."""
    return "  ".join(
        f"{f.name}={_fmt_val(f.name, getattr(msg, f.name))}"
        for f in dc_fields(msg)
    )


# ── Callback factory ─────────────────────────────────────────────────────────

def _make_cb(tag: str, level: int = logging.DEBUG):
    """Return a callback that logs *msg* at *level* and increments the counters."""
    logger = logging.getLogger(tag)

    def _callback(msg: Any) -> None:
        _counts[tag] += 1
        _counts_window[tag] += 1
        if logger.isEnabledFor(level):
            logger.log(level, "%-20s  %s", f"[{tag}]", _format_msg(msg))

    return _callback


def _make_diag_cb():
    """Special callback for LOG_DIAG: maps SBG severity to Python log levels."""
    logger = logging.getLogger("DIAG")
    _diag_level = {
        0: logging.ERROR,    # SBG error
        1: logging.WARNING,  # SBG warning
        2: logging.INFO,     # SBG info
        3: logging.DEBUG,    # SBG debug
    }

    def _callback(msg: LogDiag) -> None:
        _counts["DIAG"] += 1
        _counts_window["DIAG"] += 1
        lvl = _diag_level.get(msg.diag_type, logging.INFO)
        logger.log(lvl, "[DIAG]  code=%d  %r", msg.error_code, msg.message)

    return _callback


# ── Listener table ───────────────────────────────────────────────────────────
# (add_listener_name,           display tag,         log level)

_LISTENERS: list[tuple[str, str, int]] = [
    # ── Status & time ──────────────────────────────────────────────────────
    ("log_status",              "STATUS",            logging.INFO),
    ("log_utc_time",            "UTC_TIME",          logging.INFO),
    ("log_ptp_status",          "PTP_STATUS",        logging.INFO),

    # ── IMU (high rate → TRACE) ────────────────────────────────────────────
    ("log_imu_short",           "IMU_SHORT",         TRACE),
    ("log_imu_data",            "IMU_DATA",          TRACE),   # deprecated

    # ── Magnetometer ──────────────────────────────────────────────────────
    ("log_mag",                 "MAG",               logging.DEBUG),
    ("log_mag_calib",           "MAG_CALIB",         logging.DEBUG),

    # ── EKF outputs (moderate rate → DEBUG; body-frame → TRACE) ───────────
    ("log_ekf_euler",           "EKF_EULER",         logging.DEBUG),
    ("log_ekf_quat",            "EKF_QUAT",          logging.DEBUG),
    ("log_ekf_nav",             "EKF_NAV",           logging.DEBUG),
    ("log_ekf_vel_body",        "EKF_VEL_BODY",      TRACE),
    ("log_ekf_rot_accel_body",  "EKF_ROT_BODY",      TRACE),
    ("log_ekf_rot_accel_ned",   "EKF_ROT_NED",       TRACE),
    ("log_ekf_air_data",        "EKF_AIR_DATA",      logging.DEBUG),

    # ── Ship motion ────────────────────────────────────────────────────────
    ("log_ship_motion",         "SHIP_MOTION",       logging.DEBUG),
    ("log_ship_motion_hp",      "SHIP_MOTION_HP",    logging.DEBUG),

    # ── GNSS (low rate → INFO) ─────────────────────────────────────────────
    ("log_gps1_vel",            "GPS1_VEL",          logging.INFO),
    ("log_gps1_pos",            "GPS1_POS",          logging.INFO),
    ("log_gps1_hdt",            "GPS1_HDT",          logging.INFO),
    ("log_gps2_vel",            "GPS2_VEL",          logging.INFO),
    ("log_gps2_pos",            "GPS2_POS",          logging.INFO),
    ("log_gps2_hdt",            "GPS2_HDT",          logging.INFO),
    ("log_gps1_raw",            "GPS1_RAW",          logging.DEBUG),
    ("log_gps2_raw",            "GPS2_RAW",          logging.DEBUG),
    ("log_gps1_sat",            "GPS1_SAT",          logging.DEBUG),
    ("log_gps2_sat",            "GPS2_SAT",          logging.DEBUG),

    # ── Aiding sources ─────────────────────────────────────────────────────
    ("log_odo_vel",             "ODO_VEL",           logging.DEBUG),
    ("log_dvl_bottom_track",    "DVL_BOTTOM",        logging.DEBUG),
    ("log_dvl_water_track",     "DVL_WATER",         logging.DEBUG),
    ("log_air_data",            "AIR_DATA",          logging.DEBUG),
    ("log_usbl",                "USBL",              logging.DEBUG),
    ("log_depth",               "DEPTH",             logging.DEBUG),
    ("log_velocity_1",          "VELOCITY_1",        logging.DEBUG),
    ("log_position_1",          "POSITION_1",        logging.DEBUG),

    # ── Sync events ────────────────────────────────────────────────────────
    ("log_event_a",             "EVENT_A",           logging.DEBUG),
    ("log_event_b",             "EVENT_B",           logging.DEBUG),
    ("log_event_c",             "EVENT_C",           logging.DEBUG),
    ("log_event_d",             "EVENT_D",           logging.DEBUG),
    ("log_event_e",             "EVENT_E",           logging.DEBUG),
    ("log_event_out_a",         "EVENT_OUT_A",       logging.DEBUG),
    ("log_event_out_b",         "EVENT_OUT_B",       logging.DEBUG),

    # ── Misc / raw ─────────────────────────────────────────────────────────
    ("log_rtcm_raw",            "RTCM_RAW",          logging.DEBUG),
    ("log_session_info",        "SESSION_INFO",      logging.INFO),
    ("log_vib_mon_fft",         "VIB_MON_FFT",       logging.DEBUG),
    ("log_vib_mon_report",      "VIB_MON_REPORT",    logging.INFO),

    # LOG_DIAG is handled separately via _make_diag_cb()
]


# ── Argument parsing ──────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python utils/test_listeners.py",
        description=(
            "Register ALL sbg_ellipsd listeners and log every received message. "
            "Press Ctrl+C to stop and print final statistics."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "port",
        help="Serial port name (e.g. COM3, /dev/ttyUSB0)",
    )
    p.add_argument(
        "baudrate",
        nargs="?",
        type=int,
        default=921_600,
        help="Baud rate (default: 921600)",
    )
    p.add_argument(
        "--verbose", "-v",
        choices=list(_LEVEL_MAP),
        default="DEBUG",
        metavar="LEVEL",
        help="Log level: TRACE DEBUG INFO WARNING ERROR FATAL  (default: DEBUG)",
    )
    p.add_argument(
        "--stats", "-s",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="Statistics report interval in seconds (default: 5)",
    )
    return p.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    _setup_logging(args.verbose)

    _log.info(
        "─── sbg_ellipsd listener test ──────────────────────────────────"
    )
    _log.info("Port     : %s", args.port)
    _log.info("Baudrate : %d", args.baudrate)
    _log.info("Level    : %s (%d)", args.verbose, _LEVEL_MAP[args.verbose])
    _log.info("Stats    : every %.0f s", args.stats)
    _log.info(
        "Listeners: %d standard + 1 DIAG (total %d)",
        len(_LISTENERS), len(_LISTENERS) + 1,
    )
    _log.info(
        "────────────────────────────────────────────────────────────────"
    )

    ins = EllipsDInterface(args.port, args.baudrate)

    # Register all standard listeners
    for method_name, tag, level in _LISTENERS:
        getattr(ins, f"add_listener_{method_name}")(_make_cb(tag, level))

    # LOG_DIAG gets a special callback that maps SBG severity to Python levels
    ins.add_listener_log_diag(_make_diag_cb())

    # Stop event shared between the main thread and the statistics thread
    stop = threading.Event()

    def _on_signal(*_) -> None:
        _log.info("Stop requested — shutting down …")
        stop.set()

    signal.signal(signal.SIGINT, _on_signal)
    # SIGTERM is not available on Windows; ignore the AttributeError gracefully
    try:
        signal.signal(signal.SIGTERM, _on_signal)
    except (OSError, AttributeError):
        pass

    # Background thread: print statistics every args.stats seconds
    def _stats_loop() -> None:
        while not stop.wait(timeout=args.stats):
            _log_stats(f"Stats ({args.stats:.0f} s window)")

    stats_thread = threading.Thread(target=_stats_loop, daemon=True, name="stats")
    stats_thread.start()

    _log.info("Connecting …")
    try:
        ins.connect()
        _log.info("Connected.  Waiting for frames — press Ctrl+C to stop.")
        # Poll with a short timeout so Python's signal machinery can
        # deliver SIGINT between iterations.  A bare stop.wait() would
        # block inside C code on Windows and never wake up on Ctrl+C.
        while not stop.is_set():
            stop.wait(timeout=0.2)
    except OSError as exc:
        _log.error("Cannot open port: %s", exc)
    finally:
        ins.disconnect()
        _log.info(
            "────────────────────────────────────────────────────────────────"
        )
        _log_stats("Final statistics")
        _log.info(
            "Total messages across all types: %d",
            sum(_counts.values()),
        )
        _log.info("Done.")


if __name__ == "__main__":
    main()
