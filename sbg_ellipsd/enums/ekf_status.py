from enum import IntFlag


class EkfSolutionFlags(IntFlag):
    """Flags extracted from the upper bits of the SOLUTION_STATUS field.

    The lowest 4 bits encode SolutionMode (see general_status.py).
    Use ``SolutionMode(status & 0x0F)`` to retrieve the mode.
    """
    ATTITUDE_VALID        = 0x00000010
    HEADING_VALID         = 0x00000020
    VELOCITY_VALID        = 0x00000040
    POSITION_VALID        = 0x00000080
    VERT_REF_USED         = 0x00000100
    MAG_REF_USED          = 0x00000200
    GPS1_VEL_USED         = 0x00000400
    GPS1_POS_USED         = 0x00000800
    VEL_CONSTRAINTS_USED  = 0x00001000
    GPS1_HDT_USED         = 0x00002000
    GPS2_VEL_USED         = 0x00004000
    GPS2_POS_USED         = 0x00008000
    GPS2_HDT_USED         = 0x00020000
    ODO_USED              = 0x00040000
    DVL_BT_USED           = 0x00080000
    DVL_WT_USED           = 0x00100000
    VEL1_USED             = 0x00200000
    USBL_USED             = 0x01000000
    AIRSPEED_USED         = 0x02000000
    ZUPT_USED             = 0x04000000
    ALIGN_VALID           = 0x08000000
    VERTICAL_AIDING_USED  = 0x10000000
    ZARU_USED             = 0x20000000
    POS1_USED             = 0x40000000
