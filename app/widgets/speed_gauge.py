"""Custom arc speedometer gauge — auto-scaled, target-centred.

The gauge always displays a window of ``[target − view_half, target + view_half]``
in m/s (clamped to ``[0, MAX_SPEED_MS]``), so the target speed sits at the
12 o'clock position (centre of the 270° arc).  When no target is set the full
range ``[0, MAX_SPEED_MS]`` is shown.

Arc geometry:
  The 270° arc sweeps clockwise from the lower-left (min speed) through the
  12 o'clock position (mid / target) to the lower-right (max speed).

  Angles are in QPainter convention (degrees, CCW from the 3 o'clock position).
  ``GAUGE_START_ANGLE = 225°`` is the lower-left (7:30 o'clock).
  The arc ends at ``225° − 270° = −45°`` which is the lower-right (4:30 o'clock).

Body-frame convention: X = forward, Y = right, Z = down.
"""

from __future__ import annotations

import math

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import (QBrush, QColor, QFont, QFontMetricsF,
                          QPainter, QPen, QPolygonF)
from PyQt5.QtWidgets import QWidget

from app.config import (
    COLOR_GAUGE_BG, COLOR_GAUGE_HUB, COLOR_NEEDLE, COLOR_SPEED_LINE,
    COLOR_TEXT, COLOR_TEXT_DIM, COLOR_ZONE_GREEN,
    GAUGE_MAJOR_TICKS, GAUGE_MINOR_TICKS, GAUGE_SPAN, GAUGE_START_ANGLE,
    GAUGE_VIEW_HALF_MS, MAX_SPEED_MS,
)


