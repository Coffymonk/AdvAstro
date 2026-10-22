"""Turn measurements into findings, category verdicts, an overall verdict and a plan.

Thresholds are deliberate and documented next to each rule. Technical faults are
judged strictly; matters of taste (saturation, background level) get a wide window
and gentle wording.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from advastro.i18n import load_data, tr
from advastro.rate.measure import Measurements
from advastro.rate.objects import WEIGHTS as KIND_WEIGHTS
from advastro.rate.objects import PictureContext
from advastro.rate.picture import Picture

CATEGORIES = ("stars", "background", "colour", "detail", "tonality", "presentation", "depth")
WEIGHTS = {"stars": 0.22, "background": 0.20, "colour": 0.15, "detail": 0.14,
           "tonality": 0.15, "presentation": 0.08, "depth": 0.06}
PENALTY = {"critical": 45, "major": 18, "minor": 8, "info": 0, "good": 0}
# Overall verdict thresholds per skill level: excellent, ready, good-with-fixes.
THRESHOLDS = {"beginner": (86, 68, 52), "intermediate": (90, 77, 60), "advanced": (93, 84, 70)}
TARGET_SKY = {"beginner": "8–12", "intermediate": "8–12", "advanced": "7–11"}


@dataclass
class Finding:
    id: str
    category: str
    severity: str           # critical | major | minor | info | good
    title: str
    text: str
    overlay: str | None = None
    facts: dict = field(default_factory=dict)
    penalty: float | None = None

    @property
    def points(self) -> float:
        return PENALTY[self.severity] if self.penalty is None else self.penalty


@dataclass
class CategoryScore:
    category: str
    score: int
    verdict: str            # excellent | good | fair | weak


@dataclass
class Step:
    finding: Finding
    why: str
    steps: dict[str, list[str]]     # tool -> steps
    capture: list[str]
    masks: list[str] = field(default_factory=list)   # keys into masks.toml


@dataclass
class Rating:
    picture: Picture
    measurements: Measurements
    findings: list[Finding]
    categories: dict[str, CategoryScore]
    score: int
    verdict: str            # excellent | ready | fixable | needs_work
    headline: str
    plan: list[Step]
    capture: list[str]
    skill: str
    sky: object | None = None
    context: PictureContext = field(default_factory=PictureContext)

    @property
    def strengths(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "good"]

    @property
    def issues(self) -> list[Finding]:
        order = {"critical": 0, "major": 1, "minor": 2, "info": 3}
        return sorted((f for f in self.findings if f.severity != "good"),
                      key=lambda f: (order[f.severity], -f.points))


def _pct(v: float, digits: int = 0) -> str:
    return f"{v * 100:.{digits}f}"


def _hue_name(cast) -> tuple[str, str]:
    r, g, b = cast
    names = {(1, 0, 0): "red", (0, 1, 0): "green", (0, 0, 1): "blue",
             (1, 1, 0): "yellow", (0, 1, 1): "cyan", (1, 0, 1): "magenta"}
    best, score = "neutral", -1.0
    for key, name in names.items():
        v = [1 if k else -0.5 for k in key]
        s = r * v[0] + g * v[1] + b * v[2]
        if s > score:
            best, score = name, s
    channel = max(("red", r), ("green", g), ("blue", b), key=lambda t: t[1])[0]
    return best, channel


# ------------------------------------------------------------------------------- rules
def findings_for(m: Measurements, pic: Picture, skill: str = "intermediate",
                 sky=None, ctx: PictureContext | None = None) -> list[Finding]:
    ctx = ctx or PictureContext()
    kind = ctx.kind
    F: list[Finding] = []

    def add(id_, cat, sev, key, overlay=None, text_args=None, **facts):
        """key names the message in the catalogue (rate.f.<key>.title / .text)."""
        args = {**facts, **(text_args or {})}
        F.append(Finding(id_, cat, sev, tr(f"rate.f.{key}.title", **args),
                         tr(f"rate.f.{key}.text", **args), overlay, facts))

    target = TARGET_SKY.get(skill, "8–12")
    sky_pct = _pct(m.sky, 1)

    # --- tonality: linear, level, clipping, contrast --------------------------------
    if m.linear:
        add("linear", "tonality", "critical", "linear", target_sky=target)

    if not m.linear:
        if m.sky < 0.025 and m.black_clip_pct > 2:
            add("crushed_black", "background", "major", "crushed_black", "clipping",
                {"sky_pct": sky_pct}, black_clip=f"{m.black_clip_pct:.1f}", target_sky=target)
        elif m.sky < 0.04:
            add("dark_background", "background", "minor", "dark_background_minor", "background",
                sky_pct=sky_pct, target_sky=target)
        elif m.sky < 0.06:
            add("dark_background", "background", "info", "dark_background_info", "background",
                sky_pct=sky_pct, target_sky=target)
        elif m.sky <= 0.2:
            add("sky_level", "background", "good", "sky_level", text_args={"sky_pct": sky_pct})
        elif m.sky <= 0.28:
            add("bright_background", "background", "minor", "bright_background_minor",
                "background", sky_pct=sky_pct, target_sky=target)
        else:
            add("bright_background", "background", "major", "bright_background_major",
                "background", sky_pct=sky_pct, target_sky=target)
        if m.black_clip_pct > 1.0 and not any(f.id == "crushed_black" for f in F):
            add("shadow_clip", "tonality", "major" if m.black_clip_pct > 5 else "minor",
                "shadow_clip", "clipping", black_clip=f"{m.black_clip_pct:.1f}")
        if m.extended_clip_pct > 0.02:
            add("clipped_highlights", "tonality",
                "major" if m.extended_clip_pct > 0.15 else "minor", "clipped_highlights",
                "clipping", {"clip_pct": f"{m.extended_clip_pct:.2f}"},
                extended_clip_px=f"{m.extended_clip_px:,}")
        elif m.white_clip_pct < 0.5:
            add("highlights_ok", "tonality", "good", "highlights_ok")
        # The contrast measure looks at the whole frame. For a small galaxy or planetary
        # nebula, or a star cluster, that says little about the object itself.
        contrast_applies = not ctx.small_object and not ctx.star_subject
        if (m.signal_fraction > 0.003 or m.contrast > 0) and not m.linear and contrast_applies:
            if m.contrast < 0.07:
                add("low_contrast", "tonality", "minor" if ctx.fills_frame else "major",
                    "low_contrast", contrast_pct=_pct(m.contrast))
            elif m.contrast < 0.13:
                add("low_contrast", "tonality", "minor", "low_contrast_minor",
                    contrast_pct=_pct(m.contrast))
            elif m.contrast > 0.25:
                add("contrast_ok", "tonality", "good", "contrast_ok")
        if m.comb_pct > 20:
            add("banding", "tonality", "major" if m.comb_pct > 45 else "minor", "banding",
                comb_pct=f"{m.comb_pct:.0f}")
        elif m.plateau_pct > 40 and (m.levels or 0) <= 256:
            add("banding_risk", "tonality", "minor", "banding_risk",
                plateau_pct=f"{m.plateau_pct:.0f}")

    # --- background: gradient, cast, noise --------------------------------------------
    g = m.gradient_pct
    direction = ""
    if m.gradient_angle is not None and m.plane_pct > 1.0:
        sides = ["right", "lower_right", "bottom", "lower_left", "left", "upper_left", "top",
                 "upper_right"]
        side = sides[int(((m.gradient_angle + 22.5) % 360) // 45)]
        direction = tr("rate.w.brightest_towards", side=tr(f"rate.w.dir.{side}"))
    nebula_rich = m.signal_fraction > 0.25 or m.background_fraction < 0.2 or ctx.fills_frame
    grad = {"gradient_pct": f"{g:.1f}", "direction": direction}
    if kind == "milkyway" and (g > 5 or m.plane_pct > 3):
        add("gradient", "background", "info", "gradient_milkyway", "background", **grad)
    elif g > 9 or m.plane_pct > 6:
        add("gradient", "background", "minor" if nebula_rich else "major", "gradient",
            "background", **grad)
    elif g > 5 or m.plane_pct > 3:
        add("gradient", "background", "info" if nebula_rich or m.plane_pct < 2 else "minor",
            "gradient_slight", "background", **grad)
    else:
        add("flat_background", "background", "good", "flat_background",
            text_args={"gradient_pct": f"{g:.1f}"})
    if not m.mono:
        if m.color_gradient_pct > 7:
            add("color_gradient", "background", "major", "color_gradient", "cast",
                color_gradient_pct=f"{m.color_gradient_pct:.1f}")
        elif m.color_gradient_pct > 4:
            add("color_gradient", "background", "minor", "color_gradient_slight", "cast",
                color_gradient_pct=f"{m.color_gradient_pct:.1f}")
        dev = max(abs(c) for c in m.cast_rgb)
        name, channel = _hue_name(m.cast_rgb)
        lim_minor, lim_major = max(0.012, 0.16 * m.sky), max(0.025, 0.32 * m.sky)
        if m.green_excess > max(0.005, 0.06 * m.sky) and not m.linear:
            add("green_cast", "colour", "major" if m.green_excess > lim_major else "minor",
                "green_cast", "cast", {"green_pct": _pct(m.green_excess, 1)})
        elif dev > lim_minor and not m.linear:
            add("color_cast", "colour", "major" if dev > lim_major else "minor", "color_cast",
                "cast", {"hue_title": tr(f"rate.w.hue_title.{name}")},
                cast_name=tr(f"rate.w.hue.{name}"), cast_pct=_pct(dev, 1),
                cast_channel=tr(f"rate.w.channel.{channel}"))
        else:
            add("neutral_sky", "colour", "good", "neutral_sky")

    n = m.noise
    if m.levels and m.levels <= 256 and m.jpeg_quality and m.jpeg_quality < 70:
        pass  # compression hides the grain; the JPEG finding covers it
    elif n > 0.012:
        add("noise", "background", "major", "noise_major", "noise", noise_pct=_pct(n, 2))
    elif n > 0.0065:
        add("noise", "background", "minor", "noise_minor", "noise", noise_pct=_pct(n, 2))
    elif n < 0.0006 and (m.levels is None or m.levels > 256) and not m.linear and \
            m.black_clip_pct < 2:
        add("plastic", "detail", "minor", "plastic", "noise", noise_pct=_pct(n, 3))
    else:
        add("noise_ok", "background", "good", "noise_ok", text_args={"noise_pct": _pct(n, 2)})
    if not m.mono and m.chroma_noise > 0.008 and m.chroma_noise > 0.8 * max(n, 1e-6):
        add("color_noise", "background", "major" if m.chroma_noise > 0.016 else "minor",
            "color_noise", "noise", {"chroma_pct": _pct(m.chroma_noise, 2)})
    if m.noise_mid > 0.0026 and m.noise_mid > 0.5 * max(n, 1e-6):
        add("mottle", "background", "major" if m.noise_mid > 0.0045 else "minor", "mottle",
            "noise", {"mottle_pct": _pct(m.noise_mid, 2)})
    if m.walking_noise > 3.5:
        add("walking_noise", "background", "minor", "walking_noise", "noise",
            walking_angle=f"{m.walking_angle:.0f}")
    mp = m.width * m.height / 1e6
    if m.hot_pixels > max(30, 3 * mp):
        add("hot_pixels", "background", "major" if m.hot_pixels > 25 * mp else "minor",
            "hot_pixels", "hot", hot_pixels=m.hot_pixels)

    # --- stars --------------------------------------------------------------------------------
    if ctx.starless:
        add("starless", "presentation", "info",
            "starless_manual" if ctx.starless_source == "manual" else "starless_auto")
    elif m.star_count >= 15 and m.fwhm:
        fw = m.fwhm
        diag = math.hypot(m.width, m.height)
        trailed = (m.ellipticity or 0) > 0.3 and (m.orientation_coherence or 0) > 0.35
        if trailed:
            add("trailed_stars", "stars", "major" if m.ellipticity > 0.4 else "minor",
                "trailed_stars", "stars", ellipticity=f"{m.ellipticity:.2f}")
        elif (m.ellipticity or 0) < 0.22:
            add("round_stars", "stars", "good", "round_stars",
                text_args={"ellipticity": f"{m.ellipticity:.2f}"})
        if fw > 6.5:
            add("stars_soft", "stars", "major", "stars_soft_major", "stars", fwhm=f"{fw:.1f}")
        elif fw > 4.6:
            add("stars_soft", "stars", "minor", "stars_soft_minor", "stars", fwhm=f"{fw:.1f}")
        elif fw <= 3.6:
            add("tight_stars", "stars", "good", "tight_stars", text_args={"fwhm": f"{fw:.1f}"})
        if m.fwhm_bright and m.fwhm_bright / diag > 0.012:
            add("big_stars", "stars", "major" if m.fwhm_bright / diag > 0.02 else "minor",
                "big_stars", "stars", fwhm_bright=f"{m.fwhm_bright:.0f}")
        if m.star_area_pct > 22 and m.star_density > 1500 and kind not in (
                "milkyway", "cluster", "globular"):
            add("star_dominance", "stars", "minor", "star_dominance", "stars",
                star_area=f"{m.star_area_pct:.0f}")
        if m.corner_ratio and m.corner_ratio > 1.2 and not trailed:
            shape, hint = "", tr("rate.w.hint.default")
            if m.radial_alignment is not None and m.radial_alignment > 0.3:
                shape, hint = tr("rate.w.shape.radial"), tr("rate.w.hint.radial")
            elif m.radial_alignment is not None and m.radial_alignment < -0.3:
                shape, hint = tr("rate.w.shape.tangential"), tr("rate.w.hint.tangential")
            add("corner_stars", "stars", "major" if m.corner_ratio > 1.4 else "minor",
                "corner_stars", "stars", corner_pct=f"{(m.corner_ratio - 1) * 100:.0f}",
                shape=shape, capture_hint=hint)
        elif m.tilt_ratio and m.tilt_ratio > 1.3 and not trailed:
            add("tilt", "stars", "major" if m.tilt_ratio > 1.5 else "minor", "tilt", "stars",
                tilt_pct=f"{(m.tilt_ratio - 1) * 100:.0f}")
        elif m.corner_ratio and not trailed and not _corner_elongation(m):
            add("flat_field", "stars", "good", "flat_field",
                text_args={"within_pct": f"{abs(m.corner_ratio - 1) * 100:.0f}"})
        if not trailed and _corner_elongation(m):
            name, e = _corner_elongation(m)
            add("corner_elongation", "stars", "major" if e > 0.45 else "minor",
                "corner_elongation", "stars", {"centre": f"{m.ellipticity_grid[1, 1]:.2f}"},
                corner=tr(f"rate.w.corner.{name.replace(' ', '_')}"), ecc=f"{e:.2f}")
        if m.ring_fraction is not None:
            if m.ring_fraction > 0.25:
                add("star_rings", "stars", "major", "star_rings_major", "rings",
                    ring_pct=f"{m.ring_fraction * 100:.0f}")
            elif m.ring_fraction > 0.1:
                add("star_rings", "stars", "minor", "star_rings_minor", "rings",
                    ring_pct=f"{m.ring_fraction * 100:.0f}")
        if not m.mono:
            if m.color_spread is not None:
                if m.color_spread < 0.22:
                    add("star_color", "colour", "major" if ctx.star_subject and
                        m.color_spread < 0.15 else "minor", "star_color", "stars",
                        color_spread=f"{m.color_spread:.2f}")
                elif m.color_spread > 0.35:
                    add("star_color_ok", "colour", "good", "star_color_ok")
            if m.white_cores is not None and m.white_cores > 0.6 and not m.linear:
                add("white_cores", "stars", "minor", "white_cores", "stars",
                    {"white_pct": f"{m.white_cores * 100:.0f}"})
            if m.magenta_fraction is not None and m.magenta_fraction > 0.6:
                add("magenta_stars", "colour", "minor", "magenta_stars", "stars",
                    {"magenta_pct": f"{m.magenta_fraction * 100:.0f}"})
            if m.fringe is not None and abs(m.fringe) > 0.7:
                col = "blue" if m.fringe > 0 else "red"
                add("fringe", "stars", "minor", "fringe", "stars",
                    {"hue_title": tr(f"rate.w.hue_title.{col}"), "px": f"{abs(m.fringe):.1f}",
                     "channel": tr(f"rate.w.channel.{col}")},
                    fringe_color=tr(f"rate.w.hue.{col}"))
            elif m.lateral_ca is not None and m.lateral_ca > 1.2:
                add("fringe", "stars", "minor", "fringe_lateral", "stars",
                    {"px": f"{m.lateral_ca:.1f}"}, fringe_color=tr("rate.w.hue.red_blue"))
    elif m.star_count < 15:
        add("few_stars", "stars", "info", "few_stars")

    # --- colour ----------------------------------------------------------------------------------
    colour_applies = not ctx.star_subject
    # Galaxies have subtle colours; narrowband nebulae (HOO, SHO) are vivid by nature.
    mut_major, mut_minor = (0.05, 0.08) if kind == "galaxy" else (0.12, 0.22)
    sat_minor, sat_major = (0.78, 0.9) if kind in ("emission", "planetary") else (0.72, 0.85)
    if not m.mono and m.signal_fraction > 0.003 and not m.linear and colour_applies:
        s = m.saturation
        if s < mut_major:
            add("muted", "colour", "major", "muted_major", saturation_pct=_pct(s))
        elif s < mut_minor:
            add("muted", "colour", "minor", "muted_minor", saturation_pct=_pct(s))
        elif s > sat_major or m.saturation_high_pct > 30:
            add("oversaturated", "colour", "major", "oversaturated_major",
                sat_high=f"{m.saturation_high_pct:.0f}")
        elif s > sat_minor or m.saturation_high_pct > 10:
            add("oversaturated", "colour", "minor", "oversaturated_minor",
                sat_high=f"{m.saturation_high_pct:.0f}")
        else:
            add("saturation_ok", "colour", "good", "saturation_ok",
                text_args={"saturation_pct": _pct(s)})
        if m.channel_clip_pct > 1.0:
            add("channel_clip", "colour", "minor", "channel_clip", "clipping",
                channel_clip=f"{m.channel_clip_pct:.1f}")

    # --- detail ----------------------------------------------------------------------------
    if m.detail_ratio is not None and not m.linear and not ctx.star_subject:
        if m.detail_ratio < 1.6:
            add("low_detail", "detail", "minor", "low_detail",
                detail_ratio=f"{m.detail_ratio:.1f}")
        elif m.detail_ratio > 3:
            add("detail_ok", "detail", "good", "detail_ok",
                text_args={"detail_ratio": f"{m.detail_ratio:.1f}"})
    if m.jpeg_quality is not None:
        if m.jpeg_quality < 70 or m.blockiness > 2.2:
            add("jpeg", "detail", "major", "jpeg_major", jpeg_quality=m.jpeg_quality,
                blockiness=f"{m.blockiness:.1f}")
        elif m.jpeg_quality < 85 or m.blockiness > 1.7:
            add("jpeg", "detail", "minor", "jpeg_minor", jpeg_quality=m.jpeg_quality,
                blockiness=f"{m.blockiness:.1f}")

    # --- presentation ---------------------------------------------------------------------------
    if m.edges:
        names = ", ".join(tr(f"rate.w.edge.{e}") for e in m.edges)
        many = len(m.edges) > 1
        add("edges", "presentation", "major", "edges_many" if many else "edges_one", "edges",
            edges=names, edges_s="s" if many else "")
    else:
        add("clean_edges", "presentation", "good", "clean_edges")
    if mp < 1.0:
        add("small_image", "presentation", "minor", "small_image", megapixels=f"{mp:.1f}")
    if pic.levels and pic.levels <= 256 and pic.format in ("png", "tiff"):
        add("eight_bit", "presentation", "info", "eight_bit")
    cx, cy = m.centroid
    if m.signal_fraction > 0.01 and math.hypot(cx - 0.5, cy - 0.5) > 0.28 and \
            not ctx.fills_frame and kind != "milkyway":
        side = ("left" if cx < 0.4 else "right" if cx > 0.6 else "") or \
               ("top" if cy < 0.4 else "bottom")
        add("off_centre", "presentation", "info", "off_centre",
            text_args={"side": tr(f"rate.w.dir.{side}")})

    # --- sky (plate solve, Gaia, framing) ------------------------------------------------------
    if sky is not None:
        F.extend(sky.findings())
    return F


def _corner_elongation(m: Measurements):
    """(corner name, elongation) when one corner's stars are clearly stretched."""
    g = m.ellipticity_grid
    if g is None or not np.isfinite(g[1, 1]):
        return None
    corners = {"upper left": g[0, 0], "upper right": g[0, 2], "lower left": g[2, 0],
               "lower right": g[2, 2]}
    corners = {k: v for k, v in corners.items() if np.isfinite(v)}
    if not corners:
        return None
    name, e = max(corners.items(), key=lambda kv: kv[1])
    others = [v for k, v in corners.items() if k != name]
    if e > 0.3 and e - g[1, 1] > 0.15 and (not others or e - max(others) > 0.1):
        return name, float(e)
    return None


