from __future__ import annotations

import logging
import struct
from typing import Any, Callable, ClassVar

from .constants import (
    MSG_STATUS, MSG_UTC_TIME, MSG_IMU_DATA, MSG_MAG, MSG_MAG_CALIB,
    MSG_EKF_EULER, MSG_EKF_QUAT, MSG_EKF_NAV, MSG_SHIP_MOTION,
    MSG_GPS1_VEL, MSG_GPS1_POS, MSG_GPS1_HDT,
    MSG_GPS2_VEL, MSG_GPS2_POS, MSG_GPS2_HDT,
    MSG_ODO_VEL, MSG_EVENT_A, MSG_EVENT_B, MSG_EVENT_C, MSG_EVENT_D, MSG_EVENT_E,
    MSG_DVL_BOTTOM_TRACK, MSG_DVL_WATER_TRACK,
    MSG_GPS1_RAW, MSG_SHIP_MOTION_HP, MSG_AIR_DATA, MSG_USBL, MSG_GPS2_RAW,
    MSG_IMU_SHORT, MSG_EVENT_OUT_A, MSG_EVENT_OUT_B, MSG_DEPTH,
    MSG_DIAG, MSG_RTCM_RAW, MSG_GPS1_SAT, MSG_GPS2_SAT,
    MSG_EKF_ROT_ACCEL_BODY, MSG_EKF_ROT_ACCEL_NED, MSG_EKF_VEL_BODY,
    MSG_SESSION_INFO, MSG_PTP_STATUS, MSG_VELOCITY_1,
    MSG_VIB_MON_FFT, MSG_VIB_MON_REPORT, MSG_EKF_AIR_DATA, MSG_POSITION_1,
)
from ..messages.status import LogStatus
from ..messages.utc_time import LogUtcTime
from ..messages.imu import LogImuShort, LogImuData
from ..messages.magnetometer import LogMag, LogMagCalib
from ..messages.ekf import (
    LogEkfEuler, LogEkfQuat, LogEkfNav, LogEkfVelBody,
    LogEkfRotAccelBody, LogEkfRotAccelNed, LogEkfAirData,
)
from ..messages.ship_motion import LogShipMotion, LogShipMotionHp
from ..messages.gps import LogGps1Vel, LogGps1Pos, LogGps1Hdt, LogGps2Vel, LogGps2Pos, LogGps2Hdt
from ..messages.gps_raw import LogGps1Raw, LogGps2Raw, LogGps1Sat, LogGps2Sat, SatInfo, SignalInfo
from ..messages.events import (
    LogEventA, LogEventB, LogEventC, LogEventD, LogEventE,
    LogEventOutA, LogEventOutB,
)
from ..messages.dvl import LogDvlBottomTrack, LogDvlWaterTrack
from ..messages.air_data import LogAirData
from ..messages.usbl import LogUsbl
from ..messages.odometer import LogOdoVel
from ..messages.depth import LogDepth
from ..messages.position import LogPosition1
from ..messages.velocity import LogVelocity1
from ..messages.ptp import LogPtpStatus
from ..messages.diagnostics import LogDiag
from ..messages.session_info import LogSessionInfo
from ..messages.rtcm import LogRtcmRaw
from ..messages.vibration import LogVibMonFft, LogVibMonReport

_log = logging.getLogger(__name__)

# ─── Pre-compiled struct objects ────────────────────────────────────────────

