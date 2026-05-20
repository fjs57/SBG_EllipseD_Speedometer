from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogRtcmRaw:
    """RTCM/NTRIP correction data passthrough (MSG 0x31).

    Long streams are fragmented across multiple frames; the application is
    responsible for reassembly and parsing.
    """

    raw_data: bytes
