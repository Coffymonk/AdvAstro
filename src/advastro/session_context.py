"""Everything around the lights: calibration frames, session files, the user's targets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from advastro.integrations.miklosoft import MkSession, find_mksession, load_mksession

_CAL_DIRS = {
    "darks": re.compile(r"^(darks?|dark[ _-]?frames?)$", re.I),
    "flats": re.compile(r"^(flats?|flat[ _-]?frames?)$", re.I),
    "bias": re.compile(r"^(bias(es)?|offsets?)$", re.I),
    "darkflats": re.compile(r"^(flat[ _-]?darks?|dark[ _-]?flats?)$", re.I),
}
_MASTER = {
    "darks": re.compile(r"master[ _-]?dark(?![ _-]?flat)", re.I),
    "flats": re.compile(r"master[ _-]?flat", re.I),
    "bias": re.compile(r"master[ _-]?bias", re.I),
    "darkflats": re.compile(r"master[ _-]?(flat[ _-]?dark|dark[ _-]?flat)", re.I),
}
_IMAGE = {".fit", ".fits", ".fts", ".xisf"}


@dataclass
class Calibration:
    counts: dict[str, int] = field(default_factory=dict)   # frames found per kind
    masters: dict[str, Path] = field(default_factory=dict)
    files: dict[str, list[Path]] = field(default_factory=dict)  # frames and masters per kind

    def all_files(self) -> dict[str, list[Path]]:
        out = {k: list(v) for k, v in self.files.items()}
        for kind, master in self.masters.items():
            if master not in out.setdefault(kind, []):
                out[kind].append(master)
        return out

    def has(self, kind: str) -> bool:
        return self.counts.get(kind, 0) > 0 or kind in self.masters


@dataclass
class SessionContext:
    root: Path
    calibration: Calibration
    mksession: MkSession | None = None
    name_hints: list[str] = field(default_factory=list)


def _images(folder: Path) -> list[Path]:
    return [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in _IMAGE]


def find_calibration(root: Path) -> Calibration:
    cal = Calibration()
    if not root.is_dir():
        return cal
    for child in root.iterdir():
        if not child.is_dir():
            continue
        for kind, pattern in _CAL_DIRS.items():
            if pattern.match(child.name):
                images = sorted(_images(child))
                cal.counts[kind] = cal.counts.get(kind, 0) + len(images)
                cal.files.setdefault(kind, []).extend(images)
    for master_dir in [root, *(p for p in root.rglob("*") if p.is_dir()
                               and p.name.lower() in ("master", "masters"))]:
        for f in _images(master_dir):
            for kind in ("darkflats", "darks", "flats", "bias"):
                if _MASTER[kind].search(f.name):
                    cal.masters.setdefault(kind, f)
                    break
    return cal


def session_root(frames_dir: Path) -> Path:
    """The session folder: the parent when the lights live in a LIGHT subfolder."""
    if frames_dir.name.lower() in ("light", "lights", "lightframes", "light frames"):
        return frames_dir.parent
    return frames_dir


def build_context(frames_dir: Path, object_name: str | None = None) -> SessionContext:
    root = session_root(frames_dir)
    mk_path = find_mksession(frames_dir) or find_mksession(root)
    mk = None
    if mk_path:
        try:
            mk = load_mksession(mk_path)
        except (ValueError, OSError):
            mk = None
    hints = [h for h in (object_name, *(t.id for t in (mk.targets if mk else [])),
                         root.name) if h]
    cal = find_calibration(root)
    if mk:  # logged calibration counts when the frames themselves are elsewhere
        for e in mk.entries:
            if e.type == "cal" and e.kind and e.count:
                kind = {"flat": "flats", "dark": "darks", "bias": "bias",
                        "darkflat": "darkflats", "flatdark": "darkflats"}.get(e.kind)
                if kind and not cal.has(kind):
                    cal.counts[kind] = e.count
    return SessionContext(root, cal, mk, hints)


def folder_kind(frames: list[Path]) -> str:
    """'lights', or the calibration kind when a folder holds only calibration frames.

    The folder name wins (ASIAIR labels flat darks 'Flat'); otherwise the header of
    the first frame decides.
    """
    if not frames:
        return "lights"
    folder = frames[0].parent.name
    for kind, pattern in _CAL_DIRS.items():
        if pattern.match(folder):
            return kind
    from advastro.readers import read_frame

    try:
        image_type = read_frame(frames[0]).meta.image_type
    except Exception:
        return "lights"
    return {"dark": "darks", "flat": "flats", "bias": "bias",
            "darkflat": "darkflats"}.get(image_type or "", "lights")