# ------------------------------------------------------------------------------- scoring
def _category_verdict(score: float) -> str:
    return "excellent" if score >= 90 else "good" if score >= 75 else \
        "fair" if score >= 55 else "weak"


def score(findings: list[Finding], mono: bool, has_sky: bool,
          ctx: PictureContext | None = None) -> tuple[dict, int]:
    ctx = ctx or PictureContext()
    weights = KIND_WEIGHTS.get(ctx.kind, WEIGHTS)
    cats = {}
    for cat in CATEGORIES:
        if cat == "colour" and mono:
            continue
        if cat == "stars" and ctx.starless:
            continue
        if cat == "depth" and not any(f.category == "depth" for f in findings):
            continue
        pts = sum(f.points for f in findings if f.category == cat)
        s = int(round(max(0.0, min(100.0, 100.0 - pts))))
        cats[cat] = CategoryScore(cat, s, _category_verdict(s))
    total_w = sum(weights[c] for c in cats)
    overall = sum(weights[c] * cats[c].score for c in cats) / total_w
    majors = sum(1 for f in findings if f.severity == "major")
    minors = sum(1 for f in findings if f.severity == "minor")
    # Problems a viewer notices weigh on the whole picture, not only on their category.
    overall -= 4 * majors + 1 * minors
    if any(f.severity == "critical" for f in findings):
        overall = min(overall, 45)
    return cats, int(round(max(0, min(100, overall))))