_S_STATUS       = struct.Struct('<IHHIIIHIB')          # 27 B
_S_UTC_TIME     = struct.Struct('<IHHBBBBBIIfff')      # 33 B
_S_IMU_SHORT    = struct.Struct('<IHiiiiiih')           # 32 B
_S_IMU_DATA     = struct.Struct('<IHfffffffffffff')     # 58 B — 13 floats
_S_MAG          = struct.Struct('<IHffffff')            # 30 B
_S_MAG_CALIB    = struct.Struct('<IH16s')               # 22 B
_S_EKF_EULER    = struct.Struct('<IffffffIff')          # 40 B
_S_EKF_QUAT     = struct.Struct('<IfffffffIff')         # 44 B
_S_EKF_NAV      = struct.Struct('<IffffffdddffffI')     # 72 B
_S_SHIP_MOTION  = struct.Struct('<IffffffffffH')        # 46 B
_S_GPS_VEL      = struct.Struct('<IIIffffffff')         # 44 B
_S_GPS_POS      = struct.Struct('<IIIdddffffBHHBIBI')   # 67 B
_S_GPS_HDT      = struct.Struct('<IHIfffffBB')          # 32 B
_S_ODO_VEL      = struct.Struct('<IHf')                 # 10 B
_S_DVL          = struct.Struct('<IHffffff')            # 30 B
_S_AIR_DATA     = struct.Struct('<IHfffff')             # 26 B
_S_USBL         = struct.Struct('<IHddffffI')           # 42 B
_S_DEPTH        = struct.Struct('<IHff')                # 14 B
_S_EKF_6DOF     = struct.Struct('<IIffffff')            # 32 B
_S_EKF_AIR     = struct.Struct('<IHffffff')             # 30 B
_S_VELOCITY_1   = struct.Struct('<IHffffff')            # 30 B
_S_POSITION_1   = struct.Struct('<IHdddffffff')         # 54 B
_S_SESSION      = struct.Struct('<HHH')                 # 6 B header
_S_DIAG         = struct.Struct('<IBB')                 # 6 B header
_S_EVENT        = struct.Struct('<IHIIIII')             # 26 B
_S_SAT_HEADER   = struct.Struct('<IIB')                 # 9 B
_S_SAT_ENTRY    = struct.Struct('<BbHHB')               # 7 B per satellite
_S_SIGNAL_ENTRY = struct.Struct('<BBB')                 # 3 B per signal
# PTP: 83 B; 4x = 4 padding bytes after master_clock_time_source
_S_PTP          = struct.Struct('<IHdQBBBBHBQBBBBHB4xffdfff6sB')

_ACCEL_SCALE = 1.0 / 1_048_576.0    # IMU short counts → m/s²
_RATE_SCALE  = 1.0 / 67_108_864.0   # IMU short counts → rad/s
_TEMP_SCALE  = 1.0 / 256.0          # IMU short counts → °C


# ─── Parse helpers ──────────────────────────────────────────────────────────

def _parse_status(p: bytes) -> LogStatus | None:
    if len(p) < _S_STATUS.size:
        return None
    ts, gen, com2, com, aid, _r2, _r3, uptime, cpu = _S_STATUS.unpack_from(p)
    return LogStatus(
        timestamp_us=ts, general_status=gen, com_status_2=com2,
        com_status=com, aiding_status=aid, uptime_s=uptime, cpu_usage_pct=cpu,
    )


def _parse_utc_time(p: bytes) -> LogUtcTime | None:
    if len(p) < _S_UTC_TIME.size:
        return None
    ts, st, year, month, day, hour, minute, sec, ns, tow, bias, sf, resid = \
        _S_UTC_TIME.unpack_from(p)
    return LogUtcTime(
        timestamp_us=ts, time_status=st,
        year=year, month=month, day=day, hour=hour, minute=minute, second=sec,
        nanosecond=ns, gps_time_of_week_ms=tow,
        clock_bias_std_s=bias, clock_scale_factor_error_std_pct=sf,
        clock_residual_error_s=resid,
    )


def _parse_imu_short(p: bytes) -> LogImuShort | None:
    if len(p) < _S_IMU_SHORT.size:
        return None
    ts, st, ax, ay, az, rx, ry, rz, temp = _S_IMU_SHORT.unpack_from(p)
    return LogImuShort(
        timestamp_us=ts, status=st,
        accel_x_ms2=ax * _ACCEL_SCALE,
        accel_y_ms2=ay * _ACCEL_SCALE,
        accel_z_ms2=az * _ACCEL_SCALE,
        rate_x_rads=rx * _RATE_SCALE,
        rate_y_rads=ry * _RATE_SCALE,
        rate_z_rads=rz * _RATE_SCALE,
        temperature_c=temp * _TEMP_SCALE,
    )


