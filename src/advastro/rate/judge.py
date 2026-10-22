"""Turn measurements into findings, category verdicts, an overall verdict and a plan.

Thresholds are deliberate and documented next to each rule. Technical faults are
judged strictly; matters of taste (saturation, background level) get a wide window
and gentle wording.
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass, field
from importlib import resources

import numpy as np

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

    def add(id_, cat, sev, title, text, overlay=None, **facts):
        F.append(Finding(id_, cat, sev, title, text, overlay, facts))

    target = TARGET_SKY.get(skill, "8–12")
    sky_pct = _pct(m.sky, 1)

    # --- tonality: linear, level, clipping, contrast --------------------------------
    if m.linear:
        add("linear", "tonality", "critical", "The image has not been stretched yet",
            "The data is still linear, so the faint signal is not visible. The rest of "
            "this report judges an automatic stretch of it.", target_sky=target)

    if not m.linear:
        if m.sky < 0.025 and m.black_clip_pct > 2:
            add("crushed_black", "background", "major", "Crushed black background",
                f"The sky is at {sky_pct} % with {m.black_clip_pct:.1f} % of the pixels "
                "clipped to black. Faint stars and faint nebulosity are cut away.",
                "clipping", black_clip=f"{m.black_clip_pct:.1f}", target_sky=target)
        elif m.sky < 0.04:
            add("dark_background", "background", "minor", "Very dark background",
                f"The sky sits at {sky_pct} % brightness. Faint detail near the background "
                "is hard to see.", "background", sky_pct=sky_pct, target_sky=target)
        elif m.sky < 0.06:
            add("dark_background", "background", "info", "Dark background",
                f"The sky sits at {sky_pct} %, on the dark side. Fine if that is your style.",
                "background", sky_pct=sky_pct, target_sky=target)
        elif m.sky <= 0.2:
            add("sky_level", "background", "good", "Background level is well judged",
                f"The sky sits at {sky_pct} % brightness: dark, but not clipped.")
        elif m.sky <= 0.28:
            add("bright_background", "background", "minor", "Background a bit bright",
                f"The sky sits at {sky_pct} %, which looks slightly grey and hazy.",
                "background", sky_pct=sky_pct, target_sky=target)
        else:
            add("bright_background", "background", "major", "Washed-out background",
                f"The sky sits at {sky_pct} %: grey rather than dark. Contrast suffers.",
                "background", sky_pct=sky_pct, target_sky=target)
        if m.black_clip_pct > 1.0 and not any(f.id == "crushed_black" for f in F):
            add("shadow_clip", "tonality", "major" if m.black_clip_pct > 5 else "minor",
                "Clipped shadows",
                f"{m.black_clip_pct:.1f} % of the pixels have a colour channel clipped to zero.",
                "clipping", black_clip=f"{m.black_clip_pct:.1f}")
        if m.extended_clip_pct > 0.02:
            add("clipped_highlights", "tonality",
                "major" if m.extended_clip_pct > 0.15 else "minor", "Burned-out highlights",
                f"{m.extended_clip_px:,} pixels outside star cores are clipped to full white "
                f"({m.extended_clip_pct:.2f} % of the frame).", "clipping",
                extended_clip_px=f"{m.extended_clip_px:,}")
        elif m.white_clip_pct < 0.5:
            add("highlights_ok", "tonality", "good", "No burned-out highlights",
                "Bright areas keep their structure; only star cores reach full white.")
        # The contrast measure looks at the whole frame. For a small galaxy or planetary
        # nebula, or a star cluster, that says little about the object itself.
        contrast_applies = not ctx.small_object and not ctx.star_subject
        if (m.signal_fraction > 0.003 or m.contrast > 0) and not m.linear and contrast_applies:
            if m.contrast < 0.07:
                add("low_contrast", "tonality", "minor" if ctx.fills_frame else "major",
                    "Low contrast",
                    f"The brightest parts of the object reach only {_pct(m.contrast)} % above "
                    "the background.", contrast_pct=_pct(m.contrast))
            elif m.contrast < 0.13:
                add("low_contrast", "tonality", "minor", "Object could be brighter",
                    f"The object rises {_pct(m.contrast)} % above the background; "
                    "there is room to stretch further.", contrast_pct=_pct(m.contrast))
            elif m.contrast > 0.25:
                add("contrast_ok", "tonality", "good", "Good contrast",
                    "The object stands out clearly from the background.")
        if m.comb_pct > 20:
            add("banding", "tonality", "major" if m.comb_pct > 45 else "minor",
                "Histogram gaps (banding)",
                f"{m.comb_pct:.0f} % of the levels in the used range are empty: the image was "
                "stretched after being reduced to 8 bits.", comb_pct=f"{m.comb_pct:.0f}")
        elif m.plateau_pct > 40 and (m.levels or 0) <= 256:
            add("banding_risk", "tonality", "minor", "Risk of visible banding",
                f"{m.plateau_pct:.0f} % of the sky consists of flat 8-bit steps.",
                plateau_pct=f"{m.plateau_pct:.0f}")

    # --- background: gradient, cast, noise --------------------------------------------
    g = m.gradient_pct
    direction = ""
    if m.gradient_angle is not None and m.plane_pct > 1.0:
        sides = ["right", "lower right", "bottom", "lower left", "left", "upper left", "top",
                 "upper right"]
        direction = f", brightest towards the {sides[int(((m.gradient_angle + 22.5) % 360) // 45)]}"
    nebula_rich = m.signal_fraction > 0.25 or m.background_fraction < 0.2 or ctx.fills_frame
    if kind == "milkyway" and (g > 5 or m.plane_pct > 3):
        add("gradient", "background", "info", "Brightness changes across the field",
            f"The background changes by {g:.1f} %{direction}. In a Milky Way field much of that "
            "is the Milky Way itself; check that the darkest corners are neutral and even.",
            "background", gradient_pct=f"{g:.1f}", direction=direction)
    elif g > 9 or m.plane_pct > 6:
        add("gradient", "background", "minor" if nebula_rich else "major",
            "Uneven background (gradient)",
            f"The background brightness changes by {g:.1f} % of full scale across the "
            f"frame{direction}.", "background", gradient_pct=f"{g:.1f}", direction=direction)
    elif g > 5 or m.plane_pct > 3:
        add("gradient", "background", "info" if nebula_rich or m.plane_pct < 2 else "minor",
            "Slightly uneven background",
            f"The background changes by {g:.1f} %{direction}. If that is real nebulosity in "
            "your field, it is fine.", "background", gradient_pct=f"{g:.1f}",
            direction=direction)
    else:
        add("flat_background", "background", "good", "Even background",
            f"No significant gradient ({g:.1f} % variation).")
    if not m.mono:
        if m.color_gradient_pct > 7:
            add("color_gradient", "background", "major", "Colour gradient",
                f"The sky changes colour across the frame (up to {m.color_gradient_pct:.1f} %).",
                "cast", color_gradient_pct=f"{m.color_gradient_pct:.1f}")
        elif m.color_gradient_pct > 4:
            add("color_gradient", "background", "minor", "Slight colour gradient",
                f"The sky colour changes a little across the frame "
                f"({m.color_gradient_pct:.1f} %).", "cast",
                color_gradient_pct=f"{m.color_gradient_pct:.1f}")
        dev = max(abs(c) for c in m.cast_rgb)
        name, channel = _hue_name(m.cast_rgb)
        lim_minor, lim_major = max(0.012, 0.16 * m.sky), max(0.025, 0.32 * m.sky)
        if m.green_excess > max(0.005, 0.06 * m.sky) and not m.linear:
            add("green_cast", "colour", "major" if m.green_excess > lim_major else "minor",
                "Green tint in the sky",
                f"The background is {_pct(m.green_excess, 1)} % greener than neutral.", "cast")
        elif dev > lim_minor and not m.linear:
            add("color_cast", "colour", "major" if dev > lim_major else "minor",
                f"{name.capitalize()} background",
                f"The sky is tinted {name}: the channels differ by {_pct(dev, 1)} % "
                "of full scale.", "cast", cast_name=name, cast_pct=_pct(dev, 1),
                cast_channel=channel)
        else:
            add("neutral_sky", "colour", "good", "Neutral background colour",
                "The sky is close to neutral grey.")

    n = m.noise
    if m.levels and m.levels <= 256 and m.jpeg_quality and m.jpeg_quality < 70:
        pass  # compression hides the grain; the JPEG finding covers it
    elif n > 0.012:
        add("noise", "background", "major", "Grainy background",
            f"Noise in the sky is {_pct(n, 2)} % of full scale: clearly visible.", "noise",
            noise_pct=_pct(n, 2))
    elif n > 0.0065:
        add("noise", "background", "minor", "Visible grain",
            f"Noise in the sky is {_pct(n, 2)} % of full scale.", "noise", noise_pct=_pct(n, 2))
    elif n < 0.0006 and (m.levels is None or m.levels > 256) and not m.linear and \
            m.black_clip_pct < 2:
        add("plastic", "detail", "minor", "Background looks over-smoothed",
            f"The sky has almost no grain at all ({_pct(n, 3)} %), which can look plastic.",
            "noise", noise_pct=_pct(n, 3))
    else:
        add("noise_ok", "background", "good", "Clean background",
            f"Noise is low ({_pct(n, 2)} % of full scale).")
    if not m.mono and m.chroma_noise > 0.008 and m.chroma_noise > 0.8 * max(n, 1e-6):
        add("color_noise", "background", "major" if m.chroma_noise > 0.016 else "minor",
            "Colour noise", f"The grain is coloured ({_pct(m.chroma_noise, 2)} % chroma noise).",
            "noise")
    if m.noise_mid > 0.0026 and m.noise_mid > 0.5 * max(n, 1e-6):
        add("mottle", "background", "major" if m.noise_mid > 0.0045 else "minor",
            "Blotchy background (mottle)",
            f"The sky shows blotches a few pixels wide ({_pct(m.noise_mid, 2)} % amplitude).",
            "noise")
    if m.walking_noise > 3.5:
        add("walking_noise", "background", "minor", "Possible walking noise",
            f"The background noise has a direction (streaks at about {m.walking_angle:.0f}°).",
            "noise", walking_angle=f"{m.walking_angle:.0f}")
    mp = m.width * m.height / 1e6
    if m.hot_pixels > max(30, 3 * mp):
        add("hot_pixels", "background", "major" if m.hot_pixels > 25 * mp else "minor",
            "Hot pixels left", f"{m.hot_pixels} isolated bright pixels.", "hot",
            hot_pixels=m.hot_pixels)

    # --- stars --------------------------------------------------------------------------------
    if ctx.starless:
        add("starless", "presentation", "info", "Judged as a starless image",
            "Star checks are skipped" + (" (you marked it as starless)."
                                         if ctx.starless_source == "manual" else
                                         ": almost no real stars were found.") +
            " Background, colour, tonality and detail are judged as usual.")
    elif m.star_count >= 15 and m.fwhm:
        fw = m.fwhm
        diag = math.hypot(m.width, m.height)
        trailed = (m.ellipticity or 0) > 0.3 and (m.orientation_coherence or 0) > 0.35
        if trailed:
            add("trailed_stars", "stars", "major" if m.ellipticity > 0.4 else "minor",
                "Elongated stars", f"Stars are stretched in one direction "
                f"(median elongation {m.ellipticity:.2f}).", "stars",
                ellipticity=f"{m.ellipticity:.2f}")
        elif (m.ellipticity or 0) < 0.22:
            add("round_stars", "stars", "good", "Round stars",
                f"Stars are round across the frame (median elongation {m.ellipticity:.2f}).")
        if fw > 6.5:
            add("stars_soft", "stars", "major", "Large, soft stars",
                f"Stars are {fw:.1f} pixels across at half brightness.", "stars", fwhm=f"{fw:.1f}")
        elif fw > 4.6:
            add("stars_soft", "stars", "minor", "Stars on the large side",
                f"Stars are {fw:.1f} pixels across at half brightness.", "stars", fwhm=f"{fw:.1f}")
        elif fw <= 3.6:
            add("tight_stars", "stars", "good", "Tight stars",
                f"Stars are small and well defined ({fw:.1f} px).")
        if m.fwhm_bright and m.fwhm_bright / diag > 0.012:
            add("big_stars", "stars", "major" if m.fwhm_bright / diag > 0.02 else "minor",
                "Bright stars dominate", f"The brightest stars are {m.fwhm_bright:.0f} pixels "
                "across.", "stars", fwhm_bright=f"{m.fwhm_bright:.0f}")
        if m.star_area_pct > 22 and m.star_density > 1500 and kind not in (
                "milkyway", "cluster", "globular"):
            add("star_dominance", "stars", "minor", "Stars crowd the object",
                f"Stars cover about {m.star_area_pct:.0f} % of the frame.", "stars",
                star_area=f"{m.star_area_pct:.0f}")
        if m.corner_ratio and m.corner_ratio > 1.2 and not trailed:
            shape, hint = "", ("Check the spacing between the field flattener or corrector and "
                               "the sensor (back focus).")
            if m.radial_alignment is not None and m.radial_alignment > 0.3:
                shape = ", stretched towards the centre or outwards (coma)"
                hint = ("Radial elongation means the back focus spacing is off: adjust the "
                        "flattener or coma corrector spacing in small steps.")
            elif m.radial_alignment is not None and m.radial_alignment < -0.3:
                shape = ", stretched along circles (astigmatism or field curvature)"
                hint = ("Tangential elongation usually means field curvature: a flattener, or "
                        "a different spacing, helps.")
            add("corner_stars", "stars", "major" if m.corner_ratio > 1.4 else "minor",
                "Softer stars in the corners",
                f"Corner stars are {(m.corner_ratio - 1) * 100:.0f} % larger than in the "
                f"centre{shape}.", "stars", corner_pct=f"{(m.corner_ratio - 1) * 100:.0f}",
                shape=shape, capture_hint=hint)
        elif m.tilt_ratio and m.tilt_ratio > 1.3 and not trailed:
            add("tilt", "stars", "major" if m.tilt_ratio > 1.5 else "minor",
                "Uneven sharpness between the corners",
                f"The sharpest and softest corners differ by {(m.tilt_ratio - 1) * 100:.0f} %. "
                "Sensor tilt is one possible cause; spacing, collimation, flexure and how the "
                "subs were stacked are others (see Improve).",
                "stars", tilt_pct=f"{(m.tilt_ratio - 1) * 100:.0f}")
        elif m.corner_ratio and not trailed and not _corner_elongation(m):
            add("flat_field", "stars", "good", "Sharp to the corners",
                f"Corner stars match the centre (within {abs(m.corner_ratio - 1) * 100:.0f} %).")
        if not trailed and _corner_elongation(m):
            name, e = _corner_elongation(m)
            add("corner_elongation", "stars", "major" if e > 0.45 else "minor",
                f"Stretched stars in the {name} corner",
                f"Stars in the {name} corner are elongated ({e:.2f}, against "
                f"{m.ellipticity_grid[1, 1]:.2f} in the centre).", "stars", corner=name,
                ecc=f"{e:.2f}")
        if m.ring_fraction is not None:
            if m.ring_fraction > 0.25:
                add("star_rings", "stars", "major", "Dark rings around stars",
                    f"{m.ring_fraction * 100:.0f} % of the bright stars have a dark ring.",
                    "rings", ring_pct=f"{m.ring_fraction * 100:.0f}")
            elif m.ring_fraction > 0.1:
                add("star_rings", "stars", "minor", "Some stars have dark rings",
                    f"{m.ring_fraction * 100:.0f} % of the bright stars have a dark ring.",
                    "rings", ring_pct=f"{m.ring_fraction * 100:.0f}")
        if not m.mono:
            if m.color_spread is not None:
                if m.color_spread < 0.22:
                    add("star_color", "colour", "major" if ctx.star_subject and
                        m.color_spread < 0.15 else "minor", "Colourless stars",
                        "The stars show little colour variety.", "stars",
                        color_spread=f"{m.color_spread:.2f}")
                elif m.color_spread > 0.35:
                    add("star_color_ok", "colour", "good", "Colourful stars",
                        "Stars show a natural range of colours.")
            if m.white_cores is not None and m.white_cores > 0.6 and not m.linear:
                add("white_cores", "stars", "minor", "White star cores",
                    f"{m.white_cores * 100:.0f} % of the bright stars have clipped white cores.",
                    "stars")
            if m.magenta_fraction is not None and m.magenta_fraction > 0.6:
                add("magenta_stars", "colour", "minor", "Magenta stars",
                    f"{m.magenta_fraction * 100:.0f} % of the stars are magenta.", "stars")
            if m.fringe is not None and abs(m.fringe) > 0.7:
                col = "blue" if m.fringe > 0 else "red"
                add("fringe", "stars", "minor", f"{col.capitalize()} star rims",
                    f"Stars are {abs(m.fringe):.1f} px larger in {col} than in the other colours.",
                    "stars", fringe_color=col)
            elif m.lateral_ca is not None and m.lateral_ca > 1.2:
                add("fringe", "stars", "minor", "Colour fringes towards the edges",
                    f"Red and blue are offset by {m.lateral_ca:.1f} px in the outer field.",
                    "stars", fringe_color="red/blue")
    elif m.star_count < 15:
        add("few_stars", "stars", "info", "Few stars to measure",
            "Too few stars were found for a star assessment (starless image?).")

    # --- colour ----------------------------------------------------------------------------------
    colour_applies = not ctx.star_subject
    # Galaxies have subtle colours; narrowband nebulae (HOO, SHO) are vivid by nature.
    mut_major, mut_minor = (0.05, 0.08) if kind == "galaxy" else (0.12, 0.22)
    sat_minor, sat_major = (0.78, 0.9) if kind in ("emission", "planetary") else (0.72, 0.85)
    if not m.mono and m.signal_fraction > 0.003 and not m.linear and colour_applies:
        s = m.saturation
        if s < mut_major:
            add("muted", "colour", "major", "Almost colourless",
                f"Median saturation of the object is {_pct(s)} %.", saturation_pct=_pct(s))
        elif s < mut_minor:
            add("muted", "colour", "minor", "Muted colours",
                f"Median saturation of the object is {_pct(s)} %.", saturation_pct=_pct(s))
        elif s > sat_major or m.saturation_high_pct > 30:
            add("oversaturated", "colour", "major", "Oversaturated colours",
                f"{m.saturation_high_pct:.0f} % of the object is near full saturation.",
                sat_high=f"{m.saturation_high_pct:.0f}")
        elif s > sat_minor or m.saturation_high_pct > 10:
            add("oversaturated", "colour", "minor", "Strong saturation",
                f"{m.saturation_high_pct:.0f} % of the object is near full saturation.",
                sat_high=f"{m.saturation_high_pct:.0f}")
        else:
            add("saturation_ok", "colour", "good", "Well-balanced saturation",
                f"Colours are rich without being garish (median {_pct(s)} %).")
        if m.channel_clip_pct > 1.0:
            add("channel_clip", "colour", "minor", "Clipped colour channel",
                f"{m.channel_clip_pct:.1f} % of the object has one colour channel clipped.",
                "clipping", channel_clip=f"{m.channel_clip_pct:.1f}")

    # --- detail ----------------------------------------------------------------------------
    if m.detail_ratio is not None and not m.linear and not ctx.star_subject:
        if m.detail_ratio < 1.6:
            add("low_detail", "detail", "minor", "Little fine detail",
                "Fine structure barely rises above the noise.",
                detail_ratio=f"{m.detail_ratio:.1f}")
        elif m.detail_ratio > 3:
            add("detail_ok", "detail", "good", "Good fine detail",
                f"Fine structure stands well above the noise ({m.detail_ratio:.1f}x).")
    if m.jpeg_quality is not None:
        if m.jpeg_quality < 70 or m.blockiness > 2.2:
            add("jpeg", "detail", "major", "Heavy JPEG compression",
                f"Quality about {m.jpeg_quality}, with visible 8x8 blocks ({m.blockiness:.1f}x).",
                jpeg_quality=m.jpeg_quality, blockiness=f"{m.blockiness:.1f}")
        elif m.jpeg_quality < 85 or m.blockiness > 1.7:
            add("jpeg", "detail", "minor", "Noticeable JPEG compression",
                f"Quality about {m.jpeg_quality} ({m.blockiness:.1f}x block edges).",
                jpeg_quality=m.jpeg_quality, blockiness=f"{m.blockiness:.1f}")

    # --- presentation ---------------------------------------------------------------------------
    if m.edges:
        names = ", ".join(m.edges)
        add("edges", "presentation", "major", "Stacking edges not cropped",
            f"Ragged or dark borders on the {names} side{'s' if len(m.edges) > 1 else ''}.",
            "edges", edges=names, edges_s="s" if len(m.edges) > 1 else "")
    else:
        add("clean_edges", "presentation", "good", "Clean edges",
            "No stacking borders left.")
    if mp < 1.0:
        add("small_image", "presentation", "minor", "Small image",
            f"Only {mp:.1f} megapixels.", megapixels=f"{mp:.1f}")
    if pic.levels and pic.levels <= 256 and pic.format in ("png", "tiff"):
        add("eight_bit", "presentation", "info", "8-bit file",
            "Fine for sharing; keep a 16- or 32-bit master for printing and reprocessing.")
    cx, cy = m.centroid
    if m.signal_fraction > 0.01 and math.hypot(cx - 0.5, cy - 0.5) > 0.28 and \
            not ctx.fills_frame and kind != "milkyway":
        side = ("left" if cx < 0.4 else "right" if cx > 0.6 else "") or \
               ("top" if cy < 0.4 else "bottom")
        add("off_centre", "presentation", "info", "Subject sits off-centre",
            f"Most of the light is towards the {side}. Deliberate placement can work well; "
            "if not, a crop can rebalance the frame.")

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


HEADLINES = {
    "excellent": "This image is ready for AstroBin, competitions and print.",
    "ready": "A solid image with only small things to polish.",
    "fixable": "A few targeted changes will lift it a level.",
    "needs_work": "The issues below are visible to most viewers; the plan shows where to start.",
}


# ------------------------------------------------------------------------------- tips
def _load_tips() -> dict:
    return tomllib.loads(resources.files("advastro.rate").joinpath("tips.toml")
                         .read_text(encoding="utf-8"))


def load_masks() -> dict:
    """Mask recipes: key -> {title, what, pixinsight: [...], siril: [...]}."""
    return tomllib.loads(resources.files("advastro.rate").joinpath("masks.toml")
                         .read_text(encoding="utf-8"))


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
    return Rating(pic, m, findings, cats, overall, verdict, HEADLINES[verdict], plan, capture,
                  skill, sky, ctx)