class SpeedGauge(QWidget):
    """Auto-scaled arc speedometer.

    The displayed speed range auto-centres on the current target whenever
    :meth:`set_target` or :meth:`set_view_half` is called.

    All internal speeds are stored in m/s.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._speed_ms: float = 0.0
        self._target_ms: float = 0.0
        self._margin_ms: float = 1.0 / 3.6
        self._view_half_ms: float = GAUGE_VIEW_HALF_MS
        self._use_kmh: bool = False

        # Cache the display range so we don't recompute inside paintEvent
        self._d_min_ms: float = 0.0
        self._d_max_ms: float = MAX_SPEED_MS
        self._update_range()

        self.setMinimumSize(280, 280)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_speed(self, speed_ms: float) -> None:
        self._speed_ms = max(0.0, speed_ms)
        self.update()

    def set_target(self, target_ms: float) -> None:
        self._target_ms = max(0.0, min(target_ms, MAX_SPEED_MS))
        self._update_range()
        self.update()

    def set_margin(self, margin_ms: float) -> None:
        """Half-width of the green zone in m/s."""
        self._margin_ms = max(0.0, margin_ms)
        self.update()

    def set_view_half(self, view_half_ms: float) -> None:
        """Half the displayed speed range (in m/s).

        The gauge shows ``[target − view_half, target + view_half]``,
        clamped to ``[0, MAX_SPEED_MS]``.
        """
        self._view_half_ms = max(0.5, view_half_ms)
        self._update_range()
        self.update()

    def set_unit(self, use_kmh: bool) -> None:
        self._use_kmh = use_kmh
        self.update()

    # ── Internal geometry helpers ─────────────────────────────────────────────

    def _update_range(self) -> None:
        """Recompute the visible speed window centred on the current target."""
        if self._target_ms <= 0.0 or self._view_half_ms <= 0.0:
            self._d_min_ms = 0.0
            self._d_max_ms = MAX_SPEED_MS
            return

        d_min = self._target_ms - self._view_half_ms
        d_max = self._target_ms + self._view_half_ms

        # Clamp to physical limits while preserving the total range
        if d_min < 0.0:
            shift = -d_min
            d_min = 0.0
            d_max = min(MAX_SPEED_MS, d_max + shift)
        if d_max > MAX_SPEED_MS:
            shift = d_max - MAX_SPEED_MS
            d_max = MAX_SPEED_MS
            d_min = max(0.0, d_min - shift)

        self._d_min_ms = d_min
        self._d_max_ms = d_max

    def _to_display(self, value_ms: float) -> float:
        return value_ms * 3.6 if self._use_kmh else value_ms

    def _unit_str(self) -> str:
        return "km/h" if self._use_kmh else "m/s"

    def _ms_to_qp_angle(self, speed_ms: float) -> float:
        """Map a speed (m/s) to a QPainter arc angle (°, CCW from 3 o'clock).

        Speeds outside the display window are clamped to the arc ends.
        """
        span = self._d_max_ms - self._d_min_ms
        if span <= 0.0:
            return float(GAUGE_START_ANGLE)
        ratio = max(0.0, min(1.0, (speed_ms - self._d_min_ms) / span))
        return float(GAUGE_START_ANGLE) - ratio * float(GAUGE_SPAN)

    @staticmethod
    def _pt(angle_qp: float, radius: float, cx: float, cy: float) -> QPointF:
        """Convert a QPainter angle to a screen point (Y-axis inverted)."""
        rad = math.radians(angle_qp)
        return QPointF(cx + radius * math.cos(rad),
                       cy - radius * math.sin(rad))

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = float(self.width()), float(self.height())
        size = min(w, h)
        cx = w / 2.0
        cy = h / 2.0 + size * 0.06   # shift down slightly for top-label clearance

        r = size * 0.43
        arc_w = size * 0.095
        rect = QRectF(cx - r, cy - r, r * 2.0, r * 2.0)

        # 1 ── Background arc (full gauge range, dark) ─────────────────────────
        pen = QPen(QColor(COLOR_GAUGE_BG), arc_w)
        pen.setCapStyle(Qt.FlatCap)
        p.setPen(pen)
        p.drawArc(rect, GAUGE_START_ANGLE * 16, -GAUGE_SPAN * 16)

        # 2 ── Target zone (green band centred on target) ──────────────────────
        if self._target_ms > 0.0:
            lo = max(self._d_min_ms, self._target_ms - self._margin_ms)
            hi = min(self._d_max_ms, self._target_ms + self._margin_ms)
            if hi > lo:
                a_lo = self._ms_to_qp_angle(lo)
                a_hi = self._ms_to_qp_angle(hi)
                span = int((a_hi - a_lo) * 16)     # negative → CW

                pen = QPen(QColor(COLOR_ZONE_GREEN), arc_w)
                pen.setCapStyle(Qt.FlatCap)
                p.setPen(pen)
                p.drawArc(rect, int(a_lo * 16), span)

            # Bright tick at the exact target speed (only if in view range)
            if self._d_min_ms <= self._target_ms <= self._d_max_ms:
                t_a = self._ms_to_qp_angle(self._target_ms)
                pen_t = QPen(QColor("#ffffff"), size * 0.010)
                pen_t.setCapStyle(Qt.RoundCap)
                p.setPen(pen_t)
                p.drawLine(self._pt(t_a, r - arc_w * 0.45, cx, cy),
                           self._pt(t_a, r + arc_w * 0.45, cx, cy))

        # 3 ── Current speed progress arc (blue / green when on target) ────────
        if self._speed_ms > self._d_min_ms:
            on_target = abs(self._speed_ms - self._target_ms) <= self._margin_ms
            arc_color = COLOR_ZONE_GREEN if on_target else COLOR_SPEED_LINE
            cur_a = self._ms_to_qp_angle(min(self._speed_ms, self._d_max_ms))
            start_a = self._ms_to_qp_angle(self._d_min_ms)
            span = int((cur_a - start_a) * 16)      # negative → CW

            pen = QPen(QColor(arc_color), arc_w * 0.45)
            pen.setCapStyle(Qt.FlatCap)
            p.setPen(pen)
            p.drawArc(rect, int(start_a * 16), span)

        # 4 ── Tick marks and scale labels ─────────────────────────────────────
        total_minor = GAUGE_MAJOR_TICKS * GAUGE_MINOR_TICKS
        outer_tick = r - arc_w * 0.55
        d_range = self._d_max_ms - self._d_min_ms

        for i in range(total_minor + 1):
            is_major = (i % GAUGE_MINOR_TICKS == 0)
            ratio = i / total_minor
            angle = GAUGE_START_ANGLE - ratio * GAUGE_SPAN

            tick_len = size * 0.050 if is_major else size * 0.028
            pen = QPen(
                QColor(COLOR_TEXT if is_major else COLOR_TEXT_DIM),
                size * (0.008 if is_major else 0.004),
            )
            p.setPen(pen)
            p.drawLine(self._pt(angle, outer_tick, cx, cy),
                       self._pt(angle, outer_tick - tick_len, cx, cy))

            if is_major:
                # Speed value at this tick position (in the current display range)
                val_ms = self._d_min_ms + ratio * d_range
                val_disp = self._to_display(val_ms)
                # Format: 1 decimal for m/s, 0 for km/h
                label = f"{val_disp:.1f}" if not self._use_kmh else f"{val_disp:.0f}"
                font = QFont("Arial", max(7, int(size * 0.040)))
                p.setFont(font)
                p.setPen(QPen(QColor(COLOR_TEXT)))
                lp = self._pt(angle, outer_tick - tick_len - size * 0.055, cx, cy)
                fm = QFontMetricsF(font)
                bw = fm.horizontalAdvance(label)
                bh = fm.height()
                p.drawText(QPointF(lp.x() - bw / 2.0, lp.y() + bh * 0.35), label)

        # 5 ── Needle ──────────────────────────────────────────────────────────
        needle_r = outer_tick - size * 0.015
        n_ang = self._ms_to_qp_angle(self._speed_ms)
        n_rad = math.radians(n_ang)
        tip = self._pt(n_ang, needle_r, cx, cy)
        tail = QPointF(cx - size * 0.09 * math.cos(n_rad),
                       cy + size * 0.09 * math.sin(n_rad))

        perp = math.radians(n_ang + 90.0)
        hb = size * 0.016
        bl = QPointF(cx + hb * math.cos(perp), cy - hb * math.sin(perp))
        br_pt = QPointF(cx - hb * math.cos(perp), cy + hb * math.sin(perp))

        p.setBrush(QBrush(QColor(COLOR_NEEDLE)))
        p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([tip, bl, tail, br_pt]))

        # Hub circle
        hub_r = size * 0.036
        p.setBrush(QBrush(QColor(COLOR_GAUGE_HUB)))
        p.setPen(QPen(QColor("#50507a"), size * 0.007))
        p.drawEllipse(QPointF(cx, cy), hub_r, hub_r)

        # 6 ── Digital readout ─────────────────────────────────────────────────
        val_str = f"{self._to_display(self._speed_ms):.2f}"
        font_val = QFont("Arial", max(14, int(size * 0.115)), QFont.Bold)
        p.setFont(font_val)
        p.setPen(QPen(QColor("#ffffff")))
        fm_v = QFontMetricsF(font_val)
        bw_v = fm_v.horizontalAdvance(val_str)
        p.drawText(QPointF(cx - bw_v / 2.0, cy + size * 0.20), val_str)

        # 7 ── Range label (shows visible min–max) ─────────────────────────────
        d_min_d = self._to_display(self._d_min_ms)
        d_max_d = self._to_display(self._d_max_ms)
        fmt = ".0f" if self._use_kmh else ".1f"
        range_str = f"[{d_min_d:{fmt}} – {d_max_d:{fmt}}] {self._unit_str()}"
        font_r = QFont("Arial", max(6, int(size * 0.038)))
        p.setFont(font_r)
        p.setPen(QPen(QColor(COLOR_TEXT_DIM)))
        fm_r = QFontMetricsF(font_r)
        bw_r = fm_r.horizontalAdvance(range_str)
        p.drawText(QPointF(cx - bw_r / 2.0, cy + size * 0.30), range_str)

        p.end()