def _parse_imu_data(p: bytes) -> LogImuData | None:
    if len(p) < _S_IMU_DATA.size:
        return None
    # Last 6 fields are duplicated backward-compat values; discarded.
    ts, st, ax, ay, az, rx, ry, rz, temp, *_ = _S_IMU_DATA.unpack_from(p)
    return LogImuData(
        timestamp_us=ts, status=st,
        accel_x_ms2=ax, accel_y_ms2=ay, accel_z_ms2=az,
        rate_x_rads=rx, rate_y_rads=ry, rate_z_rads=rz,
        temperature_c=temp,
    )


def _parse_mag(p: bytes) -> LogMag | None:
    if len(p) < _S_MAG.size:
        return None
    ts, st, mx, my, mz, ax, ay, az = _S_MAG.unpack_from(p)
    return LogMag(
        timestamp_us=ts, status=st,
        mag_x=mx, mag_y=my, mag_z=mz,
        accel_x_ms2=ax, accel_y_ms2=ay, accel_z_ms2=az,
    )


def _parse_mag_calib(p: bytes) -> LogMagCalib | None:
    if len(p) < _S_MAG_CALIB.size:
        return None
    ts, _r, buf = _S_MAG_CALIB.unpack_from(p)
    return LogMagCalib(timestamp_us=ts, buffer=buf)


def _parse_ekf_euler(p: bytes) -> LogEkfEuler | None:
    if len(p) < _S_EKF_EULER.size:
        return None
    ts, roll, pitch, yaw, rstd, pstd, ystd, sol, decl, incl = _S_EKF_EULER.unpack_from(p)
    return LogEkfEuler(
        timestamp_us=ts, roll_rad=roll, pitch_rad=pitch, yaw_rad=yaw,
        roll_std_rad=rstd, pitch_std_rad=pstd, yaw_std_rad=ystd,
        solution_status=sol,
        magnetic_declination_rad=decl, magnetic_inclination_rad=incl,
    )


def _parse_ekf_quat(p: bytes) -> LogEkfQuat | None:
    if len(p) < _S_EKF_QUAT.size:
        return None
    ts, q0, q1, q2, q3, rstd, pstd, ystd, sol, decl, incl = _S_EKF_QUAT.unpack_from(p)
    return LogEkfQuat(
        timestamp_us=ts, q0=q0, q1=q1, q2=q2, q3=q3,
        roll_std_rad=rstd, pitch_std_rad=pstd, yaw_std_rad=ystd,
        solution_status=sol,
        magnetic_declination_rad=decl, magnetic_inclination_rad=incl,
    )


def _parse_ekf_nav(p: bytes) -> LogEkfNav | None:
    if len(p) < _S_EKF_NAV.size:
        return None
    (ts, vn, ve, vd, vnstd, vestd, vdstd,
     lat, lon, alt, und, latstd, lonstd, altstd, sol) = _S_EKF_NAV.unpack_from(p)
    return LogEkfNav(
        timestamp_us=ts,
        velocity_n_ms=vn, velocity_e_ms=ve, velocity_d_ms=vd,
        velocity_n_std_ms=vnstd, velocity_e_std_ms=vestd, velocity_d_std_ms=vdstd,
        latitude_deg=lat, longitude_deg=lon, altitude_m=alt,
        undulation_m=und,
        latitude_std_m=latstd, longitude_std_m=lonstd, altitude_std_m=altstd,
        solution_status=sol,
    )


def _parse_ship_motion(p: bytes) -> LogShipMotion | None:
    if len(p) < _S_SHIP_MOTION.size:
        return None
    ts, period, surge, sway, heave, ax, ay, az, vx, vy, vz, st = _S_SHIP_MOTION.unpack_from(p)
    return LogShipMotion(
        timestamp_us=ts, heave_period_s=period,
        surge_m=surge, sway_m=sway, heave_m=heave,
        accel_x_ms2=ax, accel_y_ms2=ay, accel_z_ms2=az,
        vel_x_ms=vx, vel_y_ms=vy, vel_z_ms=vz,
        status=st,
    )


