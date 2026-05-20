def _build_table() -> tuple[int, ...]:
    table = []
    for i in range(256):
        crc = i
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8408 if crc & 1 else crc >> 1
        table.append(crc)
    return tuple(table)


_TABLE: tuple[int, ...] = _build_table()


def compute_crc(data: bytes) -> int:
    """CRC-16 using polynomial 0x8408 (bit-reversed CRC-CCITT).

    Scope per SBG ECom spec: from MSG_ID byte through end of payload,
    including the CLASS and LENGTH bytes.
    """
    crc = 0
    for byte in data:
        crc = _TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return crc & 0xFFFF
