# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — produces a single LoggerSpeed.exe.

Build::

    .venv\\Scripts\\pyinstaller.exe --clean logger_speed.spec

The resulting exe is written to dist\\LoggerSpeed.exe.
No installation or admin rights are required to run it.
When launched, it creates a  log\\  folder next to the .exe.

To add an icon, set the  icon=  argument in EXE() to the path of a
.ico file, e.g.  icon='assets\\icon.ico'.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

# ── Collect entire pyqtgraph package (templates, resources, …) ────────────────
pg_datas, pg_binaries, pg_hidden = collect_all("pyqtgraph")

# ── Collect numpy (binary extensions vary by platform) ───────────────────────
np_datas, np_binaries, np_hidden = collect_all("numpy")

# ── sbg_ellipsd subpackages (installed as editable — collect explicitly) ──────
sbg_hidden = collect_submodules("sbg_ellipsd")

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=[*pg_binaries, *np_binaries],
    datas=[*pg_datas, *np_datas],
    hiddenimports=[
        # PyQt5
        "PyQt5.sip",
        "PyQt5.QtPrintSupport",   # required by some pyqtgraph code paths
        # pyqtgraph
        *pg_hidden,
        # numpy
        *np_hidden,
        # pyserial Windows backends
        "serial.serialutil",
        "serial.win32",
        "serial.serialposix",     # kept for cross-platform builds
        # sbg_ellipsd
        *sbg_hidden,
    ],
    hookspath=[],
    hooksconfig={
        # Tell PyInstaller which Qt modules the app actually uses
        # (reduces bundle size by skipping unused Qt modules)
        "PyQt5": {
            "excluded_qml_files": ["*"],
        }
    },
    runtime_hooks=[],
    excludes=[
        # Keep this list minimal: pyqtgraph pulls in a surprisingly large
        # portion of the standard library (pydoc, html, multiprocessing, …).
        # Only exclude what is demonstrably unreachable by the whole tree.
        "tkinter",   # we use PyQt5, not tkinter
        "sqlite3",   # no database usage anywhere in the app
    ],
    noarchive=False,
    optimize=1,   # remove docstrings to reduce .pyc size
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,     # ← include binaries inside the exe (--onefile)
    a.zipfiles,
    a.datas,
    [],
    name="LoggerSpeed",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,       # compress with UPX if available (reduces size ~30 %)
    upx_exclude=[
        # Qt DLLs often break when UPX-compressed
        "Qt5Core.dll", "Qt5Gui.dll", "Qt5Widgets.dll",
        "qwindows.dll",
    ],
    runtime_tmpdir=None,
    console=False,          # no black console window; GUI only
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # set to 'assets/icon.ico' to add a custom icon
)
