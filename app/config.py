"""Application-wide constants.

Body frame convention (SBG ELLIPS-D, as mounted in this vehicle):
  X = forward, Y = right, Z = down
Forward speed is therefore ``LogEkfVelBody.velocity_x_ms``.
"""

# ── Speed scale ─────────────────────────────────────────────────────────────
MAX_SPEED_MS: float = 10.0
MAX_SPEED_KMH: float = 40.0     # display ceiling in km/h mode

# ── Gauge geometry ───────────────────────────────────────────────────────────
GAUGE_START_ANGLE: int = 225    # QPainter degrees (CCW from 3 o'clock), arc start (lower-left)
GAUGE_SPAN: int = 270           # degrees swept clockwise to arc end (lower-right)
GAUGE_MAJOR_TICKS: int = 10     # number of intervals between display min and max
GAUGE_MINOR_TICKS: int = 5      # minor ticks per major interval

# Gauge auto-scaling: the gauge always shows [target − view_half, target + view_half].
# Clamped to [0, MAX_SPEED_MS].  Change via the "View ±" spin-box in the UI.
GAUGE_VIEW_HALF_MS: float = 3.0

# ── Default user settings ────────────────────────────────────────────────────
DEFAULT_TARGET_MS: float = 3.0
DEFAULT_MARGIN_KMH: float = 2.0
DEFAULT_MARGIN_MS: float = DEFAULT_MARGIN_KMH / 3.6

DEFAULT_PORT: str = "COM3"
DEFAULT_BAUDRATE: int = 921_600  # matches typical ELLIPS-D factory setting

# Directory where CSV log files are stored (relative to the working directory).
# Created automatically if it does not exist.
LOG_DIR: str = "log"

# ── Real-time plot ───────────────────────────────────────────────────────────
PLOT_HISTORY_SECONDS: int = 60  # rolling time window

# ── UI refresh ───────────────────────────────────────────────────────────────
UI_REFRESH_MS: int = 100        # gauge + plot update interval (10 Hz)

# ── Colour palette (dark theme) ──────────────────────────────────────────────
COLOR_BG            = "#1a1a2e"
COLOR_PANEL         = "#16213e"
COLOR_BORDER        = "#0f3460"
COLOR_TEXT          = "#e0e0e0"
COLOR_TEXT_DIM      = "#8080a0"
COLOR_SPEED_LINE    = "#00b4d8"
COLOR_TARGET_LINE   = "#e63946"
COLOR_ZONE_GREEN    = "#2dc653"
COLOR_ZONE_YELLOW   = "#ffb703"
COLOR_ZONE_RED      = "#e63946"
COLOR_NEEDLE        = "#ff6b6b"
COLOR_GAUGE_BG      = "#2a2a4a"
COLOR_GAUGE_HUB     = "#c0c0d0"

# ── Solution mode labels and colours ─────────────────────────────────────────
SOLUTION_LABELS = {
    0: ("Uninitialized", "#606060"),
    1: ("Vertical Gyro", "#e63946"),
    2: ("AHRS",          "#ffb703"),
    3: ("INS (Velocity)", "#00b4d8"),
    4: ("INS (Position)", "#2dc653"),
}
