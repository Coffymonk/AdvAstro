"""Helpers shared by the two PyInstaller spec files."""

from __future__ import annotations

import shutil
from importlib import metadata
from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "build" / "work" / "metadata"
PRIVATE = ("direct_url.json",)  # pip writes the local source folder (with the user name) here


def clean_metadata(names: list[str]) -> list[tuple[str, str]]:
    """Package metadata for the bundle, without files that reveal the build machine's paths."""
    datas = []
    for name in names:
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:   # an optional dependency that is not installed
            continue
        src = Path(getattr(dist, "_path", ""))
        if not src.is_dir() or not any((src / p).exists() for p in PRIVATE):
            datas += copy_metadata(name)
            continue
        dest = CLEAN / src.name
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*PRIVATE))
        datas.append((str(dest), src.name))
    return datas
