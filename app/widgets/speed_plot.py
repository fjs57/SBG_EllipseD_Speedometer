"""Real-time speed vs. time plot (pyqtgraph).

Displays a rolling window of the last :data:`~app.config.PLOT_HISTORY_SECONDS`
seconds.  Two data series are shown:

* **Blue line** — measured forward speed (body-frame X).
* **Red dashed line** — user-set target speed.

All values are stored internally in m/s and converted on the fly when the
display unit is changed.
"""

from __future__ import annotations

import time
from collections import deque

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt

from app.config import (
    COLOR_BG, COLOR_SPEED_LINE, COLOR_TARGET_LINE, COLOR_TEXT,
    MAX_SPEED_KMH, MAX_SPEED_MS, PLOT_HISTORY_SECONDS,
)


class SpeedPlot(pg.PlotWidget):
    """Rolling real-time speed chart."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._use_kmh: bool = False
        self._target_ms: float = 0.0
        self._t0: float | None = None

        # Pre-allocate rolling buffers (50 Hz × 60 s = 3 000 samples max)
        max_pts = PLOT_HISTORY_SECONDS * 50
        self._times: deque[float] = deque(maxlen=max_pts)
        self._speeds_ms: deque[float] = deque(maxlen=max_pts)

        self._setup_plot()

    # ── Public API ────────────────────────────────────────────────────────────

    def add_speed(self, speed_ms: float) -> None:
        """Append a new speed sample and refresh the chart."""
        now = time.monotonic()
        if self._t0 is None:
            self._t0 = now
        self._times.append(now - self._t0)
        self._speeds_ms.append(speed_ms)
        self._refresh()

    def set_target(self, target_ms: float) -> None:
        """Update the target speed reference line."""
        self._target_ms = target_ms
        self._target_line.setValue(self._to_display(target_ms))

    def set_unit(self, use_kmh: bool) -> None:
        """Switch between km/h and m/s display without clearing history."""
        self._use_kmh = use_kmh
        unit = "km/h" if use_kmh else "m/s"
        y_max = MAX_SPEED_KMH if use_kmh else MAX_SPEED_MS
        self.setLabel("left", "Speed", units=unit, color=COLOR_TEXT)
        self.setYRange(0, y_max, padding=0.05)
        self._target_line.setValue(self._to_display(self._target_ms))
        self._refresh()   # rescale existing data

    # ── Internal ──────────────────────────────────────────────────────────────

    def _to_display(self, speed_ms: float) -> float:
        return speed_ms * 3.6 if self._use_kmh else speed_ms

    def _setup_plot(self) -> None:
        self.setBackground(COLOR_BG)
        self.showGrid(x=True, y=True, alpha=0.25)
        self.setLabel("left", "Speed", units="m/s", color=COLOR_TEXT)
        self.setLabel("bottom", "Time", units="s", color=COLOR_TEXT)

        # Style axis labels to match the dark theme
        for axis_name in ("left", "bottom"):
            ax = self.getAxis(axis_name)
            ax.setTextPen(pg.mkPen(COLOR_TEXT))
            ax.setPen(pg.mkPen(COLOR_TEXT))

        self._speed_curve = self.plot(
            pen=pg.mkPen(COLOR_SPEED_LINE, width=2), name="Speed"
        )

        # Horizontal dashed line for target speed (infinite line)
        self._target_line = pg.InfiniteLine(
            pos=0.0,
            angle=0,
            pen=pg.mkPen(COLOR_TARGET_LINE, width=1.5, style=Qt.DashLine),
            label="Target",
            labelOpts={"color": COLOR_TARGET_LINE, "position": 0.95},
        )
        self.addItem(self._target_line)
        self.setYRange(0, MAX_SPEED_MS, padding=0.05)

    def _refresh(self) -> None:
        """Redraw curves from the current buffer contents."""
        if not self._times:
            return

        t_arr = np.asarray(self._times, dtype=float)
        v_arr = np.asarray(self._speeds_ms, dtype=float)
        if self._use_kmh:
            v_arr = v_arr * 3.6

        t_now = t_arr[-1]
        mask = t_arr >= t_now - PLOT_HISTORY_SECONDS
        self._speed_curve.setData(t_arr[mask], v_arr[mask])
        self.setXRange(max(0.0, t_now - PLOT_HISTORY_SECONDS), t_now, padding=0)