def _parse_ship_motion_hp(p: bytes) -> LogShipMotionHp | None:
    if len(p) < _S_SHIP_MOTION.size:
        return None
    ts, period, surge, sway, heave, ax, ay, az, vx, vy, vz, st = _S_SHIP_MOTION.unpack_from(p)
    return LogShipMotionHp(
        timestamp_us=ts, heave_period_s=period,
        surge_m=surge, sway_m=sway, heave_m=heave,
        accel_x_ms2=ax, accel_y_ms2=ay, accel_z_ms2=az,
        vel_x_ms=vx, vel_y_ms=vy, vel_z_ms=vz,
        status=st,
    )


def _parse_gps_vel(cls: type, p: bytes) -> Any | None:
    if len(p) < _S_GPS_VEL.size:
        return None
    ts, st, tow, vn, ve, vd, vnstd, vestd, vdstd, course, cstd = _S_GPS_VEL.unpack_from(p)
    return cls(
        timestamp_us=ts, status_type=st, time_of_week_ms=tow,
        velocity_n_ms=vn, velocity_e_ms=ve, velocity_d_ms=vd,
        velocity_n_std_ms=vnstd, velocity_e_std_ms=vestd, velocity_d_std_ms=vdstd,
        course_deg=course, course_std_deg=cstd,
    )


def _parse_gps_pos(cls: type, p: bytes) -> Any | None:
    if len(p) < _S_GPS_POS.size:
        return None
    (ts, st, tow, lat, lon, alt, und, latstd, lonstd, altstd,
     nsvused, baseid, diffage_raw, nsvtracked, stext, nreboots, uptime) = \
        _S_GPS_POS.unpack_from(p)
    return cls(
        timestamp_us=ts, status_type=st, time_of_week_ms=tow,
        latitude_deg=lat, longitude_deg=lon, altitude_m=alt, undulation_m=und,
        latitude_std_m=latstd, longitude_std_m=lonstd, altitude_std_m=altstd,
        num_sv_used=nsvused, base_station_id=baseid,
        differential_age_s=diffage_raw * 0.01,
        num_sv_tracked=nsvtracked, status_ext=stext,
        nr_diagnostic_reboots=nreboots, receiver_uptime_s=uptime,
    )


def _parse_gps_hdt(cls: type, p: bytes) -> Any | None:
    if len(p) < _S_GPS_HDT.size:
        return None
    ts, st, tow, hdg, hdgstd, pitch, pstd, base, nsvt, nsvu = _S_GPS_HDT.unpack_from(p)
    return cls(
        timestamp_us=ts, status=st, time_of_week_ms=tow,
        true_heading_deg=hdg, true_heading_std_deg=hdgstd,
        pitch_deg=pitch, pitch_std_deg=pstd, baseline_m=base,
        num_sv_tracked=nsvt, num_sv_used=nsvu,
    )


def _parse_odo_vel(p: bytes) -> LogOdoVel | None:
    if len(p) < _S_ODO_VEL.size:
        return None
    ts, st, vel = _S_ODO_VEL.unpack_from(p)
    return LogOdoVel(timestamp_us=ts, status=st, velocity_ms=vel)


def _parse_event(cls: type, p: bytes) -> Any | None:
    if len(p) < _S_EVENT.size:
        return None
    ts, st, t0, o0, o1, o2, o3 = _S_EVENT.unpack_from(p)
    return cls(
        timestamp_us=ts, status=st, time_of_first_change_us=t0,
        time_offset_0_us=o0, time_offset_1_us=o1,
        time_offset_2_us=o2, time_offset_3_us=o3,
    )


def _parse_dvl(cls: type, p: bytes) -> Any | None:
    if len(p) < _S_DVL.size:
        return None
    ts, st, vx, vy, vz, sx, sy, sz = _S_DVL.unpack_from(p)
    return cls(
        timestamp_us=ts, status=st,
        velocity_x_ms=vx, velocity_y_ms=vy, velocity_z_ms=vz,
        velocity_x_std_ms=sx, velocity_y_std_ms=sy, velocity_z_std_ms=sz,
    )


def _parse_air_data(p: bytes) -> LogAirData | None:
    if len(p) < _S_AIR_DATA.size:
        return None
    ts, st, pabs, alt, pdiff, tas, temp = _S_AIR_DATA.unpack_from(p)
    return LogAirData(
        timestamp_us=ts, status=st,
        pressure_abs_pa=pabs, altitude_m=alt,
        pressure_diff_pa=pdiff, true_airspeed_ms=tas, air_temperature_c=temp,
    )


