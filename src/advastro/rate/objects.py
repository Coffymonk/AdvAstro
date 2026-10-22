"""What kind of picture is being rated: the object type, and whether it is starless.

A galaxy, a frame-filling nebula, a star cluster and a Milky Way field are judged
differently. A galaxy's colours are subtle and its background must be flat; a nebula
may fill the frame, so a "gradient" can be the nebula itself; in a cluster the stars
are the subject; a wide Milky Way field is supposed to be full of stars.

The type comes, in order of trust, from the user's choice, the plate solve, the object
name (typed or in the file header), or is left as "unknown" (generic rules).
"""

from __future__ import annotations

from dataclasses import dataclass

KINDS = ("galaxy", "emission", "reflection", "planetary", "dark", "cluster", "globular",
         "milkyway")
CHOICES = ("auto",) + KINDS            # what the user can pick
NAMES = {
    "auto": "Automatic", "unknown": "Not known", "galaxy": "Galaxy",
    "emission": "Emission nebula", "reflection": "Reflection nebula",
    "planetary": "Planetary nebula", "dark": "Dark nebula", "cluster": "Open cluster",
    "globular": "Globular cluster", "milkyway": "Milky Way / wide field",
}

# "a galaxy", "an emission nebula": for sentences.
WITH_ARTICLE = {
    "galaxy": "a galaxy", "emission": "an emission nebula", "reflection": "a reflection nebula",
    "planetary": "a planetary nebula", "dark": "a dark nebula", "cluster": "an open cluster",
    "globular": "a globular cluster", "milkyway": "a Milky Way field", "unknown": "your target",
}

# Category weights per kind (the generic weights live in judge.WEIGHTS).
WEIGHTS = {
    "galaxy": {"stars": 0.18, "background": 0.22, "colour": 0.13, "detail": 0.19,
               "tonality": 0.15, "presentation": 0.08, "depth": 0.05},
    "emission": {"stars": 0.16, "background": 0.16, "colour": 0.18, "detail": 0.18,
                 "tonality": 0.18, "presentation": 0.08, "depth": 0.06},
    "reflection": {"stars": 0.17, "background": 0.18, "colour": 0.18, "detail": 0.16,
                   "tonality": 0.17, "presentation": 0.08, "depth": 0.06},
    "planetary": {"stars": 0.18, "background": 0.20, "colour": 0.16, "detail": 0.18,
                  "tonality": 0.16, "presentation": 0.08, "depth": 0.04},
    "dark": {"stars": 0.18, "background": 0.16, "colour": 0.14, "detail": 0.16,
             "tonality": 0.20, "presentation": 0.08, "depth": 0.08},
    "cluster": {"stars": 0.36, "background": 0.18, "colour": 0.18, "detail": 0.04,
                "tonality": 0.11, "presentation": 0.08, "depth": 0.05},
    "globular": {"stars": 0.34, "background": 0.18, "colour": 0.14, "detail": 0.08,
                 "tonality": 0.15, "presentation": 0.08, "depth": 0.03},
    "milkyway": {"stars": 0.18, "background": 0.18, "colour": 0.18, "detail": 0.14,
                 "tonality": 0.18, "presentation": 0.08, "depth": 0.06},
}


@dataclass
class PictureContext:
    kind: str = "unknown"              # one of KINDS, or "unknown"
    kind_source: str = "none"          # manual | solve | name | header | none
    name: str | None = None            # object label, when known
    starless: bool = False
    starless_source: str = "auto"      # auto | manual
    fills_frame: bool = False          # the object covers most of the frame
    object_xy: tuple[float, float] | None = None    # 0–1 position, when solved
    object_size: float | None = None   # object diameter as a share of the frame width
    object_arcmin: float | None = None  # catalogue size, when known

    @property
    def label(self) -> str:
        return NAMES.get(self.kind, self.kind)

    @property
    def nebula(self) -> bool:
        return self.kind in ("emission", "reflection", "dark", "milkyway")

    @property
    def star_subject(self) -> bool:
        return self.kind in ("cluster", "globular")

    @property
    def small_object(self) -> bool:
        """A compact object (most galaxies, planetaries) in a larger field."""
        if self.object_size is not None:
            return self.object_size < 0.35
        return self.kind in ("galaxy", "planetary")


def looks_starless(m) -> bool:
    """True when the picture has (almost) no real stars: a starless layer or render.

    Real star fields have dozens to hundreds of small, round, bright point sources per
    megapixel; what star removal leaves behind is large, faint or both. Trailed stars
    are not compact either, but they stay bright, so they do not count as starless.
    """
    mp = max(m.width * m.height / 1e6, 0.1)
    if m.star_count < 15:
        return True
    return m.compact_density < 5.0 and m.bright_sources / mp < 10.0


def _from_object(obj, milky_way: bool, field_w: float | None) -> str:
    family = getattr(obj, "family", "unknown")
    kind = {"galaxy": "galaxy", "emission": "emission", "reflection": "reflection",
            "planetary": "planetary", "cluster": "cluster", "globular": "globular"}.get(
        family, "unknown")
    if getattr(obj, "type", "") == "DrkN":
        kind = "dark"
    if milky_way and field_w is not None and field_w > 4 and kind in ("emission", "cluster",
                                                                       "unknown"):
        kind = "milkyway"
    return kind


def picture_context(m, pic, sky=None, choice: str = "auto", starless: str = "auto",
                    typed_name: str | None = None) -> PictureContext:
    """Work out the object type and whether the picture is starless.

    choice: "auto" or one of KINDS. starless: "auto", "yes" or "no".
    """
    ctx = PictureContext()
    field_w = None
    report = getattr(sky, "target", None) if sky is not None else None
    target = getattr(report, "target", None)
    if sky is not None and getattr(sky, "field", None) is not None:
        field_w = sky.field.width_deg
    if target is not None:
        ctx.name = target.label
        ctx.kind = _from_object(target, bool(getattr(report, "milky_way", False)), field_w)
        ctx.kind_source = "solve"
        ctx.object_xy = getattr(sky, "target_xy", None)
        ctx.object_arcmin = target.major_arcmin
        if target.major_arcmin and field_w:
            ctx.object_size = float(target.major_arcmin / 60.0 / field_w)
    else:
        from advastro.sky.catalog import load

        for source, name in (("name", typed_name), ("header", getattr(pic, "object_name", None))):
            obj = load().by_name(name) if name else None
            if obj is not None:
                ctx.name, ctx.kind, ctx.kind_source = obj.label, _from_object(obj, False, None), \
                    source
                ctx.object_arcmin = obj.major_arcmin
                break
    if field_w is not None and field_w > 10 and ctx.kind in ("unknown", "emission", "cluster"):
        ctx.kind, ctx.kind_source = "milkyway", "solve"
    if choice in KINDS:
        ctx.kind, ctx.kind_source = choice, "manual"

    if starless in ("yes", "no"):
        ctx.starless, ctx.starless_source = starless == "yes", "manual"
    else:
        ctx.starless = looks_starless(m)

    if ctx.object_size is not None:
        ctx.fills_frame = ctx.object_size > 0.7
    elif ctx.object_arcmin and ctx.object_arcmin >= 60 and ctx.kind in (
            "emission", "reflection", "dark"):
        ctx.fills_frame = True      # a degree or more: larger than most fields of view
    else:
        ctx.fills_frame = m.signal_fraction > 0.3 or m.background_fraction < 0.2
    if ctx.kind == "milkyway":
        ctx.fills_frame = True
    return ctx
