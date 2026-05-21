"""Custom arc speedometer gauge — auto-scaled, target-centred, nice tick spacing.

Tick spacing is chosen from the preferred set
``{0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50}`` (in the display
unit) so that labels are always round, readable numbers.

The range is computed by :func:`~app.config.compute_speed_range` from the
current target rounded to the nearest integer *in the display unit*.

Negative speeds (reversing) are displayed as their absolute value.
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
    GAUGE_SPAN, GAUGE_START_ANGLE,
    compute_speed_range,
)

# ── Nice tick spacing ─────────────────────────────────────────────────────────

_NICE_STEPS = (
    0.01, 0.02, 0.05,
    0.1,  0.2,  0.5,
    1.0,  2.0,  5.0,
    10.0, 20.0, 50.0, 100.0,
)


def _pick_major_step(span: float, max_ticks: int = 12,
                     floor_step: float = 0.0) -> float:
    """Smallest nice step giving at most *max_ticks* major intervals.

    *floor_step* sets a minimum step regardless of tick count — used to prevent
    sub-1 km/h major steps which would produce duplicate integer labels.
    """
    min_step = max(span / max_ticks, floor_step)
    for s in _NICE_STEPS:
        if s >= min_step - 1e-9:
            return s
    return _NICE_STEPS[-1]


def _pick_minor_step(major: float) -> float:
    """Largest nice step that divides *major* into exactly 2, 4 or 5 parts."""
    for n_parts in (5, 4, 2):
        candidate = major / n_parts
        for s in _NICE_STEPS:
            if abs(s - candidate) < candidate * 1e-6:
                return s
    return major / 5.0


def _label_fmt(step: float, use_kmh: bool) -> str:
    """printf-style format string for tick labels at *step* size."""
    if use_kmh:
        return ".0f"       # km/h → always integer
    if step >= 1.0:
        return ".0f"
    if step >= 0.1:
        return ".1f"
    if step >= 0.01:
        return ".2f"
    return ".3f"


# ── Widget ────────────────────────────────────────────────────────────────────

class SpeedGauge(QWidget):
    """Arc speedometer with auto-scaling range and nice tick spacing.

    The gauge always displays |speed| — negative (reversing) and positive
    forward motion both move the needle clockwise.

    Call :meth:`set_speed` with the raw signed body-frame X velocity.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._speed_ms: float = 0.0
        self._target_ms: float = 0.0
        self._margin_ms: float = 1.0 / 3.6
        self._use_kmh: bool = False
        self.setMinimumSize(280, 280)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_speed(self, speed_ms: float) -> None:
        self._speed_ms = speed_ms
        self.update()

    def set_target(self, target_ms: float) -> None:
        self._target_ms = max(0.0, target_ms)
        self.update()

    def set_margin(self, margin_ms: float) -> None:
        self._margin_ms = max(0.0, margin_ms)
        self.update()

    def set_unit(self, use_kmh: bool) -> None:
        self._use_kmh = use_kmh
        self.update()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _display_range(self) -> tuple[float, float]:
        """Return (d_min_ms, d_max_ms).

        Rounding is performed in the display unit so that e.g. 3 km/h rounds
        to 3 (giving [0, 6] km/h) rather than to round(3/3.6)=1 m/s.
        """
        factor = 3.6 if self._use_kmh else 1.0
        target_disp = self._target_ms * factor
        d_min_d, d_max_d = compute_speed_range(target_disp)
        inv = 1.0 / factor
        return d_min_d * inv, d_max_d * inv

    def _to_display(self, value_ms: float) -> float:
        return value_ms * 3.6 if self._use_kmh else value_ms

    def _unit_str(self) -> str:
        return "km/h" if self._use_kmh else "m/s"

    def _ms_to_qp_angle(self, speed_ms: float) -> float:
        d_min, d_max = self._display_range()
        span = d_max - d_min
        if span <= 0.0:
            return float(GAUGE_START_ANGLE)
        ratio = max(0.0, min(1.0, (abs(speed_ms) - d_min) / span))
        return float(GAUGE_START_ANGLE) - ratio * float(GAUGE_SPAN)

    @staticmethod
    def _pt(angle_qp: float, radius: float, cx: float, cy: float) -> QPointF:
        rad = math.radians(angle_qp)
        return QPointF(cx + radius * math.cos(rad),
                       cy - radius * math.sin(rad))

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h   = float(self.width()), float(self.height())
        size   = min(w, h)
        cx     = w / 2.0
        cy     = h / 2.0 + size * 0.06

        r      = size * 0.43
        arc_w  = size * 0.095
        rect   = QRectF(cx - r, cy - r, r * 2.0, r * 2.0)

        d_min, d_max = self._display_range()
        d_range = d_max - d_min

        # 1 ── Background arc ──────────────────────────────────────────────────
        pen = QPen(QColor(COLOR_GAUGE_BG), arc_w)
        pen.setCapStyle(Qt.FlatCap)
        p.setPen(pen)
        p.drawArc(rect, GAUGE_START_ANGLE * 16, -GAUGE_SPAN * 16)

        # 2 ── Target zone (green band) ────────────────────────────────────────
        if self._target_ms > 0.0:
            lo = max(d_min, self._target_ms - self._margin_ms)
            hi = min(d_max, self._target_ms + self._margin_ms)
            if hi > lo:
                a_lo  = self._ms_to_qp_angle(lo)
                a_hi  = self._ms_to_qp_angle(hi)
                pen   = QPen(QColor(COLOR_ZONE_GREEN), arc_w)
                pen.setCapStyle(Qt.FlatCap)
                p.setPen(pen)
                p.drawArc(rect, int(a_lo * 16), int((a_hi - a_lo) * 16))

            if d_min <= self._target_ms <= d_max:
                t_a   = self._ms_to_qp_angle(self._target_ms)
                pen_t = QPen(QColor("#ffffff"), size * 0.010)
                pen_t.setCapStyle(Qt.RoundCap)
                p.setPen(pen_t)
                p.drawLine(self._pt(t_a, r - arc_w * 0.45, cx, cy),
                           self._pt(t_a, r + arc_w * 0.45, cx, cy))

        # 3 ── Current speed arc ───────────────────────────────────────────────
        spd_abs = abs(self._speed_ms)
        if spd_abs > d_min:
            on_target  = abs(spd_abs - self._target_ms) <= self._margin_ms
            arc_color  = COLOR_ZONE_GREEN if on_target else COLOR_SPEED_LINE
            cur_a      = self._ms_to_qp_angle(min(spd_abs, d_max))
            start_a    = self._ms_to_qp_angle(d_min)
            pen = QPen(QColor(arc_color), arc_w * 0.45)
            pen.setCapStyle(Qt.FlatCap)
            p.setPen(pen)
            p.drawArc(rect, int(start_a * 16), int((cur_a - start_a) * 16))

        # 4 ── Tick marks — nice spacing in display unit ───────────────────────
        factor      = 3.6 if self._use_kmh else 1.0
        d_min_d     = d_min * factor
        d_max_d     = d_max * factor
        span_d      = d_max_d - d_min_d
        outer_tick  = r - arc_w * 0.55

        # In km/h mode the labels are integers (.0f), so the major step must be
        # at least 1 km/h — otherwise consecutive 0.5-step ticks would both
        # round to the same integer and produce duplicate labels.
        major_d = _pick_major_step(span_d, floor_step=1.0 if self._use_kmh else 0.0)
        minor_d = _pick_minor_step(major_d)
        fmt     = _label_fmt(major_d, self._use_kmh)

        # First minor tick at or after d_min_d
        first_d = math.ceil(round(d_min_d / minor_d, 8)) * minor_d
        t_d = first_d

        while t_d <= d_max_d + minor_d * 1e-6:
            # Major if t_d is a multiple of major_d (with float tolerance)
            n        = t_d / major_d
            is_major = abs(n - round(n)) < 1e-6

            val_ms = t_d / factor
            ratio  = (val_ms - d_min) / d_range if d_range else 0.0
            angle  = GAUGE_START_ANGLE - ratio * GAUGE_SPAN

            tick_len = size * 0.050 if is_major else size * 0.028
            p.setPen(QPen(
                QColor(COLOR_TEXT if is_major else COLOR_TEXT_DIM),
                size * (0.008 if is_major else 0.004),
            ))
            p.drawLine(self._pt(angle, outer_tick, cx, cy),
                       self._pt(angle, outer_tick - tick_len, cx, cy))

            if is_major:
                label = f"{t_d:{fmt}}"
                font  = QFont("Arial", max(7, int(size * 0.040)))
                p.setFont(font)
                p.setPen(QPen(QColor(COLOR_TEXT)))
                lp = self._pt(angle, outer_tick - tick_len - size * 0.055, cx, cy)
                fm = QFontMetricsF(font)
                p.drawText(
                    QPointF(lp.x() - fm.horizontalAdvance(label) / 2.0,
                            lp.y() + fm.height() * 0.35),
                    label,
                )

            # Advance, rounding to avoid floating-point drift
            t_d = round(t_d + minor_d, 10)

        # 5 ── Needle ──────────────────────────────────────────────────────────
        needle_r = outer_tick - size * 0.015
        n_ang  = self._ms_to_qp_angle(self._speed_ms)
        n_rad  = math.radians(n_ang)
        tip    = self._pt(n_ang, needle_r, cx, cy)
        tail   = QPointF(cx - size * 0.09 * math.cos(n_rad),
                         cy + size * 0.09 * math.sin(n_rad))
        perp   = math.radians(n_ang + 90.0)
        hb     = size * 0.016
        bl     = QPointF(cx + hb * math.cos(perp), cy - hb * math.sin(perp))
        br_pt  = QPointF(cx - hb * math.cos(perp), cy + hb * math.sin(perp))

        p.setBrush(QBrush(QColor(COLOR_NEEDLE)))
        p.setPen(Qt.NoPen)
        p.drawPolygon(QPolygonF([tip, bl, tail, br_pt]))

        hub_r = size * 0.036
        p.setBrush(QBrush(QColor(COLOR_GAUGE_HUB)))
        p.setPen(QPen(QColor("#50507a"), size * 0.007))
        p.drawEllipse(QPointF(cx, cy), hub_r, hub_r)

        # 6 ── Digital readout ─────────────────────────────────────────────────
        val_str  = f"{self._to_display(abs(self._speed_ms)):.2f}"
        font_val = QFont("Arial", max(14, int(size * 0.115)), QFont.Bold)
        p.setFont(font_val)
        p.setPen(QPen(QColor("#ffffff")))
        fm_v = QFontMetricsF(font_val)
        p.drawText(QPointF(cx - fm_v.horizontalAdvance(val_str) / 2.0,
                           cy + size * 0.20), val_str)

        # 7 ── Range label ─────────────────────────────────────────────────────
        range_str = f"[{d_min_d:{fmt}} - {d_max_d:{fmt}}] {self._unit_str()}"
        font_r = QFont("Arial", max(6, int(size * 0.038)))
        p.setFont(font_r)
        p.setPen(QPen(QColor(COLOR_TEXT_DIM)))
        fm_r = QFontMetricsF(font_r)
        p.drawText(QPointF(cx - fm_r.horizontalAdvance(range_str) / 2.0,
                           cy + size * 0.30), range_str)

        p.end()