def _parse_usbl(p: bytes) -> LogUsbl | None:
    if len(p) < _S_USBL.size:
        return None
    ts, st, lat, lon, depth, latstd, lonstd, dstd, age = _S_USBL.unpack_from(p)
    return LogUsbl(
        timestamp_us=ts, status=st,
        latitude_deg=lat, longitude_deg=lon, depth_m=depth,
        latitude_std_m=latstd, longitude_std_m=lonstd, depth_std_m=dstd,
        information_age_us=age,
    )


def _parse_depth(p: bytes) -> LogDepth | None:
    if len(p) < _S_DEPTH.size:
        return None
    ts, st, pres, dep = _S_DEPTH.unpack_from(p)
    return LogDepth(timestamp_us=ts, status=st, pressure_pa=pres, depth_m=dep)


def _parse_ekf_rot_accel_body(p: bytes) -> LogEkfRotAccelBody | None:
    if len(p) < _S_EKF_6DOF.size:
        return None
    ts, sol, rx, ry, rz, ax, ay, az = _S_EKF_6DOF.unpack_from(p)
    return LogEkfRotAccelBody(
        timestamp_us=ts, solution_status=sol,
        rate_x_rads=rx, rate_y_rads=ry, rate_z_rads=rz,
        accel_x_ms2=ax, accel_y_ms2=ay, accel_z_ms2=az,
    )


def _parse_ekf_rot_accel_ned(p: bytes) -> LogEkfRotAccelNed | None:
    if len(p) < _S_EKF_6DOF.size:
        return None
    ts, sol, rn, re, rd, an, ae, ad = _S_EKF_6DOF.unpack_from(p)
    return LogEkfRotAccelNed(
        timestamp_us=ts, solution_status=sol,
        rate_n_rads=rn, rate_e_rads=re, rate_d_rads=rd,
        accel_n_ms2=an, accel_e_ms2=ae, accel_d_ms2=ad,
    )


def _parse_ekf_vel_body(p: bytes) -> LogEkfVelBody | None:
    if len(p) < _S_EKF_6DOF.size:
        return None
    ts, sol, vx, vy, vz, sx, sy, sz = _S_EKF_6DOF.unpack_from(p)
    return LogEkfVelBody(
        timestamp_us=ts, solution_status=sol,
        velocity_x_ms=vx, velocity_y_ms=vy, velocity_z_ms=vz,
        velocity_x_std_ms=sx, velocity_y_std_ms=sy, velocity_z_std_ms=sz,
    )


def _parse_ekf_air_data(p: bytes) -> LogEkfAirData | None:
    if len(p) < _S_EKF_AIR.size:
        return None
    ts, st, wn, we, wd, wnstd, westd, wdstd = _S_EKF_AIR.unpack_from(p)
    return LogEkfAirData(
        timestamp_us=ts, status=st,
        wind_n_ms=wn, wind_e_ms=we, wind_d_ms=wd,
        wind_n_std_ms=wnstd, wind_e_std_ms=westd, wind_d_std_ms=wdstd,
    )


def _parse_velocity_1(p: bytes) -> LogVelocity1 | None:
    if len(p) < _S_VELOCITY_1.size:
        return None
    ts, st, v0, v1, v2, s0, s1, s2 = _S_VELOCITY_1.unpack_from(p)
    return LogVelocity1(
        timestamp_us=ts, status=st,
        velocity_0_ms=v0, velocity_1_ms=v1, velocity_2_ms=v2,
        velocity_0_std_ms=s0, velocity_1_std_ms=s1, velocity_2_std_ms=s2,
    )


def _parse_position_1(p: bytes) -> LogPosition1 | None:
    if len(p) < _S_POSITION_1.size:
        return None
    ts, st, lat, lon, h, cll, coo, chh, clo, clh, coh = _S_POSITION_1.unpack_from(p)
    return LogPosition1(
        timestamp_us=ts, status=st,
        latitude_deg=lat, longitude_deg=lon, height_m=h,
        cov_lat_lat_m2=cll, cov_lon_lon_m2=coo, cov_height_height_m2=chh,
        cov_lat_lon_m2=clo, cov_lat_height_m2=clh, cov_lon_height_m2=coh,
    )


