"""What did you image? Combines the field position with the catalog and name hints."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from advastro.i18n import tr
from advastro.sky.catalog import SkyObject, load
from advastro.sky.solve import SkyField

# How sure we are about the target, best first.
CONFIDENCE = ("solved", "pointing", "name", "none")


@dataclass
class TargetReport:
    target: SkyObject | None
    confidence: str                       # one of CONFIDENCE
    source: str                           # e.g. "plate solved (ASTAP)", "OBJECT keyword"
    sky: SkyField | None = None
    others: list[SkyObject] = field(default_factory=list)
    constellation: str | None = None
    galactic_latitude: float | None = None

    @property
    def family(self) -> str:
        return self.target.family if self.target else "unknown"

    @property
    def coverage(self) -> float | None:
        """Target size as a share of the field's long side (1.0 = edge to edge)."""
        if not (self.target and self.sky and self.target.major_arcmin):
            return None
        return self.target.major_arcmin / (max(self.sky.width_deg, self.sky.height_deg) * 60)

    @property
    def framing(self) -> str | None:
        c = self.coverage
        if c is None:
            return None
        if c > 1.1:
            return "larger_than_field"
        if c > 0.6:
            return "fills_field"
        if c > 0.2:
            return "well_framed"
        if c > 0.06:
            return "small"
        return "tiny"

    @property
    def milky_way(self) -> bool:
        return self.galactic_latitude is not None and abs(self.galactic_latitude) < 10


def _prominence(obj: SkyObject, sky: SkyField, sep_deg: float) -> float:
    """Rank candidates: big, bright and central objects first."""
    size = (obj.major_arcmin or 0.5) / 60
    long_side = max(sky.width_deg, sky.height_deg)
    size_score = min(size / long_side, 1.0)
    central = 1.0 - min(sep_deg / max(sky.radius_deg, 1e-6), 1.0)
    bright = 0.0 if obj.magnitude is None else max(0.0, (14 - obj.magnitude) / 14)
    named = 0.15 if (obj.names or obj.messier) else 0.0
    return 3.0 * size_score + 1.2 * central + 0.8 * bright + named


def _sky_facts(ra: float, dec: float) -> tuple[str | None, float | None]:
    try:
        from astropy import units as u
        from astropy.coordinates import SkyCoord, get_constellation

        c = SkyCoord(ra * u.deg, dec * u.deg)
        return get_constellation(c), float(c.galactic.b.deg)
    except Exception:
        return None, None


def identify(sky: SkyField | None, name_hints: list[str] | None = None,
             extra: list[SkyObject] | None = None) -> TargetReport:
    """Identify the main target and other catalogued objects in the frame.

    name_hints: names from the OBJECT keyword, folder name, session file, in order.
    extra: user objects (e.g. from .mktargets) checked before the catalog.
    """
    catalog = load()
    hinted: SkyObject | None = None
    hint_source = ""
    for hint in name_hints or []:
        for obj in extra or []:
            if hint and any(hint.strip().casefold() == n.casefold()
                            for n in [obj.id, *obj.aliases, *obj.names]):
                hinted, hint_source = obj, hint
                break
        hinted = hinted or catalog.by_name(hint)
        if hinted:
            hint_source = hint_source or hint
            break

    if sky is None:
        if hinted:
            const, b = _sky_facts(hinted.ra, hinted.dec)
            return TargetReport(hinted, "name", tr("sky.src.name", name=hint_source), None, [], const, b)
        return TargetReport(None, "none", "no position or name")

    margin = 0.0 if sky.level == "solved" else 0.15 * min(sky.width_deg, sky.height_deg)
    candidates = []
    for obj, sep in catalog.cone(sky.ra, sky.dec, sky.radius_deg * 1.5 + 2.5):
        reach = (obj.major_arcmin or 0) / 120  # an object's half size, in degrees
        if sky.contains(obj.ra, obj.dec, margin=margin + reach):
            candidates.append((obj, sep))
    for obj in extra or []:
        if sky.contains(obj.ra, obj.dec, margin=margin) and all(
                obj.id != c.id for c, _ in candidates):
            sep = math.degrees(math.acos(max(-1.0, min(1.0,
                  math.sin(math.radians(obj.dec)) * math.sin(math.radians(sky.dec)) +
                  math.cos(math.radians(obj.dec)) * math.cos(math.radians(sky.dec)) *
                  math.cos(math.radians(obj.ra - sky.ra))))))
            candidates.append((obj, sep))

    ranked = sorted(candidates, key=lambda t: _prominence(t[0], sky, t[1]), reverse=True)
    target = ranked[0][0] if ranked else None
    if hinted and any(hinted.id == o.id for o, _ in candidates):
        target = hinted  # the name and the position agree
    elif hinted and target is None:
        target = hinted
    others = [o for o, _ in ranked if target is None or o.id != target.id][:12]
    const, b = _sky_facts(sky.ra, sky.dec)
    source = sky.source if sky.level == "solved" else tr("sky.src.pointing")
    return TargetReport(target, sky.level, source, sky, others, const, b)
