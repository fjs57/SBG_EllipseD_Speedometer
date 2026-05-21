"""Real-time speed vs. time plot (pyqtgraph).

Displays the absolute value of forward speed so that reversing shows as a
positive value on the chart, matching the gauge behaviour.

The Y axis tracks the same range as the gauge (computed by
:func:`~app.config.compute_speed_range`) and updates whenever the target
speed changes.
"""

from __future__ import annotations

import time
from collections import deque

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt

from app.config import (
    COLOR_BG, COLOR_SPEED_LINE, COLOR_TARGET_LINE, COLOR_TEXT,
    PLOT_HISTORY_SECONDS, compute_speed_range,
)


class SpeedPlot(pg.PlotWidget):
    """Rolling real-time speed chart (absolute value)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._use_kmh: bool = False
        self._target_ms: float = 0.0
        self._t0: float | None = None

        max_pts = PLOT_HISTORY_SECONDS * 50
        self._times:     deque[float] = deque(maxlen=max_pts)
        self._speeds_ms: deque[float] = deque(maxlen=max_pts)   # signed

        self._setup_plot()

    # ── Public API ────────────────────────────────────────────────────────────

    def add_speed(self, speed_ms: float) -> None:
        """Append a new (signed) speed sample; plots the absolute value."""
        now = time.monotonic()
        if self._t0 is None:
            self._t0 = now
        self._times.append(now - self._t0)
        self._speeds_ms.append(speed_ms)
        self._refresh()

    def set_target(self, target_ms: float) -> None:
        """Update the target reference line and Y axis range."""
        self._target_ms = target_ms
        self._target_line.setValue(self._to_display(abs(target_ms)))
        self._apply_y_range()

    def set_unit(self, use_kmh: bool) -> None:
        self._use_kmh = use_kmh
        unit = "km/h" if use_kmh else "m/s"
        self.setLabel("left", "Speed", units=unit, color=COLOR_TEXT)
        self._target_line.setValue(self._to_display(abs(self._target_ms)))
        self._apply_y_range()
        self._refresh()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _to_display(self, speed_ms: float) -> float:
        return speed_ms * 3.6 if self._use_kmh else speed_ms

    def _setup_plot(self) -> None:
        self.setBackground(COLOR_BG)
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel("left", "Speed", units="m/s", color=COLOR_TEXT)
        self.setLabel("bottom", "Time", units="s", color=COLOR_TEXT)

        for axis_name in ("left", "bottom"):
            ax = self.getAxis(axis_name)
            ax.setTextPen(pg.mkPen(COLOR_TEXT))
            ax.setPen(pg.mkPen(COLOR_TEXT))

        self._speed_curve = self.plot(
            pen=pg.mkPen(COLOR_SPEED_LINE, width=2), name="Speed"
        )
        self._target_line = pg.InfiniteLine(
            pos=0.0, angle=0,
            pen=pg.mkPen(COLOR_TARGET_LINE, width=1.5, style=Qt.DashLine),
            label="Target",
            labelOpts={"color": COLOR_TARGET_LINE, "position": 0.95},
        )
        self.addItem(self._target_line)
        self._apply_y_range()

    def _apply_y_range(self) -> None:
        """Set the Y axis range to match the gauge range for the current target.

        Rounding is performed in the display unit so the axis matches the gauge
        exactly (same fix as SpeedGauge._display_range).
        """
        target_disp = self._to_display(abs(self._target_ms))
        d_min_disp, d_max_disp = compute_speed_range(target_disp)
        margin = (d_max_disp - d_min_disp) * 0.10
        self.setYRange(d_min_disp, d_max_disp + margin, padding=0)

    def _refresh(self) -> None:
        if not self._times:
            return

        t_arr = np.asarray(self._times, dtype=float)
        # Plot absolute value — negative (reversing) shows as positive magnitude
        v_arr = np.abs(np.asarray(self._speeds_ms, dtype=float))
        if self._use_kmh:
            v_arr = v_arr * 3.6

        t_now = t_arr[-1]
        mask  = t_arr >= t_now - PLOT_HISTORY_SECONDS
        self._speed_curve.setData(t_arr[mask], v_arr[mask])
        self.setXRange(max(0.0, t_now - PLOT_HISTORY_SECONDS), t_now, padding=0)
