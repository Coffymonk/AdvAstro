"""Read .mksession (Miklosoft session logger) and .mktargets (target planner).

Read-only for now. Write-back will go into a top-level "advastro" block only;
fields owned by the session app are never changed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from advastro.frame import ARCSEC_PER_RADIAN
from advastro.i18n import tr


@dataclass
class Gear:
    scope: str | None = None
    focal_length_mm: float | None = None
    aperture_mm: float | None = None
    camera: str | None = None
    pixel_size_um: float | None = None
    width_px: int | None = None
    height_px: int | None = None
    colour: bool | None = None
    filters: dict[str, bool] = field(default_factory=dict)

    @property
    def pixel_scale_arcsec(self) -> float | None:
        if not self.pixel_size_um or not self.focal_length_mm:
            return None
        return ARCSEC_PER_RADIAN * self.pixel_size_um * 1e-3 / self.focal_length_mm

    @property
    def field_arcmin(self) -> tuple[float, float] | None:
        scale = self.pixel_scale_arcsec
        if not scale or not self.width_px or not self.height_px:
            return None
        return self.width_px * scale / 60, self.height_px * scale / 60


@dataclass
class Target:
    id: str
    name: str | None
    ra_deg: float | None
    dec_deg: float | None
    type: str | None
    size_arcmin: float | None
    aliases: list[str] = field(default_factory=list)


@dataclass
class LogEntry:
    type: str  # lights | cal
    kind: str | None  # flat, dark, bias, darkflat for cal entries
    target: str | None
    filter: str | None
    exposure_s: float | None
    count: int | None
    gain: float | None
    temperature_c: float | None
    warnings: list[str] = field(default_factory=list)


@dataclass
class MkSession:
    path: Path
    date: str | None
    place: dict
    gear: Gear
    bortle: int | None
    targets: list[Target]
    entries: list[LogEntry]


def _gear(d: dict) -> Gear:
    return Gear(
        scope=d.get("scope"), focal_length_mm=d.get("focal"), aperture_mm=d.get("aperture"),
        camera=d.get("camera"), pixel_size_um=d.get("pixel"), width_px=d.get("width"),
        height_px=d.get("height"), colour=d.get("colour"), filters=d.get("filters") or {},
    )


def _target(d: dict) -> Target:
    return Target(
        id=d.get("id", ""), name=d.get("name"), ra_deg=d.get("ra"), dec_deg=d.get("dec"),
        type=d.get("type"), size_arcmin=d.get("size"), aliases=list(d.get("ids") or []),
    )


def _entry(d: dict) -> LogEntry:
    e = LogEntry(
        type=d.get("type", ""), kind=d.get("kind"), target=d.get("target"),
        filter=d.get("filter"), exposure_s=d.get("sub"), count=d.get("count"),
        gain=d.get("gain"), temperature_c=d.get("temp"),
    )
    if e.type == "cal" and e.kind == "flat" and e.exposure_s is not None:
        # Known session-app bug: the gain is stored in 'sub' for cal entries.
        if e.exposure_s > 30 or (e.gain is not None and e.exposure_s == e.gain):
            e.warnings.append(
                tr("cli.flat_exposure", s=e.exposure_s))
            e.exposure_s = None
    return e


def load_mksession(path: str | Path) -> MkSession:
    path = Path(path)
    data = json.loads(path.read_text("utf-8"))
    if data.get("app") != "miklosoft-session":
        raise ValueError(f"{path.name} is not a Miklosoft session file")
    log = data.get("log") or {}
    return MkSession(
        path=path, date=data.get("date"), place=data.get("place") or {},
        gear=_gear(data.get("gear") or {}),
        bortle=data.get("bortle") if data.get("bortle") is not None
        else (data.get("gear") or {}).get("bortle"),
        targets=[_target(t) for t in data.get("targets") or []],
        entries=[_entry(e) for e in log.get("entries") or []],
    )


def load_mktargets(path: str | Path) -> tuple[list[Target], Gear]:
    path = Path(path)
    data = json.loads(path.read_text("utf-8"))
    if data.get("app") != "miklosoft-targets":
        raise ValueError(f"{path.name} is not a Miklosoft targets file")
    return [_target(t) for t in data.get("targets") or []], _gear(data.get("gear") or {})


def find_mksession(folder: Path) -> Path | None:
    """The session file in a folder or its parent, if there is exactly one."""
    for place in (folder, folder.parent):
        found = sorted(place.glob("*.mksession"))
        if len(found) == 1:
            return found[0]
    return None
