# PyInstaller recipe for the Advanced Astrophoto Analyzer command-line executable.
# Used by build/build.py; run that script rather than this file directly.
# -*- mode: python -*-

import sys
from pathlib import Path

sys.path.insert(0, str(Path(SPECPATH)))  # noqa: F821
from specutil import clean_metadata  # noqa: E402
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).parent  # noqa: F821  (SPECPATH is set by PyInstaller)

# astropy and photutils check the installed versions of their dependencies at
# runtime, so the package metadata must travel with the executable.
_METADATA = ["advastro-analyzer", "numpy", "scipy", "astropy", "photutils", "pyerfa",
             "astropy-iers-data", "packaging", "PyYAML",
             "tifffile", "imagecodecs", "pillow"]
datas = collect_data_files("advastro")  # defaults.toml and translations
datas += clean_metadata(_METADATA)  # without direct_url.json (local paths)

a = Analysis(  # noqa: F821
    [str(ROOT / "build" / "entry_cli.py")],
    pathex=[str(ROOT / "src")],
    datas=datas,
    hiddenimports=["advastro.i18n", *collect_submodules("imagecodecs")],
    hookspath=[str(ROOT / "build" / "hooks")],  # our astropy hook wins over the stock one
    excludes=["tkinter", "matplotlib", "PySide6", "IPython", "pytest",
              "astropy.visualization"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="advastro",
    console=True,
    upx=False,
    strip=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