def verdict_for(score_: int, skill: str, findings: list[Finding] | None = None) -> str:
    excellent, ready, fixable = THRESHOLDS.get(skill, THRESHOLDS["intermediate"])
    v = "excellent" if score_ >= excellent else "ready" if score_ >= ready else \
        "fixable" if score_ >= fixable else "needs_work"
    if findings:
        majors = sum(1 for f in findings if f.severity == "major")
        rank = ["needs_work", "fixable", "ready", "excellent"]
        cap = "excellent"
        if any(f.severity == "critical" for f in findings) or majors >= 3:
            cap = "needs_work"
        elif majors >= 1:
            cap = "fixable"      # something most viewers will notice
        elif sum(1 for f in findings if f.severity == "minor") >= 4:
            cap = "ready"
        v = rank[min(rank.index(v), rank.index(cap))]
    return v


def headline(verdict: str) -> str:
    return tr(f"rate.headline.{verdict}")


# ------------------------------------------------------------------------------- tips
def _load_tips() -> dict:
    return load_data("advastro.rate", "tips.toml")


def load_masks() -> dict:
    """Mask recipes: key -> {title, what, pixinsight: [...], siril: [...]}."""
    return load_data("advastro.rate", "masks.toml")


class _Defaults(dict):
    def __missing__(self, key):
        return "?"


