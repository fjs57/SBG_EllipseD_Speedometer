from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogPtpStatus:
    """PTP (Precision Time Protocol) clock status (MSG 0x39, v5.3+)."""

    timestamp_us: int
    status: int
    time_scale_offset_s: float
    local_clock_identity: int
    local_clock_priority1: int
    local_clock_priority2: int
    local_clock_class: int
    local_clock_accuracy: int
    local_clock_log2_variance: int
    local_clock_time_source: int
    master_clock_identity: int
    master_clock_priority1: int
    master_clock_priority2: int
    master_clock_class: int
    master_clock_accuracy: int
    master_clock_log2_variance: int
    master_clock_time_source: int
    mean_path_delay_s: float
    mean_path_delay_std_s: float
    clock_offset_s: float
    clock_offset_std_s: float
    clock_freq_offset_hz: float
    clock_freq_offset_std_hz: float
    master_mac_address: bytes
    """6-byte MAC address of the PTP master."""
    domain_number: int
