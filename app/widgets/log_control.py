"""Log file control bar — filename input, file-picker and start/stop toggle."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QSizePolicy, QWidget)


class LogControl(QWidget):
    """Horizontal bar for naming and toggling the CSV data logger.

    Signals:
        start_requested (str): Emitted with the chosen file path (no extension)
            when the user clicks *Start Logging*.
        stop_requested ():     Emitted when the user clicks *Stop Logging*.
    """

    start_requested: pyqtSignal = pyqtSignal(str)
    stop_requested: pyqtSignal = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_active(self, active: bool, path: str = "") -> None:
        """Synchronise the widget state with the actual logger state.

        Args:
            active: ``True`` when the logger is currently recording.
            path:   File path to display in the status area (shown on
                    start *and* on stop with "Saved:" prefix).
        """
        self._toggle_btn.setChecked(active)
        self._name_edit.setEnabled(not active)
        self._browse_btn.setEnabled(not active)

        if active:
            self._toggle_btn.setText("■  Stop Logging")
            self._toggle_btn.setStyleSheet(
                "background-color: #8b0000; color: white; font-weight: bold;"
            )
            self._status_lbl.setText(f"● {Path(path).name}")
            self._status_lbl.setStyleSheet("color: #2dc653;")
        else:
            self._toggle_btn.setText("▶  Start Logging")
            self._toggle_btn.setStyleSheet("font-weight: bold;")
            if path:
                self._status_lbl.setText(f"Saved: {Path(path).name}")
                self._status_lbl.setStyleSheet("color: #8080b0;")
            else:
                self._status_lbl.setText("")

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Log file:"))

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("run_01  (no extension needed)")
        self._name_edit.setText(
            f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self._name_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self._name_edit)

        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.setFixedWidth(80)
        self._browse_btn.clicked.connect(self._on_browse)
        layout.addWidget(self._browse_btn)

        self._toggle_btn = QPushButton("▶  Start Logging")
        self._toggle_btn.setFixedWidth(160)
        self._toggle_btn.setCheckable(True)
        self._toggle_btn.setStyleSheet("font-weight: bold;")
        self._toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle_btn)

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont("Arial", 8))
        self._status_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self._status_lbl)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Choose log destination",
            self._name_edit.text(),
            "CSV files (*.csv);;All files (*)",
        )
        if path:
            # Strip extension — DataLogger adds .csv automatically
            p = Path(path)
            self._name_edit.setText(str(p.with_suffix("")))

    def _on_toggle(self, checked: bool) -> None:
        if checked:
            name = self._name_edit.text().strip()
            if not name:
                name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.start_requested.emit(name)
        else:
            self.stop_requested.emit()
