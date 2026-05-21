#!/usr/bin/env python3
"""Development launcher and PyInstaller entry point.

Development::

    python run.py
    python run.py --verbose DEBUG

Build::

    powershell -ExecutionPolicy Bypass -File build_exe.ps1
"""
import sys
from pathlib import Path

# Guarantee the project root is in sys.path when running from source
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.main import main

if __name__ == "__main__":
    main()
