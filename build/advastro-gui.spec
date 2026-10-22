# PyInstaller recipe for the Advanced Astrophoto Analyzer desktop app.
# Used by build/build.py; run that script rather than this file directly.
#
# Built as a folder (not a single file) so the app starts quickly: a one-file
# Qt app would unpack ~150 MB to a temporary folder on every start.
# -*- mode: python -*-

import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH)))  # noqa: F821
from specutil import clean_metadata  # noqa: E402
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent  # noqa: F821  (SPECPATH is set by PyInstaller)
ICONS = ROOT / "build" / "icons"

_METADATA = ["advastro-analyzer", "numpy", "scipy", "astropy", "photutils", "pyerfa",
             "astropy-iers-data", "packaging", "PyYAML",
             "tifffile", "imagecodecs", "pillow"]
datas = collect_data_files("advastro")
datas += clean_metadata(_METADATA)  # without direct_url.json (local paths)

# Qt modules the app does not use; leaving them out saves a lot of space.
_QT_UNUSED = ["QtWebEngineCore", "QtWebEngineWidgets", "QtWebEngineQuick", "QtWebChannel",
              "QtQuick", "QtQuick3D", "QtQml", "Qt3DCore", "Qt3DRender", "QtCharts",
              "QtDataVisualization", "QtMultimedia", "QtMultimediaWidgets", "QtPdf",
              "QtPdfWidgets", "QtSql", "QtTest", "QtBluetooth", "QtNfc", "QtPositioning",
              "QtLocation", "QtSensors", "QtSerialPort", "QtRemoteObjects", "QtScxml",
              "QtTextToSpeech", "QtDesigner", "QtUiTools", "QtHelp", "QtOpenGLWidgets",
              "QtNetworkAuth", "QtSpatialAudio", "QtHttpServer", "QtWebSockets"]

a = Analysis(  # noqa: F821
    [str(ROOT / "build" / "entry_gui.py")],
    pathex=[str(ROOT / "src")],
    datas=datas,
    hiddenimports=["advastro.i18n", *collect_submodules("imagecodecs")],
    hookspath=[str(ROOT / "build" / "hooks")],
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "astropy.visualization",
              *[f"PySide6.{m}" for m in _QT_UNUSED]],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821

icon = str(ICONS / ("advastro.icns" if sys.platform == "darwin" else "advastro.ico"))
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Advanced Astrophoto Analyzer",
    console=False,          # no terminal window behind the app
    icon=icon,
    upx=False,
    strip=False,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    upx=False,
    strip=False,
    name="Advanced Astrophoto Analyzer",
)

if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821
        coll,
        name="Advanced Astrophoto Analyzer.app",
        icon=icon,
        bundle_identifier="se.miklosoft.advastro",
        info_plist={
            "CFBundleShortVersionString": "1.0.0",
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": False,
            "LSMinimumSystemVersion": "12.0",
        },
    )
