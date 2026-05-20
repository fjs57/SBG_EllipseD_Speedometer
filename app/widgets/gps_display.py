"""GPS position and INS solution-type display panel.

Coordinates are shown with 7 decimal places, giving ≈ 1 cm resolution
at the latitude of Brussels (≈ 50.85 °N):

* 1 ° latitude  ≈ 111 195 m  →  1 × 10⁻⁷ ° ≈ 0.011 m
* 1 ° longitude ≈  71 600 m  →  1 × 10⁻⁷ ° ≈ 0.007 m
"""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QGroupBox, QHBoxLayout, QLabel,
                               QSizePolicy, QVBoxLayout, QWidget)

from app.config import SOLUTION_LABELS


class GPSDisplay(QWidget):
    """Panel with three coordinate rows and a colour-coded solution indicator."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def update_solution(self, solution_status: int) -> None:
        """Colour the solution label according to the current mode.

        Args:
            solution_status: Raw 32-bit SOLUTION_STATUS field.  Bits [0-3]
                             encode the :class:`~sbg_ellipsd.enums.SolutionMode`.
        """
        mode = solution_status & 0x0F
        name, color = SOLUTION_LABELS.get(mode, ("Unknown", "#606060"))
        self._sol_dot.setStyleSheet(f"color: {color};")
        self._sol_value.setText(name)
        self._sol_value.setStyleSheet(f"color: {color}; font-weight: bold;")

    def update_position(self, lat: float, lon: float, alt: float) -> None:
        """Refresh coordinate rows.

        Args:
            lat: Latitude in decimal degrees (positive = North).
            lon: Longitude in decimal degrees (positive = East).
            alt: Altitude above mean sea level in metres.
        """
        lat_dir = "N" if lat >= 0.0 else "S"
        lon_dir = "E" if lon >= 0.0 else "W"
        self._lat_val.setText(f"{abs(lat):.7f} °{lat_dir}")
        self._lon_val.setText(f"{abs(lon):.7f} °{lon_dir}")
        self._alt_val.setText(f"{alt:+.2f} m")

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # Solution type row ──────────────────────────────────────────────────
        sol_box = QGroupBox("INS Solution")
        sol_layout = QHBoxLayout(sol_box)
        sol_layout.setContentsMargins(8, 4, 8, 4)

        self._sol_dot = QLabel("●")
        self._sol_dot.setFont(QFont("Arial", 14))

        self._sol_value = QLabel("—")
        self._sol_value.setFont(QFont("Arial", 11))

        sol_layout.addWidget(self._sol_dot)
        sol_layout.addWidget(self._sol_value)
        sol_layout.addStretch()
        root.addWidget(sol_box)

        # Coordinates ────────────────────────────────────────────────────────
        coord_box = QGroupBox("GPS Position")
        coord_layout = QVBoxLayout(coord_box)
        coord_layout.setContentsMargins(8, 4, 8, 6)
        coord_layout.setSpacing(4)

        mono = QFont("Courier New", 10)

        self._lat_val = self._coord_row("Lat:", coord_layout, mono)
        self._lon_val = self._coord_row("Lon:", coord_layout, mono)
        self._alt_val = self._coord_row("Alt:", coord_layout, mono)

        root.addWidget(coord_box)
        root.addStretch()

    @staticmethod
    def _coord_row(prefix: str, layout: QVBoxLayout,
                   font: QFont) -> QLabel:
        """Build a label-pair row and add it to *layout*; return the value label."""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel(prefix)
        lbl.setFont(font)
        lbl.setFixedWidth(34)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        val = QLabel("—")
        val.setFont(font)
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        val.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        h.addWidget(lbl)
        h.addWidget(val)
        layout.addWidget(row)
        return val