def plan_for(findings: list[Finding], m: Measurements, tools: list[str],
             addons: list[str], kind: str = "unknown") -> tuple[list[Step], list[str]]:
    """Steps per finding and tool. tips.toml may hold variants: <tool>#<kind> for an object
    type, <tool>@<add-on> for an add-on, and <tool>@<add-on>#<kind> for both."""
    tips = _load_tips()
    base = _Defaults(sky_pct=_pct(m.sky, 1), noise_pct=_pct(m.noise, 2),
                     fwhm=f"{m.fwhm:.1f}" if m.fwhm else "?",
                     gradient_pct=f"{m.gradient_pct:.1f}", saturation_pct=_pct(m.saturation),
                     target_sky="8–12", direction="", shape="")
    steps, capture = [], []
    order = {"critical": 0, "major": 1, "minor": 2, "info": 3}
    for f in sorted((f for f in findings if f.severity != "good" and f.id in tips),
                    key=lambda f: (order[f.severity], -f.points)):
        entry = tips[f.id]
        facts = _Defaults(base)
        facts.update({k: v for k, v in f.facts.items()})
        per_tool = {}
        for tool in tools:
            key = tool.lower()
            chosen = entry.get(f"{key}#{kind}") or entry.get(key, [])
            for addon in addons:
                variant = entry.get(f"{key}@{addon}#{kind}") or entry.get(f"{key}@{addon}")
                if variant:
                    chosen = variant
                    break
            if chosen:
                per_tool[tool] = [s.format_map(facts) for s in chosen]
        cap = [s.format_map(facts) for s in entry.get("capture", []) if s.strip("{}") != ""]
        for c in cap:
            if c and c not in capture:
                capture.append(c)
        why = entry.get(f"why#{kind}") or entry.get("why", "")
        steps.append(Step(f, why.format_map(facts), per_tool, cap, list(entry.get("masks", []))))
    return steps, capture


