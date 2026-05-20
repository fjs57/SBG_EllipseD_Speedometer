from __future__ import annotations

from collections import deque
from enum import IntEnum, auto
from typing import Iterator

from .constants import SYNC1, SYNC2, ETX
from .crc import compute_crc


class _State(IntEnum):
    WAIT_SYNC1 = auto()
    WAIT_SYNC2 = auto()
    HEADER     = auto()
    PAYLOAD    = auto()
    CRC_LO     = auto()
    CRC_HI     = auto()
    END        = auto()


class FrameReader:
    """Stateful byte consumer that yields complete, CRC-validated SBG ECom frames.

    Feed raw bytes from the serial port with :meth:`feed`, then iterate the
    instance to consume any complete frames that became available::

        reader = FrameReader()
        reader.feed(chunk)
        for msg_id, msg_class, payload in reader:
            ...

    Each yielded tuple contains ``(msg_id: int, msg_class: int, payload: bytes)``.

    CRC-16 scope (verified against sbgEComProtocol.c in the SBG SDK):
        sbgCrc16Compute(&frame[MSG_ID_OFFSET],
                        PAYLOAD_OFFSET - MSG_ID_OFFSET + payloadSize)
    i.e. MSG_ID + CLASS + LEN_LO + LEN_HI + PAYLOAD  (all 4 header bytes included).
    """

    def __init__(self) -> None:
        self._state: _State = _State.WAIT_SYNC1
        self._crc_buf: bytearray = bytearray()   # [msg_id, class, len_lo, len_hi] + payload
        self._header: bytearray = bytearray()    # [msg_id, class, len_lo, len_hi]
        self._payload: bytearray = bytearray()
        self._expected_len: int = 0
        self._crc_lo: int = 0
        self._pending: deque[tuple[int, int, bytes]] = deque()

    def feed(self, data: bytes) -> None:
        for byte in data:
            self._consume(byte)

    def __iter__(self) -> Iterator[tuple[int, int, bytes]]:
        while self._pending:
            yield self._pending.popleft()

    def _reset(self) -> None:
        self._state = _State.WAIT_SYNC1

    def _consume(self, byte: int) -> None:  # noqa: C901 – linear state machine
        state = self._state

        if state is _State.WAIT_SYNC1:
            if byte == SYNC1:
                self._state = _State.WAIT_SYNC2

        elif state is _State.WAIT_SYNC2:
            if byte == SYNC2:
                self._header = bytearray()
                self._crc_buf = bytearray()
                self._state = _State.HEADER
            elif byte == SYNC1:
                # Another 0xFF immediately after the first: treat it as the new
                # SYNC1 and stay waiting for SYNC2.  Without this, a sequence
                # like 0xFF 0xFF 0x5A would miss the valid frame.
                pass   # state stays WAIT_SYNC2
            else:
                self._reset()

        elif state is _State.HEADER:
            self._header.append(byte)
            if len(self._header) == 4:
                # Seed CRC with all 4 header bytes: MSG_ID + CLASS + LEN_LO + LEN_HI
                self._crc_buf = bytearray(self._header)
                self._expected_len = self._header[2] | (self._header[3] << 8)
                self._payload = bytearray()
                self._state = _State.PAYLOAD if self._expected_len else _State.CRC_LO

        elif state is _State.PAYLOAD:
            self._payload.append(byte)
            self._crc_buf.append(byte)
            if len(self._payload) == self._expected_len:
                self._state = _State.CRC_LO

        elif state is _State.CRC_LO:
            self._crc_lo = byte
            self._state = _State.CRC_HI

        elif state is _State.CRC_HI:
            received_crc = self._crc_lo | (byte << 8)
            if compute_crc(bytes(self._crc_buf)) == received_crc:
                self._state = _State.END
            else:
                self._reset()

        elif state is _State.END:
            if byte == ETX:
                self._pending.append((
                    self._header[0],
                    self._header[1],
                    bytes(self._payload),
                ))
            self._reset()