def _parse_ptp_status(p: bytes) -> LogPtpStatus | None:
    if len(p) < _S_PTP.size:
        return None
    (ts, st, tso,
     lci, lp1, lp2, lcl, lac, lvar, lts,
     mci, mp1, mp2, mcl, mac, mvar, mts,
     mpd, mpdstd, co, costd, cfo, cfostd, mmac, domain) = _S_PTP.unpack_from(p)
    return LogPtpStatus(
        timestamp_us=ts, status=st, time_scale_offset_s=tso,
        local_clock_identity=lci,
        local_clock_priority1=lp1, local_clock_priority2=lp2,
        local_clock_class=lcl, local_clock_accuracy=lac,
        local_clock_log2_variance=lvar, local_clock_time_source=lts,
        master_clock_identity=mci,
        master_clock_priority1=mp1, master_clock_priority2=mp2,
        master_clock_class=mcl, master_clock_accuracy=mac,
        master_clock_log2_variance=mvar, master_clock_time_source=mts,
        mean_path_delay_s=mpd, mean_path_delay_std_s=mpdstd,
        clock_offset_s=co, clock_offset_std_s=costd,
        clock_freq_offset_hz=cfo, clock_freq_offset_std_hz=cfostd,
        master_mac_address=mmac, domain_number=domain,
    )


def _parse_diag(p: bytes) -> LogDiag | None:
    if len(p) < _S_DIAG.size:
        return None
    ts, dtype, ecode = _S_DIAG.unpack_from(p)
    msg = p[_S_DIAG.size:].rstrip(b'\x00').decode('ascii', errors='replace')
    return LogDiag(timestamp_us=ts, diag_type=dtype, error_code=ecode, message=msg)


def _parse_session_info(p: bytes) -> LogSessionInfo | None:
    if len(p) < _S_SESSION.size:
        return None
    page_idx, page_cnt, data_size = _S_SESSION.unpack_from(p)
    data = p[_S_SESSION.size: _S_SESSION.size + data_size]
    return LogSessionInfo(page_index=page_idx, page_count=page_cnt,
                          data_size=data_size, data=data)


def _parse_gps_sat(cls: type, p: bytes) -> Any | None:
    if len(p) < _S_SAT_HEADER.size:
        return None
    ts, _reserved, nr_sats = _S_SAT_HEADER.unpack_from(p)
    offset = _S_SAT_HEADER.size
    satellites: list[SatInfo] = []
    for _ in range(nr_sats):
        if offset + _S_SAT_ENTRY.size > len(p):
            break
        sat_id, elev, az, sat_flags, nr_signals = _S_SAT_ENTRY.unpack_from(p, offset)
        offset += _S_SAT_ENTRY.size
        signals: list[SignalInfo] = []
        for _ in range(nr_signals):
            if offset + _S_SIGNAL_ENTRY.size > len(p):
                break
            sig_id, sig_flags, snr = _S_SIGNAL_ENTRY.unpack_from(p, offset)
            offset += _S_SIGNAL_ENTRY.size
            signals.append(SignalInfo(signal_id=sig_id, flags=sig_flags, snr_db=snr))
        satellites.append(SatInfo(
            satellite_id=sat_id, elevation_deg=elev, azimuth_deg=az,
            flags=sat_flags, signals=tuple(signals),
        ))
    return cls(timestamp_us=ts, satellites=tuple(satellites))


# ─── Dispatch table ─────────────────────────────────────────────────────────