# ------------------------------------------------------------------------------- entry
def judge(pic: Picture, m: Measurements, profile: dict | None = None, sky=None,
          object_kind: str = "auto", starless: str = "auto",
          object_name: str | None = None) -> Rating:
    """object_kind: "auto" or one of objects.KINDS; starless: "auto", "yes" or "no"."""
    from advastro.rate.objects import picture_context

    profile = profile or {}
    ctx = picture_context(m, pic, sky, object_kind, starless, object_name)
    skill = profile.get("skill", "intermediate")
    software = [s for s in profile.get("software", ["PixInsight", "Siril"])
                if s.lower() in ("pixinsight", "siril")] or ["PixInsight", "Siril"]
    addons = list(profile.get("paid_addons", []))
    findings = findings_for(m, pic, skill, sky, ctx)
    if ctx.starless:      # the Gaia checks need stars
        findings = [f for f in findings if f.id not in ("color_calibration",
                                                        "color_calibration_ok", "depth")]
    for f in findings:
        if f.id in ("dark_background", "bright_background", "crushed_black", "linear"):
            f.facts.setdefault("target_sky", TARGET_SKY.get(skill, "8–12"))
    cats, overall = score(findings, m.mono, sky is not None, ctx)
    verdict = verdict_for(overall, skill, findings)
    plan, capture = plan_for(findings, m, software, addons, ctx.kind)
    return Rating(pic, m, findings, cats, overall, verdict, headline(verdict), plan, capture,
                  skill, sky, ctx)
