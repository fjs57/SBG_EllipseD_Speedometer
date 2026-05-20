#!/usr/bin/env python3
"""SBG ECom raw serial diagnostic — completely standalone (pyserial only).

This tool BYPASSES the sbg_ellipsd library entirely.  It opens the serial port
directly, reads raw bytes, searches for 0xFF 0x5A sync patterns and validates
each candidate frame against the CRC.  Use it to determine at which layer
reception is failing:

  1. If ``bytes/s = 0``        → serial port not open / wrong port name
  2. If ``bytes/s > 0``        → bytes ARE arriving
     a. If ``sync = 0``        → wrong baud rate, or wrong device protocol
     b. If ``sync > 0``
        - ``CRC_OK > 0``       → frames are valid; issue is in sbg_ellipsd
        - ``CRC_FAIL > 0``     → CRC mismatch (see which scope works better)
        - ``TRUNC > 0``        → frames arrive fragmented (normal at high rate)

Usage::

    python utils/raw_dump.py COM3
    python utils/raw_dump.py COM3 921600
    python utils/raw_dump.py COM3 921600 --hex        # also print hex dump
    python utils/raw_dump.py COM3 921600 --interval 2 # stats every 2 s
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
import time
from collections import defaultdict
from pathlib import Path

try:
    import serial
except ImportError:
    sys.exit("pyserial is not installed.  Run:  pip install pyserial")

# ── Protocol constants ────────────────────────────────────────────────────────
SYNC1 = 0xFF
SYNC2 = 0x5A
ETX   = 0x33

# Known SBG ECom message-ID names (for human-readable output)
_MSG_NAMES: dict[int, str] = {
    0x01: "STATUS",        0x02: "UTC_TIME",      0x03: "IMU_DATA",
    0x04: "MAG",           0x05: "MAG_CALIB",     0x06: "EKF_EULER",
    0x07: "EKF_QUAT",      0x08: "EKF_NAV",       0x09: "SHIP_MOTION",
    0x0D: "GPS1_VEL",      0x0E: "GPS1_POS",      0x0F: "GPS1_HDT",
    0x10: "GPS2_VEL",      0x11: "GPS2_POS",      0x12: "GPS2_HDT",
    0x13: "ODO_VEL",       0x18: "EVENT_A",       0x19: "EVENT_B",
    0x1A: "EVENT_C",       0x1B: "EVENT_D",       0x1C: "EVENT_E",
    0x1D: "DVL_BOTTOM",    0x1E: "DVL_WATER",     0x1F: "GPS1_RAW",
    0x20: "SHIP_MOTION_HP",0x24: "AIR_DATA",      0x25: "USBL",
    0x26: "GPS2_RAW",      0x2C: "IMU_SHORT",     0x2D: "EVENT_OUT_A",
    0x2E: "EVENT_OUT_B",   0x2F: "DEPTH",         0x30: "DIAG",
    0x31: "RTCM_RAW",      0x32: "GPS1_SAT",      0x33: "GPS2_SAT",
    0x34: "EKF_ROT_BODY",  0x35: "EKF_ROT_NED",   0x36: "EKF_VEL_BODY",
    0x37: "SESSION_INFO",  0x39: "PTP_STATUS",    0x3A: "VELOCITY_1",
    0x3B: "VIB_FFT",       0x3C: "VIB_REPORT",    0x3D: "EKF_AIR_DATA",
    0x3E: "POSITION_1",
}


# ── Standalone CRC-16 (polynomial 0x8408) ─────────────────────────────────────
# Reimplement here so this script has ZERO dependency on sbg_ellipsd.

def _build_crc_table() -> tuple[int, ...]:
    t = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if (crc & 1) else (crc >> 1)
        t.append(crc)
    return tuple(t)


_CRC_TABLE = _build_crc_table()


def _crc16(data: bytes) -> int:
    """CRC-16 with polynomial 0x8408 over *data*."""
    crc = 0
    for b in data:
        crc = _CRC_TABLE[(crc ^ b) & 0xFF] ^ (crc >> 8)
    return crc & 0xFFFF


# ── Statistics ────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_total_bytes:   int = 0
_sync_found:    int = 0
_crc_ok:        int = 0
_crc_fail:      int = 0
_etx_fail:      int = 0
_trunc:         int = 0
_msg_counts: dict[int, int] = defaultdict(int)


# ── Frame scanner ─────────────────────────────────────────────────────────────

def _scan(buf: bytes, show_hex: bool) -> bytes:
    """Search *buf* for SBG ECom frames.  Returns the unconsumed tail."""
    global _sync_found, _crc_ok, _crc_fail, _etx_fail, _trunc

    i = 0
    while i < len(buf) - 1:
        # Fast scan for SYNC1
        if buf[i] != SYNC1:
            i += 1
            continue
        if buf[i + 1] != SYNC2:
            i += 1
            continue

        # Sync found — need at least 6 bytes for the full header
        _sync_found += 1
        if i + 6 > len(buf):
            break   # keep the partial frame in the buffer

        msg_id    = buf[i + 2]
        msg_class = buf[i + 3]
        length    = buf[i + 4] | (buf[i + 5] << 8)

        # Total frame size: 2 (sync) + 4 (header) + length (payload) + 2 (crc) + 1 (etx)
        frame_end = i + 9 + length

        if frame_end > len(buf):
            # Frame not complete yet — stop here and carry the tail forward
            _trunc += 1
            break

        # CRC over: MSG_ID + CLASS + LEN_LO + LEN_HI + PAYLOAD
        crc_data     = buf[i + 2: i + 6 + length]
        crc_computed = _crc16(crc_data)
        crc_received = buf[i + 6 + length] | (buf[i + 7 + length] << 8)
        etx_byte     = buf[i + 8 + length]

        crc_ok  = (crc_computed == crc_received)
        etx_ok  = (etx_byte == ETX)

        if crc_ok and etx_ok:
            _crc_ok += 1
            _msg_counts[msg_id] += 1
            name = _MSG_NAMES.get(msg_id, f"0x{msg_id:02X}")
            print(
                f"  FRAME OK   cls=0x{msg_class:02X}  "
                f"id=0x{msg_id:02X}({name})  "
                f"len={length:4d}  "
                f"crc=0x{crc_received:04X}"
            )
        elif not crc_ok:
            _crc_fail += 1
            print(
                f"  CRC FAIL   cls=0x{msg_class:02X}  "
                f"id=0x{msg_id:02X}  "
                f"len={length:4d}  "
                f"recv=0x{crc_received:04X}  calc=0x{crc_computed:04X}"
            )
        else:
            _etx_fail += 1
            print(
                f"  ETX FAIL   cls=0x{msg_class:02X}  "
                f"id=0x{msg_id:02X}  "
                f"len={length:4d}  "
                f"etx=0x{etx_byte:02X}"
            )

        if show_hex:
            _hexdump(buf[i:frame_end], i)

        i = frame_end   # advance past the consumed frame

    return buf[i:]   # unconsumed tail


def _hexdump(data: bytes, offset: int = 0) -> None:
    """Print data as a hex dump (16 bytes per line)."""
    for row in range(0, len(data), 16):
        chunk = data[row: row + 16]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        asc_part = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        print(f"    {offset + row:06X}  {hex_part:<47}  |{asc_part}|")


# ── Statistics reporter ───────────────────────────────────────────────────────

def _print_stats(elapsed: float) -> None:
    rate = _total_bytes / elapsed if elapsed > 0 else 0.0
    print()
    print(
        f"─── {elapsed:.1f} s ─────────────────────────────────────────────"
    )
    print(f"  bytes received : {_total_bytes:>10,}  ({rate:>8.0f} bytes/s)")
    print(f"  sync found     : {_sync_found:>10,}")
    print(f"  CRC OK         : {_crc_ok:>10,}")
    print(f"  CRC FAIL       : {_crc_fail:>10,}")
    print(f"  ETX FAIL       : {_etx_fail:>10,}")
    print(f"  truncated      : {_trunc:>10,}")

    if _msg_counts:
        print("  message counts :")
        for msg_id in sorted(_msg_counts):
            name = _MSG_NAMES.get(msg_id, f"0x{msg_id:02X}")
            print(f"    0x{msg_id:02X} {name:<20s} {_msg_counts[msg_id]:>6,}")

    if _total_bytes == 0:
        print()
        print("  !! No bytes received — check port name and that the device")
        print("     is powered on and connected.")
    elif _sync_found == 0:
        print()
        print("  !! Bytes received but no sync pattern (0xFF 0x5A) found.")
        print("     Likely causes: wrong baud rate, or device is not in binary mode.")
    elif _crc_ok == 0 and _crc_fail > 0:
        print()
        print("  !! Sync patterns found but all CRCs fail.")
        print("     CRC scope used: MSG_ID + CLASS + LEN_LO + LEN_HI + PAYLOAD.")

    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python utils/raw_dump.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("port", help="Serial port (e.g. COM3, /dev/ttyUSB0)")
    p.add_argument("baudrate", nargs="?", type=int, default=921_600,
                   help="Baud rate (default: 921600)")
    p.add_argument("--hex", action="store_true",
                   help="Print hex dump of each frame")
    p.add_argument("--interval", "-i", type=float, default=5.0, metavar="S",
                   help="Statistics report interval in seconds (default: 5)")
    p.add_argument("--quiet", "-q", action="store_true",
                   help="Only print statistics, suppress per-frame lines")
    return p.parse_args()


def main() -> None:
    global _total_bytes
    args = _parse_args()

    print(f"Opening {args.port} at {args.baudrate} baud …")
    try:
        ser = serial.Serial(
            port=args.port,
            baudrate=args.baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.2,
            rtscts=False,
            xonxoff=False,
        )
    except serial.SerialException as exc:
        sys.exit(f"Cannot open {args.port}: {exc}")

    print(f"Port open.  Listening for SBG ECom frames — Ctrl+C to stop.")
    print()

    stop = threading.Event()

    def _on_signal(*_) -> None:
        stop.set()

    signal.signal(signal.SIGINT, _on_signal)
    try:
        signal.signal(signal.SIGTERM, _on_signal)
    except (OSError, AttributeError):
        pass

    buf = b""
    t_start = time.monotonic()
    t_last_stat = t_start

    try:
        while not stop.is_set():
            chunk = ser.read(4096)
            if chunk:
                _total_bytes += len(chunk)
                buf += chunk
                if not args.quiet:
                    buf = _scan(buf, args.hex)
                else:
                    # Still scan to update stats, just don't print per-frame
                    import io, contextlib
                    with contextlib.redirect_stdout(io.StringIO()):
                        buf = _scan(buf, False)

            now = time.monotonic()
            if now - t_last_stat >= args.interval:
                _print_stats(now - t_start)
                t_last_stat = now

    finally:
        ser.close()
        elapsed = time.monotonic() - t_start
        print(f"\nFinal report after {elapsed:.1f} s:")
        _print_stats(elapsed)


if __name__ == "__main__":
    main()
