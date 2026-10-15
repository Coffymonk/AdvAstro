# Replaces PyInstaller's stock astropy hook.
#
# The stock hook imports every astropy submodule, which fails in a clean build
# environment (astropy.visualization needs matplotlib). This version bundles
# all of astropy except its test suites and plotting code, and skips modules
# whose optional dependencies are missing instead of failing the build.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

_SKIP = (".tests", "visualization", "conftest")


def _wanted(name: str) -> bool:
    return not any(part in name for part in _SKIP)


hiddenimports = collect_submodules("astropy", filter=_wanted, on_error="ignore")
# astropy/__init__.py imports its test runner at startup (it does not need pytest).
hiddenimports += ["astropy.tests", "astropy.tests.runner"]

# include_py_files: astropy reads some .py files as data at runtime
# (for example the unit parser tables in astropy/units/format/*_parsetab.py).
datas = collect_data_files("astropy", include_py_files=True,
                           excludes=["**/tests/**", "visualization/**"])
datas += copy_metadata("astropy")
