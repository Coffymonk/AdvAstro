# PyInstaller hook for photutils.
# photutils reads its own package metadata at import time and ships data files,
# so both must be bundled; its test suites are left out.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

hiddenimports = collect_submodules(
    "photutils", filter=lambda name: ".tests" not in name, on_error="ignore")
datas = collect_data_files("photutils", excludes=["**/tests/**"])
datas += copy_metadata("photutils")

# Compiled photutils extensions import these scipy modules from C code,
# which PyInstaller cannot see by scanning Python imports.
hiddenimports += collect_submodules("scipy.optimize.cython_optimize")
hiddenimports += ["scipy.special.cython_special", "scipy.ndimage", "scipy.spatial"]
