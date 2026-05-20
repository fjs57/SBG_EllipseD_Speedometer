from enum import IntFlag


class EventStatus(IntFlag):
    TIME_SYNC_OK      = 0x0001
    # Bits [1-3]: number of offsets available (0-4 additional pulses)
    OVERFLOW          = 0x0010
