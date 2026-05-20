from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogEventA:
    """Sync-In A edge detection timestamps (MSG 0x18)."""

    timestamp_us: int
    """Timestamp of the most recent detected edge."""
    status: int
    """Interpret with :class:`~sbg_ellipsd.enums.EventStatus`."""
    time_of_first_change_us: int
    time_offset_0_us: int
    time_offset_1_us: int
    time_offset_2_us: int
    time_offset_3_us: int


@dataclass(frozen=True, slots=True)
class LogEventB:
    """Sync-In B edge detection timestamps (MSG 0x19)."""

    timestamp_us: int
    status: int
    time_of_first_change_us: int
    time_offset_0_us: int
    time_offset_1_us: int
    time_offset_2_us: int
    time_offset_3_us: int


@dataclass(frozen=True, slots=True)
class LogEventC:
    """Sync-In C edge detection timestamps (MSG 0x1A)."""

    timestamp_us: int
    status: int
    time_of_first_change_us: int
    time_offset_0_us: int
    time_offset_1_us: int
    time_offset_2_us: int
    time_offset_3_us: int


@dataclass(frozen=True, slots=True)
class LogEventD:
    """Sync-In D edge detection timestamps (MSG 0x1B)."""

    timestamp_us: int
    status: int
    time_of_first_change_us: int
    time_offset_0_us: int
    time_offset_1_us: int
    time_offset_2_us: int
    time_offset_3_us: int


@dataclass(frozen=True, slots=True)
class LogEventE:
    """Sync-In E edge detection timestamps (MSG 0x1C)."""

    timestamp_us: int
    status: int
    time_of_first_change_us: int
    time_offset_0_us: int
    time_offset_1_us: int
    time_offset_2_us: int
    time_offset_3_us: int


@dataclass(frozen=True, slots=True)
class LogEventOutA:
    """Sync-Out A event timestamps (MSG 0x2D)."""

    timestamp_us: int
    status: int
    time_of_first_change_us: int
    time_offset_0_us: int
    time_offset_1_us: int
    time_offset_2_us: int
    time_offset_3_us: int


@dataclass(frozen=True, slots=True)
class LogEventOutB:
    """Sync-Out B event timestamps (MSG 0x2E)."""

    timestamp_us: int
    status: int
    time_of_first_change_us: int
    time_offset_0_us: int
    time_offset_1_us: int
    time_offset_2_us: int
    time_offset_3_us: int
