"""In-application console panel — coloured, scrolling log output.

A :class:`QtLogHandler` is a standard :class:`logging.Handler` that re-emits
each log record as a Qt signal.  Wire it to :meth:`ConsolePanel.append_log`
after creating the main window.

Colour coding:
  TRACE   dark gray   — very verbose internal events
  DEBUG   medium gray — debug detail
  INFO    white       — normal operational messages
  WARNING amber       — non-fatal anomalies
  ERROR   red         — recoverable errors
  FATAL   bright red  — critical / unrecoverable
"""

from __future__ import annotations

import html
import logging

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor
from PyQt5.QtWidgets import (QHBoxLayout, QPushButton,
                               QTextEdit, QVBoxLayout, QWidget)

# Custom TRACE level sits below DEBUG
TRACE: int = 5
logging.addLevelName(TRACE, "TRACE")

_LEVEL_COLORS: dict[int, str] = {
    TRACE:             "#404055",   # very dark gray
    logging.DEBUG:     "#707090",   # medium gray
    logging.INFO:      "#d0d0e0",   # near-white
    logging.WARNING:   "#ffb703",   # amber
    logging.ERROR:     "#e63946",   # red
    logging.CRITICAL:  "#ff4040",   # bright red (FATAL)
}


def level_color(levelno: int) -> str:
    """Return the HTML colour string for a given logging level number."""
    for lvl in sorted(_LEVEL_COLORS, reverse=True):
        if levelno >= lvl:
            return _LEVEL_COLORS[lvl]
    return "#d0d0e0"


# ── Qt-aware logging handler ─────────────────────────────────────────────────

class QtLogHandler(logging.Handler, QObject):
    """Logging handler that forwards records to the Qt event loop via a signal.

    Thread-safe: ``emit()`` can be called from any thread; the signal delivery
    is queued to the main thread automatically by PyQt5.
    """

    message_logged = pyqtSignal(int, str)
    """``(levelno, formatted_message)`` — connect to :meth:`ConsolePanel.append_log`."""

    def __init__(self) -> None:
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record: logging.LogRecord) -> None:  # noqa: A003
        try:
            msg = self.format(record)
            self.message_logged.emit(record.levelno, msg)
        except Exception:
            self.handleError(record)


# ── Console widget ───────────────────────────────────────────────────────────

class ConsolePanel(QWidget):
    """Read-only QTextEdit that displays coloured log lines.

    Max line count is capped to :attr:`MAX_LINES` to prevent unbounded
    memory growth during long sessions.
    """

    MAX_LINES: int = 3_000

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def append_log(self, levelno: int, message: str) -> None:
        """Append one log line with the appropriate colour.

        Must be called from the main (GUI) thread — connect to the
        :attr:`QtLogHandler.message_logged` signal directly (queued connection).
        """
        color = level_color(levelno)
        # Escape HTML entities so < > & in log messages render correctly
        escaped = html.escape(message)
        self._text.append(
            f'<span style="color:{color};white-space:pre">{escaped}</span>'
        )
        # Keep the view scrolled to the latest line
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self._text.setTextCursor(cursor)

    # ── Private ───────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        # Toolbar
        bar = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._text_clear)
        bar.addWidget(clear_btn)
        bar.addStretch()
        layout.addLayout(bar)

        # Log output area
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        mono = QFont("Courier New", 8)
        mono.setStyleHint(QFont.Monospace)
        self._text.setFont(mono)
        self._text.document().setMaximumBlockCount(self.MAX_LINES)
        layout.addWidget(self._text)

    def _text_clear(self) -> None:
        self._text.clear()
