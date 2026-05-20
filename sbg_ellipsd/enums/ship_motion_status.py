from enum import IntFlag


class ShipMotionStatus(IntFlag):
    HEAVE_VALID        = 0x0001
    SURGE_SWAY_VALID   = 0x0002
    ACCEL_VALID        = 0x0004
    VEL_VALID          = 0x0008
    PERIOD_AVAILABLE   = 0x0010
    # Bit 8: delayed heave (HP models only)
    DELAYED_HEAVE      = 0x0100