class FrameParser:
    """Maps message IDs to typed dataclass instances.

    Call :meth:`parse` with a message ID and raw payload bytes; returns the
    appropriate dataclass or ``None`` if the ID is unknown or the payload is
    malformed.
    """

    _HANDLERS: ClassVar[dict[int, Callable[[bytes], Any | None]]] = {
        MSG_STATUS:            _parse_status,
        MSG_UTC_TIME:          _parse_utc_time,
        MSG_IMU_DATA:          _parse_imu_data,
        MSG_MAG:               _parse_mag,
        MSG_MAG_CALIB:         _parse_mag_calib,
        MSG_EKF_EULER:         _parse_ekf_euler,
        MSG_EKF_QUAT:          _parse_ekf_quat,
        MSG_EKF_NAV:           _parse_ekf_nav,
        MSG_SHIP_MOTION:       _parse_ship_motion,
        MSG_GPS1_VEL:          lambda p: _parse_gps_vel(LogGps1Vel, p),
        MSG_GPS1_POS:          lambda p: _parse_gps_pos(LogGps1Pos, p),
        MSG_GPS1_HDT:          lambda p: _parse_gps_hdt(LogGps1Hdt, p),
        MSG_GPS2_VEL:          lambda p: _parse_gps_vel(LogGps2Vel, p),
        MSG_GPS2_POS:          lambda p: _parse_gps_pos(LogGps2Pos, p),
        MSG_GPS2_HDT:          lambda p: _parse_gps_hdt(LogGps2Hdt, p),
        MSG_ODO_VEL:           _parse_odo_vel,
        MSG_EVENT_A:           lambda p: _parse_event(LogEventA, p),
        MSG_EVENT_B:           lambda p: _parse_event(LogEventB, p),
        MSG_EVENT_C:           lambda p: _parse_event(LogEventC, p),
        MSG_EVENT_D:           lambda p: _parse_event(LogEventD, p),
        MSG_EVENT_E:           lambda p: _parse_event(LogEventE, p),
        MSG_DVL_BOTTOM_TRACK:  lambda p: _parse_dvl(LogDvlBottomTrack, p),
        MSG_DVL_WATER_TRACK:   lambda p: _parse_dvl(LogDvlWaterTrack, p),
        MSG_GPS1_RAW:          lambda p: LogGps1Raw(raw_data=p),
        MSG_SHIP_MOTION_HP:    _parse_ship_motion_hp,
        MSG_AIR_DATA:          _parse_air_data,
        MSG_USBL:              _parse_usbl,
        MSG_GPS2_RAW:          lambda p: LogGps2Raw(raw_data=p),
        MSG_IMU_SHORT:         _parse_imu_short,
        MSG_EVENT_OUT_A:       lambda p: _parse_event(LogEventOutA, p),
        MSG_EVENT_OUT_B:       lambda p: _parse_event(LogEventOutB, p),
        MSG_DEPTH:             _parse_depth,
        MSG_DIAG:              _parse_diag,
        MSG_RTCM_RAW:          lambda p: LogRtcmRaw(raw_data=p),
        MSG_GPS1_SAT:          lambda p: _parse_gps_sat(LogGps1Sat, p),
        MSG_GPS2_SAT:          lambda p: _parse_gps_sat(LogGps2Sat, p),
        MSG_EKF_ROT_ACCEL_BODY: _parse_ekf_rot_accel_body,
        MSG_EKF_ROT_ACCEL_NED:  _parse_ekf_rot_accel_ned,
        MSG_EKF_VEL_BODY:      _parse_ekf_vel_body,
        MSG_SESSION_INFO:      _parse_session_info,
        MSG_PTP_STATUS:        _parse_ptp_status,
        MSG_VELOCITY_1:        _parse_velocity_1,
        MSG_VIB_MON_FFT:       lambda p: LogVibMonFft(raw_data=p),
        MSG_VIB_MON_REPORT:    lambda p: LogVibMonReport(raw_data=p),
        MSG_EKF_AIR_DATA:      _parse_ekf_air_data,
        MSG_POSITION_1:        _parse_position_1,
    }

    @classmethod
    def parse(cls, msg_id: int, payload: bytes) -> Any | None:
        """Parse *payload* for the given *msg_id*.

        Returns the typed dataclass on success, ``None`` for unknown IDs or
        truncated/malformed payloads.
        """
        handler = cls._HANDLERS.get(msg_id)
        if handler is None:
            return None
        try:
            return handler(payload)
        except struct.error:
            _log.warning("Malformed payload for msg_id=0x%02X len=%d", msg_id, len(payload))
            return None
