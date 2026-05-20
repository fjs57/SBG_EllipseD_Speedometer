from enum import IntFlag


class AidingStatus(IntFlag):
    GPS1_POS     = 0x00000001
    GPS1_VEL     = 0x00000002
    GPS1_HDT     = 0x00000004
    GPS1_UTC     = 0x00000008
    GPS2_POS     = 0x00000010
    GPS2_VEL     = 0x00000020
    GPS2_HDT     = 0x00000040
    GPS2_UTC     = 0x00000080
    MAG          = 0x00000100
    ODO          = 0x00000200
    DVL_BOTTOM   = 0x00000400
    DVL_WATER    = 0x00000800
    USBL         = 0x00001000
    AIR_DATA     = 0x00002000
    DEPTH        = 0x00004000
    VELOCITY_1   = 0x00008000
