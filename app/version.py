"""Application version information.

Values are baked in at build time by ``build_exe.ps1`` and stored in
``app/_version.py``.  That file is auto-generated -- do not edit it by hand.

When running from a fresh clone (before the first build) the fallback values
below are used so the app still starts cleanly.
"""

from __future__ import annotations

try:
    from app._version import BUILD, COMMIT, FULL_VERSION, IS_DEV, VERSION
except ImportError:
    VERSION = "0.0.0"
    BUILD = 0
    COMMIT = "unknown"
    IS_DEV = True
    FULL_VERSION = "DEV 0.0.0 (no build)"

__all__ = ["VERSION", "BUILD", "COMMIT", "IS_DEV", "FULL_VERSION"]
