"""Logger Speed — main application entry point.

Usage::

    # Start with default INFO level
    python -m app.main

    # Enable verbose debug / trace output
    python -m app.main --verbose DEBUG
    python -m app.main -v TRACE

Supported ``--verbose`` levels (most → least verbose):
    TRACE  DEBUG  INFO  WARNING  ERROR  FATAL

Layout::

    ┌───────────────────────────────────────────────────────────┐
    │  Port [COM3] Baud [921600 ▼]  [Connect]  ● [RX ● 0 Hz]  │  ← connection bar
    ├──────────────────────┬────────────────────────────────────┤
    │                      │  ── Target & range ─────────────  │
    │                      │  Target: [ 5.00 ] [m/s] [km/h]   │
    │    SPEED GAUGE        │  Zone ±: [ 1.00 ] m/s            │
    │  (auto-centred on     │  View ±: [ 3.00 ] m/s            │
    │   target speed)       │  ── INS Solution ───────────────  │
    │                      │  ● INS (Position)                 │
    │                      │  ── GPS Position ───────────────  │
    │                      │  Lat:  50.8503712 °N              │
    │                      │  Lon:   4.3517000 °E              │
    │                      │  Alt:      35.20 m               │
    ├──────────────────────┴────────────────────────────────────┤
    │           Speed vs. Time (rolling 60 s)                  │
    ├──────────────────────────────────────────────────────────┤
    │  Log file: [run_20260520_123456]  [Browse]  [▶ Start]    │
    └──────────────────────────────────────────────────────────┘
    ┌──────────────────────────────────────────────────────────┐
    │  [Console dock — coloured log output, dockable]          │
    └──────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import argparse
import logging
import sys

from PyQt5.QtCore import Qt, QSize, QTimer, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QPalette
from PyQt5.QtWidgets import (
    QApplication, QComboBox, QDockWidget, QDoubleSpinBox, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QSizePolicy, QSplitter, QStatusBar,
    QVBoxLayout, QWidget,
)

from app.config import (
    COLOR_BG, COLOR_BORDER, COLOR_PANEL, COLOR_TEXT, COLOR_TEXT_DIM,
    DEFAULT_BAUDRATE, DEFAULT_MARGIN_MS, DEFAULT_PORT, DEFAULT_TARGET_MS,
    GAUGE_VIEW_HALF_MS, MAX_SPEED_KMH, MAX_SPEED_MS,
)
from app.core.data_logger import DataLogger
from app.core.ins_controller import INSController
from app.version import COMMIT, FULL_VERSION
from app.widgets.console_panel import ConsolePanel, QtLogHandler, TRACE
from app.widgets.gps_display import GPSDisplay
from app.widgets.log_control import LogControl
from app.widgets.speed_gauge import SpeedGauge
from app.widgets.speed_plot import SpeedPlot

_log = logging.getLogger(__name__)

_BAUDRATES = [9_600, 19_200, 38_400, 57_600, 115_200,
              230_400, 460_800, 921_600]

# Milliseconds the RX LED stays lit after a message arrives
_RX_LED_ON_MS = 120


# ── Logging setup ─────────────────────────────────────────────────────────────

def _add_trace_method() -> None:
    """Inject a ``Logger.trace()`` convenience method (level 5)."""
    def _trace(self: logging.Logger, msg: str, *args, **kwargs) -> None:
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)

    logging.Logger.trace = _trace  # type: ignore[attr-defined]


def _setup_logging(level_name: str) -> QtLogHandler:
    """Configure root logger and return the Qt handler for the console panel."""
    _add_trace_method()

    _level_map: dict[str, int] = {
        "TRACE":   TRACE,
        "DEBUG":   logging.DEBUG,
        "INFO":    logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR":   logging.ERROR,
        "FATAL":   logging.CRITICAL,
    }
    level: int = _level_map.get(level_name, logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # stdout handler (for terminal / IDE output)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(level)
    stdout_handler.setFormatter(fmt)

    # Qt-signal handler (feeds the in-app console panel)
    qt_handler = QtLogHandler()
    qt_handler.setLevel(level)
    qt_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(stdout_handler)
    root.addHandler(qt_handler)

    return qt_handler


# ── Dark palette ──────────────────────────────────────────────────────────────

def _apply_dark_palette(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    bg  = QColor(COLOR_BG)
    pan = QColor(COLOR_PANEL)
    txt = QColor(COLOR_TEXT)
    dim = QColor(COLOR_TEXT_DIM)
    brd = QColor(COLOR_BORDER)

    pal.setColor(QPalette.Window,          bg)
    pal.setColor(QPalette.WindowText,      txt)
    pal.setColor(QPalette.Base,            pan)
    pal.setColor(QPalette.AlternateBase,   bg)
    pal.setColor(QPalette.Text,            txt)
    pal.setColor(QPalette.Button,          pan)
    pal.setColor(QPalette.ButtonText,      txt)
    pal.setColor(QPalette.Highlight,       brd)
    pal.setColor(QPalette.HighlightedText, txt)
    pal.setColor(QPalette.Disabled, QPalette.WindowText, dim)
    pal.setColor(QPalette.Disabled, QPalette.Text,       dim)
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, dim)
    app.setPalette(pal)

    app.setStyleSheet("""
        QGroupBox {
            border: 1px solid #0f3460;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 4px;
            font-weight: bold;
            color: #8080a0;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 4px;
        }
        QLineEdit, QComboBox, QDoubleSpinBox {
            background-color: #16213e;
            border: 1px solid #0f3460;
            border-radius: 3px;
            padding: 2px 4px;
            color: #e0e0e0;
        }
        QDockWidget::title {
            background: #16213e;
            padding: 4px;
            font-weight: bold;
            color: #8080a0;
        }
        QToolTip { color: #e0e0e0; background-color: #16213e; border: 1px solid #0f3460; }
    """)


# ── Main window ───────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Logger Speed — ELLIPS-D Field Monitor")
        self.resize(1150, 820)

        self._controller: INSController | None = None
        self._logger = DataLogger()
        self._use_kmh: bool = False

        # Cached nav data for the logger (updated by _on_nav)
        self._lat: float = 0.0
        self._lon: float = 0.0
        self._alt: float = 0.0
        self._solution_status: int = 0

        # Activity counter for the RX rate display
        self._rx_count: int = 0          # incremented on every message_received
        self._rx_rate: float = 0.0       # messages/s, updated at 1 Hz

        # One-shot timer that turns the RX LED off after _RX_LED_ON_MS ms
        self._rx_off_timer = QTimer(self)
        self._rx_off_timer.setSingleShot(True)
        self._rx_off_timer.timeout.connect(self._rx_led_off)

        # 1 Hz timer for the rate display
        self._rate_timer = QTimer(self)
        self._rate_timer.setInterval(1000)
        self._rate_timer.timeout.connect(self._update_rx_rate)
        self._rate_timer.start()

        self._build_ui()
        self._connect_internal_signals()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_connection_bar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._gauge = SpeedGauge()
        self._gauge.setMinimumWidth(280)
        splitter.addWidget(self._gauge)

        right_panel = self._build_right_panel()
        right_panel.setMinimumWidth(270)
        splitter.addWidget(right_panel)
        splitter.setSizes([430, 340])

        root.addWidget(splitter, stretch=3)

        self._plot = SpeedPlot()
        self._plot.setMinimumHeight(160)
        root.addWidget(self._plot, stretch=2)

        self._log_control = LogControl()
        root.addWidget(self._log_control)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Disconnected")

        # Version + commit hash pinned to the lower-right corner
        _commit_short = COMMIT[:7] if len(COMMIT) > 7 else COMMIT
        _ver_lbl = QLabel(f"  {FULL_VERSION}  [{_commit_short}]  ")
        _ver_lbl.setFont(QFont("Courier New", 8))
        _ver_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM};")
        self._status_bar.addPermanentWidget(_ver_lbl)

        # Console dock (bottom, initially shown, user can close/float it)
        self._console = ConsolePanel()
        dock = QDockWidget("Console Log", self)
        dock.setWidget(self._console)
        dock.setObjectName("ConsoleDock")
        dock.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        self._console_dock = dock

    def _build_connection_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Port:"))
        self._port_edit = QLineEdit(DEFAULT_PORT)
        self._port_edit.setFixedWidth(80)
        layout.addWidget(self._port_edit)

        layout.addWidget(QLabel("Baud:"))
        self._baud_combo = QComboBox()
        for b in _BAUDRATES:
            self._baud_combo.addItem(str(b), b)
        self._baud_combo.setCurrentText(str(DEFAULT_BAUDRATE))
        self._baud_combo.setFixedWidth(90)
        layout.addWidget(self._baud_combo)

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setCheckable(True)
        self._connect_btn.setFixedWidth(100)
        self._connect_btn.clicked.connect(self._on_connect_toggle)
        layout.addWidget(self._connect_btn)

        # Connection status dot + label
        self._status_dot = QLabel("●")
        self._status_dot.setFont(QFont("Arial", 14))
        self._status_dot.setStyleSheet("color: #606060;")
        layout.addWidget(self._status_dot)

        self._conn_label = QLabel("Disconnected")
        self._conn_label.setStyleSheet(f"color: {COLOR_TEXT_DIM};")
        layout.addWidget(self._conn_label)

        # Separator
        sep = QLabel("  |  ")
        sep.setStyleSheet(f"color: {COLOR_TEXT_DIM};")
        layout.addWidget(sep)

        # RX activity LED + rate display
        rx_lbl = QLabel("RX")
        rx_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM}; font-weight: bold;")
        layout.addWidget(rx_lbl)

        self._rx_led = QLabel("●")
        self._rx_led.setFont(QFont("Arial", 14))
        self._rx_led.setStyleSheet("color: #303050;")    # off = very dim
        self._rx_led.setToolTip("Flashes green when SBG frames are received")
        layout.addWidget(self._rx_led)

        self._rx_rate_lbl = QLabel("0 msg/s")
        self._rx_rate_lbl.setStyleSheet(f"color: {COLOR_TEXT_DIM};")
        self._rx_rate_lbl.setFixedWidth(70)
        self._rx_rate_lbl.setToolTip("Messages received per second from the INS")
        layout.addWidget(self._rx_rate_lbl)

        layout.addStretch()

        # Console visibility toggle
        console_btn = QPushButton("Console")
        console_btn.setCheckable(True)
        console_btn.setChecked(True)
        console_btn.setFixedWidth(80)
        console_btn.clicked.connect(
            lambda checked: self._console_dock.setVisible(checked)
        )
        layout.addWidget(console_btn)

        return bar

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(8)

        # ── Target speed + gauge range controls ───────────────────────────────
        tgt_box = QGroupBox("Target Speed")
        tgt_layout = QVBoxLayout(tgt_box)
        tgt_layout.setSpacing(6)

        # Row 1: target value + unit toggle
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Target:"))
        self._target_spin = QDoubleSpinBox()
        self._target_spin.setRange(0.0, MAX_SPEED_MS)
        self._target_spin.setValue(DEFAULT_TARGET_MS)
        self._target_spin.setSingleStep(0.1)
        self._target_spin.setDecimals(2)
        self._target_spin.setSuffix("  m/s")
        self._target_spin.setFixedWidth(130)
        row1.addWidget(self._target_spin)

        self._unit_ms_btn = QPushButton("m/s")
        self._unit_ms_btn.setCheckable(True)
        self._unit_ms_btn.setChecked(True)
        self._unit_ms_btn.setFixedWidth(46)
        self._unit_kmh_btn = QPushButton("km/h")
        self._unit_kmh_btn.setCheckable(True)
        self._unit_kmh_btn.setFixedWidth(46)
        self._unit_ms_btn.clicked.connect(lambda: self._set_unit(False))
        self._unit_kmh_btn.clicked.connect(lambda: self._set_unit(True))
        row1.addWidget(self._unit_ms_btn)
        row1.addWidget(self._unit_kmh_btn)
        row1.addStretch()
        tgt_layout.addLayout(row1)

        # Row 2: margin (green zone half-width)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Zone ±:"))
        self._margin_spin = QDoubleSpinBox()
        self._margin_spin.setRange(0.0, MAX_SPEED_MS / 2.0)
        self._margin_spin.setValue(DEFAULT_MARGIN_MS)
        self._margin_spin.setSingleStep(0.1)
        self._margin_spin.setDecimals(2)
        self._margin_spin.setSuffix("  m/s")
        self._margin_spin.setFixedWidth(130)
        self._margin_spin.setToolTip(
            "Half-width of the green zone: [target − margin, target + margin]."
        )
        row2.addWidget(self._margin_spin)
        row2.addStretch()
        tgt_layout.addLayout(row2)

        # Row 3: view half (gauge display window)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("View ±:"))
        self._view_spin = QDoubleSpinBox()
        self._view_spin.setRange(0.5, MAX_SPEED_MS)
        self._view_spin.setValue(GAUGE_VIEW_HALF_MS)
        self._view_spin.setSingleStep(0.5)
        self._view_spin.setDecimals(1)
        self._view_spin.setSuffix("  m/s")
        self._view_spin.setFixedWidth(130)
        self._view_spin.setToolTip(
            "Gauge displays [target − view, target + view].\n"
            "Decrease to zoom in on the target zone."
        )
        row3.addWidget(self._view_spin)
        row3.addStretch()
        tgt_layout.addLayout(row3)

        layout.addWidget(tgt_box)

        # ── GPS + solution ────────────────────────────────────────────────────
        self._gps = GPSDisplay()
        layout.addWidget(self._gps)
        layout.addStretch()
        return panel

    # ── Internal signal wiring ────────────────────────────────────────────────

    def _connect_internal_signals(self) -> None:
        self._target_spin.valueChanged.connect(self._on_target_changed)
        self._margin_spin.valueChanged.connect(self._on_margin_changed)
        self._view_spin.valueChanged.connect(self._on_view_changed)
        self._log_control.start_requested.connect(self._on_log_start)
        self._log_control.stop_requested.connect(self._on_log_stop)
        # Push initial values
        self._on_target_changed(self._target_spin.value())
        self._on_margin_changed(self._margin_spin.value())
        self._on_view_changed(self._view_spin.value())

    def attach_log_handler(self, handler: QtLogHandler) -> None:
        """Connect the Qt log handler to the console panel."""
        handler.message_logged.connect(self._console.append_log)

    def _connect_controller_signals(self) -> None:
        assert self._controller is not None
        self._controller.speed_updated.connect(self._on_speed)
        self._controller.nav_updated.connect(self._on_nav)
        self._controller.diag_received.connect(self._on_diag)
        self._controller.message_received.connect(self._on_message_received)

    # ── Slots — user interactions ─────────────────────────────────────────────

    @pyqtSlot(bool)
    def _on_connect_toggle(self, checked: bool) -> None:
        if checked:
            self._do_connect()
        else:
            self._do_disconnect()

    def _do_connect(self) -> None:
        port = self._port_edit.text().strip()
        baudrate = int(self._baud_combo.currentData())
        _log.info("Opening %s at %d baud …", port, baudrate)
        try:
            self._controller = INSController(port, baudrate)
            self._connect_controller_signals()
            self._controller.connect()
        except Exception as exc:
            _log.error("Connection failed: %s", exc)
            QMessageBox.critical(self, "Connection failed", str(exc))
            self._connect_btn.setChecked(False)
            return

        self._connect_btn.setText("Disconnect")
        self._status_dot.setStyleSheet("color: #2dc653;")
        self._conn_label.setText(f"{port} @ {baudrate}")
        self._conn_label.setStyleSheet("color: #2dc653;")
        self._port_edit.setEnabled(False)
        self._baud_combo.setEnabled(False)
        self._status_bar.showMessage(f"Connected — {port} at {baudrate} baud")

    def _do_disconnect(self) -> None:
        if self._logger.is_active:
            self._on_log_stop()
        if self._controller is not None:
            self._controller.disconnect()
            self._controller = None

        self._connect_btn.setText("Connect")
        self._connect_btn.setChecked(False)
        self._status_dot.setStyleSheet("color: #606060;")
        self._rx_led.setStyleSheet("color: #303050;")
        self._rx_rate_lbl.setText("0 msg/s")
        self._conn_label.setText("Disconnected")
        self._conn_label.setStyleSheet(f"color: {COLOR_TEXT_DIM};")
        self._port_edit.setEnabled(True)
        self._baud_combo.setEnabled(True)
        self._status_bar.showMessage("Disconnected")

    @pyqtSlot(float)
    def _on_target_changed(self, value: float) -> None:
        target_ms = value / 3.6 if self._use_kmh else value
        _log.debug("Target speed set to %.3f m/s", target_ms)
        self._gauge.set_target(target_ms)
        self._plot.set_target(target_ms)

    @pyqtSlot(float)
    def _on_margin_changed(self, value: float) -> None:
        margin_ms = value / 3.6 if self._use_kmh else value
        self._gauge.set_margin(margin_ms)

    @pyqtSlot(float)
    def _on_view_changed(self, value: float) -> None:
        view_ms = value / 3.6 if self._use_kmh else value
        self._gauge.set_view_half(view_ms)

    def _set_unit(self, use_kmh: bool) -> None:
        self._use_kmh = use_kmh
        self._unit_ms_btn.setChecked(not use_kmh)
        self._unit_kmh_btn.setChecked(use_kmh)
        self._gauge.set_unit(use_kmh)
        self._plot.set_unit(use_kmh)

        if use_kmh:
            old_ms      = self._target_spin.value()
            old_marg_ms = self._margin_spin.value()
            old_view_ms = self._view_spin.value()
            self._target_spin.blockSignals(True)
            self._margin_spin.blockSignals(True)
            self._view_spin.blockSignals(True)
            self._target_spin.setRange(0.0, MAX_SPEED_KMH)
            self._target_spin.setSingleStep(0.5)
            self._target_spin.setSuffix("  km/h")
            self._margin_spin.setRange(0.0, MAX_SPEED_KMH / 2.0)
            self._margin_spin.setSingleStep(0.5)
            self._margin_spin.setSuffix("  km/h")
            self._view_spin.setRange(1.0, MAX_SPEED_KMH)
            self._view_spin.setSingleStep(1.0)
            self._view_spin.setSuffix("  km/h")
            self._target_spin.setValue(old_ms * 3.6)
            self._margin_spin.setValue(old_marg_ms * 3.6)
            self._view_spin.setValue(old_view_ms * 3.6)
            self._target_spin.blockSignals(False)
            self._margin_spin.blockSignals(False)
            self._view_spin.blockSignals(False)
        else:
            old_kmh      = self._target_spin.value()
            old_marg_kmh = self._margin_spin.value()
            old_view_kmh = self._view_spin.value()
            self._target_spin.blockSignals(True)
            self._margin_spin.blockSignals(True)
            self._view_spin.blockSignals(True)
            self._target_spin.setRange(0.0, MAX_SPEED_MS)
            self._target_spin.setSingleStep(0.1)
            self._target_spin.setSuffix("  m/s")
            self._margin_spin.setRange(0.0, MAX_SPEED_MS / 2.0)
            self._margin_spin.setSingleStep(0.1)
            self._margin_spin.setSuffix("  m/s")
            self._view_spin.setRange(0.5, MAX_SPEED_MS)
            self._view_spin.setSingleStep(0.5)
            self._view_spin.setSuffix("  m/s")
            self._target_spin.setValue(old_kmh / 3.6)
            self._margin_spin.setValue(old_marg_kmh / 3.6)
            self._view_spin.setValue(old_view_kmh / 3.6)
            self._target_spin.blockSignals(False)
            self._margin_spin.blockSignals(False)
            self._view_spin.blockSignals(False)

        self._on_target_changed(self._target_spin.value())
        self._on_margin_changed(self._margin_spin.value())
        self._on_view_changed(self._view_spin.value())

    # ── Slots — INS data ──────────────────────────────────────────────────────

    @pyqtSlot(float)
    def _on_speed(self, speed_ms: float) -> None:
        self._gauge.set_speed(speed_ms)
        self._plot.add_speed(speed_ms)
        if self._logger.is_active:
            self._logger.record(speed_ms,
                                self._lat, self._lon, self._alt,
                                self._solution_status)

    @pyqtSlot(float, float, float, int)
    def _on_nav(self, lat: float, lon: float, alt: float,
                solution_status: int) -> None:
        self._lat = lat
        self._lon = lon
        self._alt = alt
        self._solution_status = solution_status
        self._gps.update_position(lat, lon, alt)
        self._gps.update_solution(solution_status)

    @pyqtSlot(str, int)
    def _on_diag(self, message: str, _diag_type: int) -> None:
        self._status_bar.showMessage(f"[INS] {message}", 5000)

    # ── Slots — RX activity indicator ─────────────────────────────────────────

    @pyqtSlot()
    def _on_message_received(self) -> None:
        """Light the RX LED and increment the activity counter."""
        self._rx_count += 1
        self._rx_led.setStyleSheet("color: #2dc653;")   # bright green
        # Re-start (debounce): reset to dim after _RX_LED_ON_MS
        self._rx_off_timer.start(_RX_LED_ON_MS)

    def _rx_led_off(self) -> None:
        self._rx_led.setStyleSheet("color: #303050;")   # dim

    def _update_rx_rate(self) -> None:
        """Called every 1 s — compute and display the message rate."""
        self._rx_rate = float(self._rx_count)
        self._rx_count = 0
        if self._controller is not None:
            self._rx_rate_lbl.setText(f"{self._rx_rate:.0f} msg/s")
        else:
            self._rx_rate_lbl.setText("0 msg/s")

    # ── Slots — logging ───────────────────────────────────────────────────────

    @pyqtSlot(str)
    def _on_log_start(self, name: str) -> None:
        try:
            path = self._logger.start(name)
        except OSError as exc:
            _log.error("Cannot start log: %s", exc)
            QMessageBox.critical(self, "Cannot start log", str(exc))
            self._log_control.set_active(False)
            return
        _log.info("Logging started → %s", path)
        self._log_control.set_active(True, path)
        self._status_bar.showMessage(f"Logging → {path}")

    @pyqtSlot()
    def _on_log_stop(self) -> None:
        path = self._logger.stop() or ""
        _log.info("Logging stopped → %s", path)
        self._log_control.set_active(False, path)
        self._status_bar.showMessage(
            f"Log saved: {path}" if path else "Logging stopped", 4000
        )

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # windowHandle() is only valid after the native window is created,
        # which happens just before showEvent fires — schedule via the event
        # loop to be safe.
        QTimer.singleShot(0, self._setup_screen_tracking)

    def _setup_screen_tracking(self) -> None:
        """Connect to screenChanged and do an initial refresh.

        Called once after the window is first shown.  The screenChanged signal
        fires whenever the window moves to a monitor with a different DPI scale,
        letting us recalculate pyqtgraph's viewport each time.
        """
        handle = self.windowHandle()
        if handle:
            handle.screenChanged.connect(self._on_screen_changed)
        # Force an initial refresh: on the primary (lower-DPI) screen the
        # ViewBox may not have computed its geometry correctly on first paint.
        self._bump_resize()

    def _on_screen_changed(self, _screen) -> None:
        """Fired when the window moves to a monitor with a different DPI."""
        # Give Qt a moment to finish updating the window geometry for the
        # new screen before we trigger the resize.
        QTimer.singleShot(80, self._bump_resize)

    def _bump_resize(self) -> None:
        """Force a genuine QResizeEvent through the full widget tree.

        pyqtgraph's ViewBox calculates its grid geometry lazily from the
        widget's device-pixel size.  When the window moves between monitors
        with different DPI scales the cached size becomes stale.  A 1-pixel
        resize + restore sends a real QResizeEvent to every child widget,
        causing the ViewBox to recompute its viewport correctly.
        """
        s = self.size()
        self.resize(s.width(), s.height() + 1)
        QTimer.singleShot(0, lambda: self.resize(s))

    def closeEvent(self, event) -> None:  # noqa: N802
        _log.info("Application closing.")
        self._do_disconnect()
        event.accept()


# ── CLI argument parsing ──────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.main",
        description="Logger Speed — ELLIPS-D field monitoring application.",
    )
    parser.add_argument(
        "--verbose", "-v",
        choices=["FATAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE"],
        default="INFO",
        metavar="LEVEL",
        help=(
            "Logging verbosity.  One of: FATAL ERROR WARNING INFO DEBUG TRACE  "
            "(default: INFO).  TRACE logs every received SBG frame."
        ),
    )
    return parser.parse_args()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    qt_handler = _setup_logging(args.verbose)

    # Must be set BEFORE QApplication is instantiated.
    # Tells Qt to query each screen's DPI independently (per-monitor DPI
    # awareness) so widgets are sized correctly on every monitor from the start.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Logger Speed")
    app.setApplicationVersion("1.0.0")
    _apply_dark_palette(app)

    window = MainWindow()
    window.attach_log_handler(qt_handler)   # wire log → console panel

    _log.info(
        "Logger Speed started  (verbose=%s, default_baud=%d)",
        args.verbose, DEFAULT_BAUDRATE,
    )
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
