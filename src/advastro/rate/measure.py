"""Measure a finished (stretched, processed) astrophoto.

Everything here works in display space: values in [0, 1] as the viewer sees them.
The measurements look for what processing leaves behind: background level and
neutrality, gradients, grain and mottle, star size and shape across the field,
rings from sharpening, colour fringes, clipping, banding, compression, edges.

Each measurement keeps the data needed to draw it on the picture (maps, points,
regions), so every finding can show where it is.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

from advastro.rate.picture import Picture

MAD = 1.4826
WORK_MAX_SIDE = 6200       # bigger pictures are binned 2x2 for the analysis


# ---------------------------------------------------------------------------- results
@dataclass
class StarSample:
    x: float
    y: float
    fwhm: float
    ellipticity: float
    angle: float            # major axis, radians, image coordinates
    peak: float
    saturated: bool
    ring: bool
    color_index: float | None   # -2.5 log10(B/R): negative = blue, positive = red


@dataclass
class Overlays:
    """What the window draws on top of the picture. Coordinates in work pixels."""

    scale: float = 1.0                          # work pixel -> picture pixel
    background: np.ndarray | None = None        # deviation from sky level, small grid
    noise: np.ndarray | None = None             # pixel noise per tile
    cast: np.ndarray | None = None              # (gy, gx, 3) background colour deviation
    fwhm_map: np.ndarray | None = None          # star size per region
    stars: list[StarSample] = field(default_factory=list)
    clipped_white: np.ndarray | None = None     # low-res masks
    clipped_black: np.ndarray | None = None
    hot_pixels: list[tuple[int, int]] = field(default_factory=list)
    edges: list[str] = field(default_factory=list)   # "left", "top", ...
    rings: list[tuple[float, float, float]] = field(default_factory=list)  # x, y, r


@dataclass
class Measurements:
    width: int
    height: int
    work_binned: int
    mono: bool
    linear: bool                    # data was still linear; measured on an auto-stretch
    # background
    sky: float = 0.0
    sky_rgb: tuple[float, float, float] = (0.0, 0.0, 0.0)
    background_fraction: float = 0.0   # share of the frame that is (darkest) sky
    gradient_pct: float = 0.0          # range of the smooth background model, % of full scale
    gradient_angle: float | None = None  # direction of increasing brightness, degrees
    color_gradient_pct: float = 0.0
    plane_pct: float = 0.0             # linear (one-sided) part of the gradient
    black_clip_pct: float = 0.0
    white_clip_pct: float = 0.0
    extended_clip_px: int = 0           # clipped area outside star cores
    extended_clip_pct: float = 0.0
    channel_clip_pct: float = 0.0       # one channel clipped while the others are not
    cast_rgb: tuple[float, float, float] = (0.0, 0.0, 0.0)  # background deviation per channel
    green_excess: float = 0.0
    # noise
    noise: float = 0.0                  # pixel-scale noise in the darkest areas
    noise_mid: float = 0.0              # mottle: noise at 3–12 px scales
    mottle_ratio: float = 0.0           # noise_mid relative to white noise expectation
    chroma_noise: float = 0.0
    walking_noise: float = 0.0          # anisotropy of background noise (1 = none)
    walking_angle: float | None = None
    hot_pixels: int = 0
    # tonality
    p_low: float = 0.0
    p_high: float = 0.0
    contrast: float = 0.0               # bright structure above the sky
    levels: int | None = None
    plateau_pct: float = 0.0            # flat 8-bit steps in smooth areas (banding)
    comb_pct: float = 0.0               # empty histogram bins inside the used range
    jpeg_quality: int | None = None
    blockiness: float = 1.0
    # colour
    saturation: float = 0.0             # median saturation of nebula / galaxy areas
    saturation_high_pct: float = 0.0
    signal_fraction: float = 0.0
    # stars
    star_count: int = 0
    star_density: float = 0.0           # per megapixel
    fwhm: float | None = None           # median, picture pixels
    fwhm_bright: float | None = None    # core diameter of the brightest stars
    ellipticity: float | None = None
    orientation_coherence: float | None = None   # 1 = all stars point the same way
    fwhm_grid: np.ndarray | None = None          # 3x3
    ellipticity_grid: np.ndarray | None = None   # 3x3
    radial_alignment: float | None = None        # corners: +1 radial (coma), -1 tangential
    corner_ratio: float | None = None            # corner / centre FWHM
    tilt_ratio: float | None = None              # worst / best corner FWHM
    ring_fraction: float | None = None           # bright stars with a dark ring
    color_spread: float | None = None            # spread of star colour index
    white_cores: float | None = None             # saturated stars with white cores
    magenta_fraction: float | None = None
    fringe: float | None = None                  # blue minus red radius, px
    lateral_ca: float | None = None              # R/B centroid shift in the corners, px
    star_area_pct: float = 0.0
    compact_sources: int = 0                     # small, round, clearly bright point sources
    compact_density: float = 0.0                 # the same per megapixel
    bright_sources: int = 0                      # sources well above the sky, any shape
    # detail
    detail_ratio: float | None = None
    edges: list[str] = field(default_factory=list)
    detections: np.ndarray | None = None       # (n, 3): x, y, peak of every star peak found
    star_colors: np.ndarray | None = None      # (n, 3): x, y, colour index of measured stars
    centroid: tuple[float, float] = (0.5, 0.5)   # brightness centre of the subject, 0–1
    overlays: Overlays = field(default_factory=Overlays)
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------- helpers
def _bin2(a: np.ndarray) -> np.ndarray:
    h, w = (a.shape[-2] // 2) * 2, (a.shape[-1] // 2) * 2
    a = a[..., :h, :w]
    return 0.25 * (a[..., 0::2, 0::2] + a[..., 1::2, 0::2] + a[..., 0::2, 1::2]
                   + a[..., 1::2, 1::2])


def _tiles(img: np.ndarray, t: int) -> np.ndarray:
    """(gy, gx, t*t) view of complete tiles."""
    gy, gx = img.shape[0] // t, img.shape[1] // t
    a = img[: gy * t, : gx * t].reshape(gy, t, gx, t).swapaxes(1, 2)
    return a.reshape(gy, gx, t * t)


def _robust_std(a: np.ndarray, axis=-1) -> np.ndarray:
    med = np.median(a, axis=axis, keepdims=True)
    return MAD * np.median(np.abs(a - med), axis=axis)


def _is_linear(lum: np.ndarray, rgb: np.ndarray) -> bool:
    sample = lum[:: 7, :: 7]
    if float((rgb[:, ::7, ::7].min(axis=0) <= 1e-4).mean()) > 0.02:
        return False                           # clipped shadows: stretched, not linear
    med = float(np.median(sample))
    hi = float(np.percentile(sample, 99.5))
    return med < 0.04 and (hi - med) < 0.25 or med < 0.012


def _poly2(xs, ys, vals, iters: int = 3):
    """Robust 2nd-order surface fit. Returns coefficients and a callable."""
    def design(x, y):
        return np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], axis=-1)

    keep = np.ones(vals.shape, bool)
    coef = np.zeros(6)
    for _ in range(iters):
        if keep.sum() < 8:
            break
        coef, *_ = np.linalg.lstsq(design(xs[keep], ys[keep]), vals[keep], rcond=None)
        resid = vals - design(xs, ys) @ coef
        s = MAD * np.median(np.abs(resid[keep])) + 1e-9
        keep = np.abs(resid) < 2.5 * s
    return coef, lambda x, y: design(x, y) @ coef


# ---------------------------------------------------------------------------- main
def measure(pic: Picture, progress=None) -> Measurements:
    def step(text: str) -> None:
        if progress:
            progress(text)

    rgb = pic.rgb
    binned = 1
    while max(rgb.shape[1:]) > WORK_MAX_SIDE:
        rgb = _bin2(rgb)
        binned *= 2
    lum = (rgb[0] if pic.mono else
           (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])).astype(np.float32)
    m = Measurements(width=pic.width, height=pic.height, work_binned=binned, mono=pic.mono,
                     linear=_is_linear(lum, rgb), levels=pic.levels, jpeg_quality=pic.jpeg_quality)
    m.overlays.scale = float(binned)
    if m.linear:
        from advastro.display import auto_stretch

        rgb = auto_stretch(rgb, target_bkg=0.12, linked=True)
        lum = (rgb[0] if pic.mono else
               (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])).astype(np.float32)
        m.notes.append("linear")
    h, w = lum.shape

    step("background")
    _background(m, rgb, lum)
    step("noise")
    _noise(m, rgb, lum)
    step("tonality")
    _tonality(m, pic, rgb, lum)
    step("stars")
    star_mask = _stars(m, rgb, lum, binned)
    step("colour")
    if not pic.mono:
        _colour(m, rgb, lum, star_mask)
    step("detail")
    _detail(m, lum, star_mask)
    _edges(m, lum)
    _hot_pixels(m, rgb, lum)
    _walking_noise(m, lum, star_mask)
    m.star_area_pct = 100.0 * float(star_mask.mean()) if star_mask is not None else 0.0
    del h, w
    return m


# ---------------------------------------------------------------------------- background
def _background(m: Measurements, rgb: np.ndarray, lum: np.ndarray) -> None:
    h, w = lum.shape
    t = int(np.clip(min(h, w) // 22, 24, 192))
    tl = _tiles(lum, t)
    med = np.median(tl, axis=-1)
    hp = lum - ndi.uniform_filter(lum, 3)
    tnoise = _robust_std(_tiles(hp, t)) / 0.943
    gy, gx = med.shape
    # The darkest third of the frame, plus anything close to the sky level, is "sky".
    sky0 = float(np.percentile(med, 15))
    noise0 = float(np.median(tnoise)) + 1e-6
    bg = (med <= np.percentile(med, 33)) | (med < sky0 + 3 * noise0)
    m.background_fraction = float(bg.mean())
    m._bg_tiles = bg            # noqa: SLF001 (used by the next steps)
    m._tile = t
    m._tile_noise = tnoise
    m.sky = float(np.median(med[bg]))
    chans = [np.median(_tiles(c, t), axis=-1) for c in rgb]
    m.sky_rgb = tuple(float(np.median(c[bg])) for c in chans)
    mean_sky = float(np.mean(m.sky_rgb))
    m.cast_rgb = tuple(c - mean_sky for c in m.sky_rgb)
    m.green_excess = m.sky_rgb[1] - 0.5 * (m.sky_rgb[0] + m.sky_rgb[2])

    yy, xx = np.mgrid[0:gy, 0:gx]
    xs, ys = (xx + 0.5) / gx - 0.5, (yy + 0.5) / gy - 0.5
    coef, model = _poly2(xs[bg], ys[bg], med[bg])
    full = model(xs, ys)
    m.gradient_pct = 100.0 * float(full.max() - full.min())
    lin_c, *_ = np.linalg.lstsq(np.stack([np.ones(bg.sum()), xs[bg], ys[bg]], 1), med[bg],
                                rcond=None)
    m.plane_pct = 100.0 * float(abs(lin_c[1]) + abs(lin_c[2]))
    if abs(coef[1]) + abs(coef[2]) > 1e-9:
        m.gradient_angle = math.degrees(math.atan2(coef[2], coef[1])) % 360
    ranges = []
    cast_grid = np.zeros((gy, gx, 3), np.float32)
    for i, c in enumerate(chans):
        _, mod = _poly2(xs[bg], ys[bg], c[bg])
        cast_grid[..., i] = mod(xs, ys)
    if not m.mono:
        dev = cast_grid - cast_grid.mean(axis=-1, keepdims=True)
        ranges = [float(dev[..., i].max() - dev[..., i].min()) for i in range(3)]
        m.color_gradient_pct = 100.0 * max(ranges)
    m.overlays.background = (full - full.min()).astype(np.float32)
    m.overlays.noise = tnoise.astype(np.float32)
    local = np.stack([c - c.mean() for c in np.moveaxis(np.stack(chans, -1), -1, 0)], -1) \
        if not m.mono else None
    if local is not None:
        cast = np.stack(chans, -1) - np.stack(chans, -1).mean(axis=-1, keepdims=True)
        cast[~bg] = np.nan
        m.overlays.cast = cast.astype(np.float32)


# ---------------------------------------------------------------------------- noise
def _noise(m: Measurements, rgb: np.ndarray, lum: np.ndarray) -> None:
    bg, t = m._bg_tiles, m._tile
    m.noise = float(np.median(m._tile_noise[bg]))
    small = _bin2(lum)
    dog = ndi.gaussian_filter(small, 1.5) - ndi.gaussian_filter(small, 6.0)
    th = max(8, t // 2)
    dt = _robust_std(_tiles(dog, th))
    bg_small = np.zeros(dt.shape, bool)
    by = np.minimum((np.arange(dt.shape[0]) * th * 2 + th) // t, bg.shape[0] - 1)
    bx = np.minimum((np.arange(dt.shape[1]) * th * 2 + th) // t, bg.shape[1] - 1)
    bg_small = bg[np.ix_(by, bx)]
    m.noise_mid = float(np.median(dt[bg_small])) if bg_small.any() else 0.0
    # White noise of sigma s, binned 2x2 (s/2) then filtered: about 0.089 * s/2.
    white = 0.089 * 0.5 * max(m.noise, 1e-6)
    quant = (1.0 / (m.levels - 1)) * 0.29 if m.levels else 0.0
    m.mottle_ratio = float(m.noise_mid / max(white, quant * 0.089, 1e-6))
    if not m.mono:
        cr = rgb[0] - rgb[1]
        cb = rgb[2] - rgb[1]
        n = []
        for c in (cr, cb):
            hp = c - ndi.uniform_filter(c, 3)
            n.append(float(np.median((_robust_std(_tiles(hp, t)) / 0.943)[bg])))
        m.chroma_noise = float(np.hypot(*n) / math.sqrt(2))


# ---------------------------------------------------------------------------- tonality
def _tonality(m: Measurements, pic: Picture, rgb: np.ndarray, lum: np.ndarray) -> None:
    q = 1.0 / (m.levels - 1) if m.levels else 1e-4
    lo_thr = q * 0.5 + 1e-6
    hi_thr = 1.0 - max(q * 0.5, 1e-3)
    sample = lum[::3, ::3]
    m.p_low, m.p_high = (float(v) for v in np.percentile(sample, [0.5, 99.8]))
    m.contrast = float(np.percentile(sample, 99.0) - m.sky)
    black = (rgb <= lo_thr).any(axis=0)
    white = (rgb >= hi_thr).any(axis=0)
    m.black_clip_pct = 100.0 * float(black.mean())
    m.white_clip_pct = 100.0 * float(white.mean())
    if not m.mono:
        some = (rgb >= hi_thr) | (rgb <= lo_thr)
        cnt = some.sum(axis=0)
        m.channel_clip_pct = 100.0 * float(((cnt >= 1) & (cnt <= 2) & (lum > m.sky + 0.1)).mean())
    lab, n = ndi.label(white)
    if n:
        sizes = ndi.sum_labels(np.ones_like(lum), lab, index=np.arange(1, n + 1))
        # Star cores rarely exceed ~0.02 % of the frame; larger clipped blobs are structure.
        big = sizes > max(150.0, lum.size * 2e-4)
        m.extended_clip_px = int(sizes[big].sum() * m.work_binned ** 2)
        m.extended_clip_pct = 100.0 * float(sizes[big].sum() / lum.size)
    f = max(1, max(lum.shape) // 900)
    if f > 1:
        hh, ww = (lum.shape[0] // f) * f, (lum.shape[1] // f) * f
        m.overlays.clipped_white = white[:hh, :ww].reshape(hh // f, f, ww // f, f).any(axis=(1, 3))
        m.overlays.clipped_black = black[:hh, :ww].reshape(hh // f, f, ww // f, f).mean(
            axis=(1, 3)) > 0.5
    else:
        m.overlays.clipped_white, m.overlays.clipped_black = white, black

    # Banding: in smooth sky, quantization steps form flat plateaus.
    if m.levels and m.levels <= 4096:
        steps = np.round(lum * (m.levels - 1))
        same = (steps[1:-1, 1:-1] == steps[:-2, 1:-1]) & (steps[1:-1, 1:-1] == steps[2:, 1:-1]) & \
               (steps[1:-1, 1:-1] == steps[1:-1, :-2]) & (steps[1:-1, 1:-1] == steps[1:-1, 2:])
        sky_px = (lum[1:-1, 1:-1] < m.sky + 4 * m.noise + 2 * q) & \
                 (lum[1:-1, 1:-1] > m.sky - 4 * m.noise - 2 * q)
        if sky_px.any():
            m.plateau_pct = 100.0 * float(same[sky_px].mean())
        # Combing: gaps in the histogram inside the used range (8-bit data stretched again).
        bins = min(m.levels, 256)
        combs = []
        for c in (rgb if not m.mono else rgb[:1]):
            hist = np.bincount(np.clip(np.round(c[::2, ::2] * (bins - 1)).astype(np.int32),
                                       0, bins - 1).ravel(), minlength=bins)
            cum = np.cumsum(hist) / hist.sum()
            a, b = int(np.searchsorted(cum, 0.01)), int(np.searchsorted(cum, 0.995))
            if b - a > 8:
                combs.append(float((hist[a:b] == 0).mean()))
        m.comb_pct = 100.0 * max(combs) if combs else 0.0

    if pic.format in ("jpeg", "jpg", "mpo"):
        g = lum * 255.0
        dx = np.abs(np.diff(g, axis=1))
        dy = np.abs(np.diff(g, axis=0))
        bx = dx[:, 7::8].mean() / max(1e-6, np.delete(dx, np.s_[7::8], axis=1).mean())
        by = dy[7::8, :].mean() / max(1e-6, np.delete(dy, np.s_[7::8], axis=0).mean())
        m.blockiness = float(0.5 * (bx + by))


# ---------------------------------------------------------------------------- stars
def _stars(m: Measurements, rgb: np.ndarray, lum: np.ndarray, binned: int):
    h, w = lum.shape
    t = m._tile
    med = np.median(_tiles(lum, t), axis=-1)
    # Local background: tile medians, smoothly interpolated, then a light median polish.
    bkg = ndi.zoom(ndi.median_filter(med, size=3, mode="nearest"),
                   (h / med.shape[0], w / med.shape[1]), order=1, mode="nearest")
    bkg = np.pad(bkg, ((0, max(0, h - bkg.shape[0])), (0, max(0, w - bkg.shape[1]))),
                 mode="edge")[:h, :w]
    bsub = lum - bkg
    noise = max(m.noise, 0.6 / 255 if m.levels and m.levels <= 256 else 1e-4)
    sm = ndi.gaussian_filter(bsub, 1.0)
    thr = max(6.0 * noise * 0.45, 0.02)
    peaks = (sm == ndi.maximum_filter(sm, size=5)) & (sm > thr)
    ys, xs = np.nonzero(peaks)
    if ys.size == 0:
        return np.zeros_like(lum, bool)
    vals = sm[ys, xs]
    order = np.argsort(vals)[::-1][:40000]
    ys, xs, vals = ys[order], xs[order], vals[order]
    m.detections = np.column_stack([xs, ys, vals]).astype(np.float32)
    m.star_count = int(ys.size)
    ys, xs, vals = ys[:12000], xs[:12000], vals[:12000]
    m.star_density = m.star_count / (h * w * binned * binned / 1e6)

    # First pass: typical size from moderately bright stars, to size the cutouts.
    r = 9
    keep = (ys >= r) & (ys < h - r) & (xs >= r) & (xs < w - r)
    ys, xs, vals = ys[keep], xs[keep], vals[keep]
    est = _measure_cutouts(lum, rgb, bsub, ys[:400], xs[:400], r, noise)
    typical = float(np.nanmedian(est["fwhm"][~est["saturated"]])) if est["fwhm"].size else 3.0
    if not np.isfinite(typical):
        typical = 3.0
    r = int(np.clip(round(typical * 3.2), 7, 30))
    keep = (ys >= r) & (ys < h - r) & (xs >= r) & (xs < w - r)
    ys, xs, vals = ys[keep], xs[keep], vals[keep]
    # Isolation: no brighter neighbour inside the cutout.
    if ys.size > 1:
        tree = cKDTree(np.column_stack([xs, ys]))
        pairs = tree.query_pairs(r * 0.8, output_type="ndarray")
        crowded = np.zeros(ys.size, bool)
        if pairs.size:
            crowded[np.maximum(pairs[:, 0], pairs[:, 1])] = True  # sorted by brightness
        ys, xs, vals = ys[~crowded], xs[~crowded], vals[~crowded]
    ys, xs = ys[:4000], xs[:4000]
    s = _measure_cutouts(lum, rgb, bsub, ys, xs, r, noise)
    ok = np.isfinite(s["fwhm"]) & (s["fwhm"] > 0.8) & (s["fwhm"] < r * 1.4)
    if ok.sum() < 5:
        return np.zeros_like(lum, bool)
    for k in s:
        s[k] = s[k][ok]
    # Real stars are small, round and clearly brighter than the noise; what a star
    # removal tool leaves behind (and nebula texture) is large or faint.
    compact = (s["fwhm"] < 6.0) & (s["peak"] > 10 * noise) & (s["ellipticity"] < 0.35)
    m.compact_sources = int(compact.sum())
    m.compact_density = m.compact_sources / (h * w * binned * binned / 1e6)
    m.bright_sources = int((s["peak"] > max(0.12, 20 * noise)).sum())
    xs_f, ys_f = s["x"], s["y"]
    has_ci = np.isfinite(s["ci"])
    m.star_colors = np.column_stack([xs_f[has_ci], ys_f[has_ci], s["ci"][has_ci]]).astype(
        np.float32)
    sat = s["saturated"]
    unsat = ~sat & (s["peak"] > 6 * noise)
    pick = unsat if unsat.sum() >= 10 else np.ones_like(sat)
    fw = s["fwhm"][pick] * binned
    m.fwhm = float(np.median(fw))
    m.ellipticity = float(np.median(s["ellipticity"][pick]))
    ang2 = 2 * s["angle"][pick]
    wts = s["ellipticity"][pick]
    if wts.sum() > 0:
        m.orientation_coherence = float(np.hypot((wts * np.cos(ang2)).sum(),
                                                 (wts * np.sin(ang2)).sum()) / wts.sum())
    bright = np.argsort(s["peak"] + 10 * sat)[::-1][: max(5, len(sat) // 50)]
    m.fwhm_bright = float(np.median(s["core"][bright])) * binned

    # Field map: 3x3 regions.
    gx = np.clip((xs_f / w * 3).astype(int), 0, 2)
    gy = np.clip((ys_f / h * 3).astype(int), 0, 2)
    fg = np.full((3, 3), np.nan)
    eg = np.full((3, 3), np.nan)
    for j in range(3):
        for i in range(3):
            sel = pick & (gx == i) & (gy == j)
            if sel.sum() >= 4:
                fg[j, i] = np.median(s["fwhm"][sel]) * binned
                eg[j, i] = np.median(s["ellipticity"][sel])
    m.fwhm_grid, m.ellipticity_grid = fg, eg
    corners = [fg[0, 0], fg[0, 2], fg[2, 0], fg[2, 2]]
    if np.isfinite(fg[1, 1]) and np.isfinite(corners).sum() >= 3:
        m.corner_ratio = float(np.nanmean(corners) / fg[1, 1])
        m.tilt_ratio = float(np.nanmax(corners) / np.nanmin(corners))
    # Radial or tangential elongation in the outer field (coma vs astigmatism).
    cx, cy = w / 2, h / 2
    rad = np.hypot(xs_f - cx, ys_f - cy) / math.hypot(cx, cy)
    outer = pick & (rad > 0.65) & (s["ellipticity"] > 0.12)
    if outer.sum() >= 8:
        phi = np.arctan2(ys_f[outer] - cy, xs_f[outer] - cx)
        m.radial_alignment = float(np.mean(np.cos(2 * (s["angle"][outer] - phi))))
    # Rings around bright stars (sharpening / deconvolution).
    candidates = s["peak"] > 0.25
    if candidates.sum() >= 5:
        m.ring_fraction = float(s["ring"][candidates].mean())
    if not m.mono:
        ci = s["ci"][pick & np.isfinite(s["ci"])]
        if ci.size >= 10:
            m.color_spread = float(np.std(np.clip(ci, -1.5, 1.5)))
        gm = s["gmag"][pick & np.isfinite(s["gmag"])]
        if gm.size >= 10:
            m.magenta_fraction = float((gm < 0.85).mean())
        if sat.sum() >= 5:
            m.white_cores = float(s["white_core"][sat].mean())
        fr = s["fringe"][np.isfinite(s["fringe"])]
        if fr.size >= 10:
            m.fringe = float(np.median(fr)) * binned
        out2 = (rad > 0.6) & np.isfinite(s["lat_ca"])
        if out2.sum() >= 10:
            m.lateral_ca = float(np.median(s["lat_ca"][out2])) * binned

    # Overlays: a spread-out subset, and a smooth FWHM map.
    idx = np.argsort(-s["peak"])
    chosen = idx[np.linspace(0, len(idx) - 1, min(len(idx), 600)).astype(int)]
    m.overlays.stars = [
        StarSample(float(s["x"][i]), float(s["y"][i]), float(s["fwhm"][i]),
                   float(s["ellipticity"][i]), float(s["angle"][i]), float(s["peak"][i]),
                   bool(s["saturated"][i]), bool(s["ring"][i]),
                   float(s["ci"][i]) if np.isfinite(s["ci"][i]) else None) for i in chosen]
    m.overlays.rings = [(float(s["x"][i]), float(s["y"][i]), float(s["core"][i]))
                        for i in np.nonzero(s["ring"])[0][:300]]
    gyn, gxn = 6, max(3, round(6 * w / h))
    grid = np.full((gyn, gxn), np.nan)
    gi = np.clip((xs_f / w * gxn).astype(int), 0, gxn - 1)
    gj = np.clip((ys_f / h * gyn).astype(int), 0, gyn - 1)
    for j in range(gyn):
        for i in range(gxn):
            sel = pick & (gi == i) & (gj == j)
            if sel.sum() >= 3:
                grid[j, i] = np.median(s["fwhm"][sel]) * binned
    m.overlays.fwhm_map = grid

    # Star mask for colour and detail measurements.
    mask = np.zeros_like(lum, bool)
    rad_px = np.clip(s["core"] * 1.3 + 1.5, 2, r)
    for x, y, rr in zip(s["x"], s["y"], rad_px, strict=False):
        x0, x1 = int(max(0, x - rr)), int(min(w, x + rr + 1))
        y0, y1 = int(max(0, y - rr)), int(min(h, y + rr + 1))
        mask[y0:y1, x0:x1] = True
    # Stars not measured (crowded) still count: mark their peaks generously.
    mask[ndi.binary_dilation(peaks, iterations=max(2, int(typical)))] = True
    return mask


def _measure_cutouts(lum, rgb, bsub, ys, xs, r, noise) -> dict:
    n = len(ys)
    out = {k: np.full(n, np.nan) for k in ("x", "y", "fwhm", "ellipticity", "angle", "peak",
                                           "core", "ci", "gmag", "fringe", "lat_ca")}
    out["saturated"] = np.zeros(n, bool)
    out["ring"] = np.zeros(n, bool)
    out["white_core"] = np.zeros(n, bool)
    if n == 0:
        return out
    oy, ox = np.mgrid[-r:r + 1, -r:r + 1]
    iy = ys[:, None, None] + oy[None]
    ix = xs[:, None, None] + ox[None]
    cut = bsub[iy, ix]                                    # (n, k, k)
    raw = rgb[:, iy, ix]                                  # (3, n, k, k)
    dist = np.hypot(oy, ox)
    ring_out = dist > r - 2
    local_bg = np.median(cut[:, ring_out], axis=1)
    c = cut - local_bg[:, None, None]
    peak = c[:, r - 1:r + 2, r - 1:r + 2].max(axis=(1, 2))
    sat = (raw.max(axis=0) >= 0.985).reshape(n, -1).sum(axis=1) >= 2
    half = c > 0.5 * peak[:, None, None]
    # Only the connected core around the centre: restrict to a disc that grows with size.
    area = (half & (dist[None] <= r - 1)).sum(axis=(1, 2)).astype(float)
    fwhm = 2.0 * np.sqrt(area / math.pi)
    # Moments of the part above half maximum.
    wgt = np.where(half, c - 0.5 * peak[:, None, None], 0.0)
    sw = wgt.sum(axis=(1, 2)) + 1e-12
    mx = (wgt * ox).sum(axis=(1, 2)) / sw
    my = (wgt * oy).sum(axis=(1, 2)) / sw
    dx, dy = ox[None] - mx[:, None, None], oy[None] - my[:, None, None]
    sxx = (wgt * dx * dx).sum(axis=(1, 2)) / sw
    syy = (wgt * dy * dy).sum(axis=(1, 2)) / sw
    sxy = (wgt * dx * dy).sum(axis=(1, 2)) / sw
    tr_, det = sxx + syy, sxx * syy - sxy * sxy
    disc = np.sqrt(np.maximum(tr_ * tr_ / 4 - det, 0))
    l1, l2 = tr_ / 2 + disc, np.maximum(tr_ / 2 - disc, 1e-9)
    ell = 1 - np.sqrt(l2 / np.maximum(l1, 1e-9))
    angle = 0.5 * np.arctan2(2 * sxy, sxx - syy)
    # Core size of saturated stars: the clipped / near-white area.
    core_area = (raw.max(axis=0) >= 0.9 * raw.max(axis=0).max(axis=(1, 2))[:, None, None]
                 ).sum(axis=(1, 2))
    core = np.where(sat, 2 * np.sqrt(core_area / math.pi), fwhm)
    # Radial profile for rings: mean in annuli of 1 px.
    rbin = np.minimum(dist.astype(int), r)
    prof = np.stack([c[:, rbin == i].mean(axis=1) for i in range(r + 1)], axis=1)
    ring = np.zeros(n, bool)
    for i in range(n):
        f = fwhm[i]
        if not np.isfinite(f) or peak[i] < 0.2:
            continue
        a, b = int(max(1, round(f * 0.8))), int(min(r - 2, round(f * 2.5) + 1))
        if b > a:
            dip = prof[i, a:b].min()
            ring[i] = dip < -max(4 * noise, 0.025 * peak[i])
    # Colours from aperture sums.
    ap = dist[None] <= np.maximum(fwhm, 1.5)[:, None, None] * 1.2
    bgc = np.median(raw[:, :, ring_out], axis=2)          # (3, n)
    flux = ((raw - bgc[:, :, None, None]) * ap[None]).sum(axis=(2, 3))  # (3, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        good = (flux[0] > 0) & (flux[2] > 0) & ~sat & (peak > 6 * noise)
        ci = np.where(good, -2.5 * np.log10(flux[2] / flux[0]), np.nan)
        gmag = np.where(good & (flux[1] > 0), flux[1] / (0.5 * (flux[0] + flux[2])), np.nan)
        # Fringe: blue vs red half-maximum radius.
        hr = []
        for ch in (0, 2):
            cc = raw[ch] - bgc[ch][:, None, None]
            pk = cc[:, r - 1:r + 2, r - 1:r + 2].max(axis=(1, 2))
            hr.append(np.sqrt((cc > 0.5 * pk[:, None, None]).sum(axis=(1, 2)) / math.pi))
        fringe = np.where(good, hr[1] - hr[0], np.nan)
        # Lateral colour: red vs blue centroid shift.
        cen = []
        for ch in (0, 2):
            cc = np.clip(raw[ch] - bgc[ch][:, None, None], 0, None) * ap
            s_ = cc.sum(axis=(1, 2)) + 1e-12
            cen.append(((cc * ox).sum(axis=(1, 2)) / s_, (cc * oy).sum(axis=(1, 2)) / s_))
        lat = np.where(good, np.hypot(cen[0][0] - cen[1][0], cen[0][1] - cen[1][1]), np.nan)
    white_core = sat & ((raw >= 0.97).reshape(3, n, -1).all(axis=0).sum(axis=1) >= 1)
    out.update(x=xs + mx, y=ys + my, fwhm=fwhm, ellipticity=ell, angle=angle, peak=peak,
               core=core, ci=ci, gmag=gmag, fringe=fringe, lat_ca=lat)
    out["saturated"], out["ring"], out["white_core"] = sat, ring, white_core
    return out


# ---------------------------------------------------------------------------- colour
def _colour(m: Measurements, rgb: np.ndarray, lum: np.ndarray, star_mask) -> None:
    smooth = ndi.uniform_filter(lum, 5)
    sig = smooth > m.sky + max(8 * m.noise, 0.06)
    if star_mask is not None:
        sig &= ~star_mask
    m.signal_fraction = float(sig.mean())
    if sig.sum() < 500:
        return
    sub = rgb[:, sig]
    mx, mn = sub.max(axis=0), sub.min(axis=0)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    m.saturation = float(np.median(sat))
    m.saturation_high_pct = 100.0 * float((sat > 0.85).mean())
    ys, xs = np.nonzero(sig)
    wts = np.clip(lum[sig] - m.sky, 0, None)
    if wts.sum() > 0:
        m.centroid = (float((xs * wts).sum() / wts.sum() / lum.shape[1]),
                      float((ys * wts).sum() / wts.sum() / lum.shape[0]))


# ---------------------------------------------------------------------------- detail
def _detail(m: Measurements, lum: np.ndarray, star_mask) -> None:
    dog = ndi.gaussian_filter(lum, 0.8) - ndi.gaussian_filter(lum, 2.4)
    smooth = ndi.uniform_filter(lum, 9)
    sig = smooth > m.sky + max(10 * m.noise, 0.08)
    bg = smooth < m.sky + 2 * m.noise
    if star_mask is not None:
        sig &= ~star_mask
        bg &= ~star_mask
    if sig.sum() > 2000 and bg.sum() > 2000:
        s_sig = float(np.std(dog[sig]))
        s_bg = MAD * float(np.median(np.abs(dog[bg] - np.median(dog[bg])))) + 1e-6
        m.detail_ratio = s_sig / s_bg
    if m.signal_fraction == 0.0:
        m.signal_fraction = float(sig.mean())
        if sig.any() and m.mono:
            ys, xs = np.nonzero(sig)
            wts = np.clip(lum[sig] - m.sky, 0, None)
            if wts.sum() > 0:
                m.centroid = (float((xs * wts).sum() / wts.sum() / lum.shape[1]),
                              float((ys * wts).sum() / wts.sum() / lum.shape[0]))


# ---------------------------------------------------------------------------- edges
def _edges(m: Measurements, lum: np.ndarray) -> None:
    h, w = lum.shape
    q = 1.0 / (m.levels - 1) if m.levels else 1e-4
    sides = {
        "top": (lum[: max(3, h // 100)], lum[max(3, h // 100) * 2: max(3, h // 100) * 6]),
        "bottom": (lum[-max(3, h // 100):], lum[-max(3, h // 100) * 6: -max(3, h // 100) * 2]),
        "left": (lum[:, : max(3, w // 100)], lum[:, max(3, w // 100) * 2: max(3, w // 100) * 6]),
        "right": (lum[:, -max(3, w // 100):], lum[:, -max(3, w // 100) * 6: -max(3, w // 100) * 2]),
    }
    for name, (strip, inner) in sides.items():
        dark = float((strip <= q + 1e-6).mean())
        sm, im = float(np.median(strip)), float(np.median(inner))
        sn = float(_robust_std((strip - ndi.uniform_filter(strip, 3)).ravel()))
        inn = float(_robust_std((inner - ndi.uniform_filter(inner, 3)).ravel())) + 1e-6
        const = float(np.std(strip)) < 1e-5 and abs(sm - im) > 0.01
        if dark > 0.3 or const or abs(sm - im) > max(6 * m.noise, 0.03) or \
                (sn > 1.8 * inn and sn > 3 * q):
            m.edges.append(name)
    m.overlays.edges = list(m.edges)


# ---------------------------------------------------------------------------- hot pixels
def _hot_pixels(m: Measurements, rgb: np.ndarray, lum: np.ndarray) -> None:
    fp = np.ones((3, 3), bool)
    fp[1, 1] = False
    thr = max(10 * m.noise, 0.12)
    hits = np.zeros(lum.shape, bool)
    for c in (rgb if not m.mono else rgb[:1]):
        neigh = ndi.maximum_filter(c, footprint=fp, mode="nearest")
        cand = (c - neigh) > thr
        if not cand.any():
            continue
        # A hot pixel stands alone: its neighbours sit near the local background.
        # A star (even a sharpened one) has bright neighbours.
        ys, xs = np.nonzero(cand)
        local = ndi.median_filter(c, size=5, mode="nearest")[ys, xs]
        lift = c[ys, xs] - local
        # Even a very sharp star (FWHM 1.2 px) puts ~15 % of its peak into the brightest
        # neighbour and lifts the ring around it; a hot pixel lifts neither.
        ring_mean = ndi.uniform_filter(c, 3, mode="nearest")[ys, xs] * 9 / 8 - c[ys, xs] / 8
        alone = ((neigh[ys, xs] - local) < 0.12 * lift) & \
                ((ring_mean - local) < max(2.5 * m.noise, 0.04 * float(np.median(lift))))
        hits[ys[alone], xs[alone]] = True
    ys, xs = np.nonzero(hits)
    m.hot_pixels = int(ys.size)
    m.overlays.hot_pixels = list(zip(xs[:500].tolist(), ys[:500].tolist(), strict=False))


# ---------------------------------------------------------------------------- walking noise
def _walking_noise(m: Measurements, lum: np.ndarray, star_mask) -> None:
    if m.background_fraction < 0.25:
        return
    small = _bin2(lum)
    g = ndi.gaussian_filter(small, 1.5) - ndi.gaussian_filter(small, 10)
    t = m._tile
    bg = np.repeat(np.repeat(m._bg_tiles, t // 2, axis=0), t // 2, axis=1)
    bg = np.pad(bg, ((0, max(0, small.shape[0] - bg.shape[0])),
                     (0, max(0, small.shape[1] - bg.shape[1]))))[: small.shape[0], : small.shape[1]]
    wgt = ndi.gaussian_filter(bg.astype(np.float32), 6)
    if star_mask is not None:
        sm = _bin2(star_mask.astype(np.float32)) > 0
        wgt[sm[: wgt.shape[0], : wgt.shape[1]]] = 0
    n = min(small.shape)
    n = 2 ** int(math.log2(n))
    if n < 128:
        return
    cy, cx = small.shape[0] // 2, small.shape[1] // 2
    patch = (g * wgt)[cy - n // 2: cy + n // 2, cx - n // 2: cx + n // 2]
    win = np.outer(np.hanning(n), np.hanning(n))
    p = np.abs(np.fft.fftshift(np.fft.fft2(patch * win))) ** 2
    fy, fx = np.mgrid[-n // 2: n // 2, -n // 2: n // 2]
    rr = np.hypot(fx, fy)
    ang = (np.degrees(np.arctan2(fy, fx)) + 180) % 180
    ring = (rr > n / 40) & (rr < n / 6)
    bins = np.linspace(0, 180, 37)
    power = np.array([p[ring & (ang >= a) & (ang < b)].mean() for a, b in zip(bins[:-1], bins[1:],
                                                                                strict=False)])
    centres = 0.5 * (bins[:-1] + bins[1:])
    axis = (np.abs(centres - 0) < 6) | (np.abs(centres - 90) < 6) | (np.abs(centres - 180) < 6)
    valid = power[~axis]
    if valid.size and np.median(valid) > 0:
        best = int(np.argmax(np.where(axis, 0, power)))
        m.walking_noise = float(power[best] / np.median(valid))
        # Streaks run perpendicular to their spectral line.
        m.walking_angle = float((centres[best] + 90) % 180)
