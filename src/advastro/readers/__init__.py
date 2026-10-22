"""File readers. Each format registers its extensions here.

To add a format (XISF, raw), write a module with a `read(path) -> Frame`
function and add its extensions to READERS. Nothing else needs to change.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from advastro.frame import Frame
from advastro.i18n import tr
from advastro.readers import fits, xisf

READERS: dict[str, Callable[[Path], Frame]] = {
    ".fits": fits.read,
    ".fit": fits.read,
    ".fts": fits.read,
    ".xisf": xisf.read,
}


class UnsupportedFormatError(ValueError):
    pass


def supported_extensions() -> set[str]:
    return set(READERS)


def read_frame(path: str | Path) -> Frame:
    path = Path(path)
    reader = READERS.get(path.suffix.lower())
    if reader is None:
        raise UnsupportedFormatError(tr("read.err.type", ext=path.suffix, name=path.name))
    return reader(path)


def find_frames(folder: str | Path, recursive: bool = False) -> list[Path]:
    """All supported image files in a folder, sorted by name."""
    folder = Path(folder)
    pattern: Iterable[Path] = folder.rglob("*") if recursive else folder.iterdir()
    return sorted(p for p in pattern if p.is_file() and p.suffix.lower() in READERS)
