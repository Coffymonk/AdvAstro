"""Calibration frames: bias, darks, flats and flat darks.

Each frame type gets the measurements that matter for it:

  bias, darks, flat darks   level, read/thermal noise, hot pixels, amp glow, banding
  flats                     level per colour channel, clipping, vignetting, dust shadows

Then each group is checked for consistency (an odd frame is flagged like an odd
light), and against the lights: do the darks match the lights' exposure, gain,
offset and temperature; do the flat darks match the flats; are the flats from
the same night?
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import ndimage

from advastro.engine.session import SubFlag
from advastro.frame import Frame, FrameMeta
from advastro.readers import read_frame

KINDS = ("bias", "darks", "flats", "darkflats")
HEADER_KIND = {"bias": "bias", "dark": "darks", "flat": "flats", "darkflat": "darkflats"}
_REGIONS = {  # name: (row slice, col slice) as fractions of the frame
    "top left": ((0.0, 0.12), (0.0, 0.12)), "top right": ((0.0, 0.12), (0.88, 1.0)),
    "bottom left": ((0.88, 1.0), (0.0, 0.12)), "bottom right": ((0.88, 1.0), (0.88, 1.0)),
    "left edge": ((0.4, 0.6), (0.0, 0.06)), "right edge": ((0.4, 0.6), (0.94, 1.0)),
    "top edge": ((0.0, 0.06), (0.4, 0.6)), "bottom edge": ((0.94, 1.0), (0.4, 0.6)),
}


@dataclass
class CalMetrics:
    file: str
    path: str
    kind: str                     # bias | darks | flats | darkflats
    is_master: bool
    header_type: str | None
    time: str | None
    exposure_s: float | None
    gain: float | None
    offset: float | None
    temperature_c: float | None
    binning: int | None
    width: int
    height: int
    filter: str | None
    median_adu: float
    noise_adu: float | None = None
    hot_pixels: int | None = None
    hot_pct: float | None = None
    glow_adu: float | None = None
    glow_where: str | None = None
    banding_adu: float | None = None
    level_pct: float | None = None
    channel_levels: list[float] | None = None
    clipped_pct: float | None = None
    vignetting_pct: float | None = None
    dust_spots: int | None = None
    dust_depth_pct: float | None = None
    saturation_adu: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CalNote:
    level: str     # good | info | warn | bad
    kind: str      # which group it is about, or "session"
    text: str


@dataclass
class CalGroup:
    kind: str
    frames: list[CalMetrics]
    masters: list[CalMetrics] = field(default_factory=list)
    flags: list[SubFlag] = field(default_factory=list)
    medians: dict[str, float | None] = field(default_factory=dict)

    def flagged_files(self) -> set[str]:
        return {f.file for f in self.flags}

    def setting(self, attr: str):
        """The most common value of a setting across the group's frames."""
        values = [getattr(m, attr) for m in self.frames if getattr(m, attr) is not None]
        return Counter(values).most_common(1)[0][0] if values else None


@dataclass
class CalibrationSummary:
    groups: dict[str, CalGroup]
    notes: list[CalNote]
    errors: dict[str, str] = field(default_factory=dict)

    def group(self, kind: str) -> CalGroup | None:
        return self.groups.get(kind)

    def count(self, kind: str) -> int:
        g = self.groups.get(kind)
        return len(g.frames) + len(g.masters) if g else 0


# ---------------------------------------------------------------- measurement ----
def _robust_noise(data: np.ndarray, rng_seed: int = 0) -> tuple[float, float]:
    """Median and sigma-clipped standard deviation from a random subsample.

    A clipped standard deviation (not the MAD) is used because many cameras scale a
    12-bit ADC to 16 bits: values come in steps of 16 ADU, and the MAD then gets
    stuck at exactly one step.
    """
    flat = data.ravel()
    if flat.size > 600_000:
        idx = np.random.default_rng(rng_seed).integers(0, flat.size, 600_000)
        flat = flat[idx]
    sample = flat.astype(np.float64)
    med = float(np.median(sample))
    std = float(np.std(sample))
    for _ in range(5):
        keep = np.abs(sample - med) < 3.0 * std
        if keep.all():
            break
        sample = sample[keep]
        med, std = float(np.median(sample)), float(np.std(sample))
    return med, std


def _region(data: np.ndarray, rows: tuple[float, float], cols: tuple[float, float]):
    h, w = data.shape[-2:]
    return data[..., int(rows[0] * h):max(int(rows[1] * h), int(rows[0] * h) + 1),
                int(cols[0] * w):max(int(cols[1] * w), int(cols[0] * w) + 1)]


def _dark_like(m: CalMetrics, data: np.ndarray) -> None:
    med, noise = _robust_noise(data)
    m.median_adu, m.noise_adu = med, noise
    # Hot pixels stand out from their local surroundings (so amp glow is not counted).
    block = 32
    h, w = (data.shape[0] // block) * block, (data.shape[1] // block) * block
    local = np.median(data[:h, :w].reshape(h // block, block, w // block, block)
                      .transpose(0, 2, 1, 3).reshape(h // block, w // block, -1), axis=2)
    background = np.repeat(np.repeat(local, block, axis=0), block, axis=1)
    hot = int(np.count_nonzero(data[:h, :w] - background > max(10.0 * noise, 1.0)))
    m.hot_pixels, m.hot_pct = hot, hot / data.size * 100.0

    center = float(np.median(_region(data, (0.4, 0.6), (0.4, 0.6))))
    best, where = 0.0, None
    for name, (rows, cols) in _REGIONS.items():
        level = float(np.median(_region(data, rows, cols))) - center
        if level > best:
            best, where = level, name
    m.glow_adu, m.glow_where = best, where

    # Banding: row and column medians after removing slow variation.
    step = max(1, data.shape[1] // 1024)
    rows = np.median(data[:, ::step], axis=1)
    cols = np.median(data[::step, :], axis=0)
    band = 0.0
    for profile in (rows, cols):
        smooth = ndimage.median_filter(profile, size=31, mode="nearest")
        band = max(band, float(np.std(profile - smooth)))
    m.banding_adu = band


def _superpixels(frame: Frame) -> np.ndarray:
    """(channels, h, w): R, G, B superpixels for colour data, one plane for mono."""
    data = frame.data
    if data.ndim == 3:
        return data
    pattern = frame.meta.bayer_pattern
    if not pattern:
        return data[None]
    from advastro.display import _CFA_OFFSETS

    h, w = (data.shape[0] // 2) * 2, (data.shape[1] // 2) * 2
    d = data[:h, :w]
    (rr, rc), (g1r, g1c), (g2r, g2c), (br, bc) = _CFA_OFFSETS[pattern]
    return np.stack([d[rr::2, rc::2], 0.5 * (d[g1r::2, g1c::2] + d[g2r::2, g2c::2]),
                     d[br::2, bc::2]])


def _flat(m: CalMetrics, frame: Frame, sat: float) -> None:
    channels = _superpixels(frame)
    levels = [float(np.median(c)) for c in channels]
    m.channel_levels = levels
    m.median_adu = float(np.median(frame.data))
    m.level_pct = max(levels) / sat * 100.0
    m.clipped_pct = float(np.count_nonzero(frame.data >= 0.98 * sat)) / frame.data.size * 100

    lum = channels.mean(axis=0)
    factor = max(1, int(np.ceil(max(lum.shape) / 960)))
    h, w = (lum.shape[0] // factor) * factor, (lum.shape[1] // factor) * factor
    small = lum[:h, :w].reshape(h // factor, factor, w // factor, factor).mean(axis=(1, 3))

    center = float(np.median(_region(small, (0.4, 0.6), (0.4, 0.6))))
    corners = [float(np.median(_region(small, r, c))) for name, (r, c) in _REGIONS.items()
               if name.split()[0] in ("top", "bottom") and "edge" not in name]
    m.vignetting_pct = max(0.0, (1.0 - float(np.mean(corners)) / center) * 100.0) \
        if center > 0 else None

    # Dust shadows: small dark rings or spots against the smooth illumination.
    smooth = ndimage.gaussian_filter(small, sigma=max(small.shape) / 40)
    ratio = small / np.maximum(smooth, 1e-6)
    border = max(4, int(0.04 * max(small.shape)))
    inner = np.zeros_like(ratio, dtype=bool)
    inner[border:-border, border:-border] = True
    mask = (ratio < 0.985) & inner
    labels, n = ndimage.label(mask)
    if n:
        sizes = ndimage.sum_labels(mask, labels, index=np.arange(1, n + 1))
        depths = ndimage.minimum(ratio, labels, index=np.arange(1, n + 1))
        real = (sizes >= 12) & (sizes <= 0.02 * small.size)
        m.dust_spots = int(np.count_nonzero(real))
        m.dust_depth_pct = float((1.0 - np.min(depths[real])) * 100.0) if real.any() else 0.0
    else:
        m.dust_spots, m.dust_depth_pct = 0, 0.0


def measure_calibration(frame: Frame, kind: str) -> CalMetrics:
    meta: FrameMeta = frame.meta
    sat = meta.saturation_adu or float(np.max(frame.data)) or 1.0
    name = frame.path.name
    m = CalMetrics(
        file=name, path=str(frame.path), kind=kind,
        is_master="master" in name.lower(),
        header_type=meta.image_type, time=meta.date_obs.isoformat() if meta.date_obs else None,
        exposure_s=meta.exposure_s, gain=meta.gain, offset=meta.offset,
        temperature_c=meta.temperature_c, binning=meta.binning,
        width=int(frame.data.shape[-1]), height=int(frame.data.shape[-2]),
        filter=meta.filter_name, median_adu=0.0, saturation_adu=sat)
    data = frame.data if frame.data.ndim == 2 else frame.data.mean(axis=0)
    if kind == "flats":
        _flat(m, frame, sat)
    else:
        _dark_like(m, data)
    return m


def _measure(path: str, kind: str) -> CalMetrics:
    return measure_calibration(read_frame(path), kind)


# ------------------------------------------------------------------ analysis ----
def analyze_calibration(files: dict[str, list[Path]], jobs: int | None = None,
                        progress=None, on_result=None, should_stop=None
                        ) -> tuple[list[CalMetrics], dict[str, str]]:
    """Measure every calibration frame, in parallel like the lights."""
    import multiprocessing
    from concurrent.futures import ProcessPoolExecutor, as_completed

    items = [(str(p), kind) for kind in KINDS for p in files.get(kind, [])]
    results: list[CalMetrics] = []
    errors: dict[str, str] = {}
    stop = should_stop or (lambda: False)

    def handle(i, path, get):
        try:
            m = get()
            results.append(m)
            if on_result:
                on_result(m)
        except Exception as exc:
            errors[Path(path).name] = str(exc)
        if progress:
            progress(i, len(items), Path(path).name)

    if jobs == 1 or len(items) <= 1:
        for i, (p, k) in enumerate(items, 1):
            if stop():
                break
            handle(i, p, lambda p=p, k=k: _measure(p, k))
    else:
        pool = ProcessPoolExecutor(max_workers=jobs,
                                   mp_context=multiprocessing.get_context("spawn"))
        try:
            futures = {pool.submit(_measure, p, k): p for p, k in items}
            for i, fut in enumerate(as_completed(futures), 1):
                if stop():
                    break
                handle(i, futures[fut], fut.result)
        finally:
            pool.shutdown(wait=not stop(), cancel_futures=True)
    return results, errors


def _median(values) -> float | None:
    v = [x for x in values if x is not None]
    return float(np.median(v)) if v else None


def _group(kind: str, metrics: list[CalMetrics]) -> CalGroup:
    frames = sorted((m for m in metrics if not m.is_master), key=lambda m: m.file)
    masters = [m for m in metrics if m.is_master]
    g = CalGroup(kind, frames, masters)
    for attr in ("median_adu", "noise_adu", "hot_pixels", "hot_pct", "glow_adu",
                 "banding_adu", "level_pct", "clipped_pct", "vignetting_pct", "dust_spots",
                 "dust_depth_pct"):
        g.medians[attr] = _median(getattr(m, attr) for m in frames)
    if len(frames) < 3:
        return g

    # Settings that differ from the rest of the group
    for attr, label, tol in (("exposure_s", "exposure", 0.01), ("gain", "gain", 0.0),
                             ("offset", "offset", 0.0), ("binning", "binning", 0.0),
                             ("temperature_c", "temperature", 1.5)):
        common = g.setting(attr) if attr != "temperature_c" else g.medians.get("_t") \
            or _median(m.temperature_c for m in frames)
        if common is None:
            continue
        for m in frames:
            v = getattr(m, attr)
            if v is None:
                continue
            limit = tol * abs(common) if attr == "exposure_s" else tol
            if abs(v - common) > limit:
                g.flags.append(SubFlag(m.file, attr, float(v), float(common),
                                       f"{label} {v:g} differs from the rest ({common:g})"))
    for m in frames:
        if (m.width, m.height) != (frames[0].width, frames[0].height) and \
                Counter((f.width, f.height) for f in frames).most_common(1)[0][0] != \
                (m.width, m.height):
            g.flags.append(SubFlag(m.file, "size", m.width, frames[0].width,
                                   f"size {m.width}×{m.height} differs from the rest"))

    # Level outliers
    levels = np.array([m.median_adu for m in frames])
    med = float(np.median(levels))
    spread = 1.4826 * float(np.median(np.abs(levels - med)))
    if kind == "flats":
        for m in frames:
            if med > 0 and abs(m.median_adu - med) / med > 0.15:
                g.flags.append(SubFlag(m.file, "median_adu", m.median_adu, med,
                                       f"brightness {m.median_adu:.0f} ADU vs {med:.0f} for the "
                                       "other flats (panel or sky changed)"))
            if m.clipped_pct and m.clipped_pct > 0.01:
                g.flags.append(SubFlag(m.file, "clipped_pct", m.clipped_pct, 0.01,
                                       f"{m.clipped_pct:.2f} % of pixels clipped (overexposed)"))
    else:
        noise_med = g.medians.get("noise_adu") or 0.0
        # A dark's level should only wander by a fraction of its noise; more means light
        # reached the sensor (or the frame is not a dark at all).
        limit = max(min(5.0 * spread, 2.0 * noise_med), 0.5 * noise_med, 8.0)
        for m in frames:
            if m.median_adu - med > limit:
                g.flags.append(SubFlag(m.file, "median_adu", m.median_adu, med + limit,
                                       f"level {m.median_adu:.0f} ADU vs {med:.0f} (light leak, "
                                       "or not a dark frame?)"))
            elif med - m.median_adu > limit:
                g.flags.append(SubFlag(m.file, "median_adu", m.median_adu, med - limit,
                                       f"level {m.median_adu:.0f} ADU vs {med:.0f} (different "
                                       "offset setting?)"))
        if noise_med:
            for m in frames:
                if m.noise_adu and m.noise_adu > 1.3 * noise_med + 2:
                    g.flags.append(SubFlag(m.file, "noise_adu", m.noise_adu, 1.3 * noise_med,
                                           f"noise {m.noise_adu:.1f} ADU vs {noise_med:.1f} "
                                           "for the rest"))
    return g


def _time(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def summarize_calibration(metrics: list[CalMetrics], lights: FrameMeta | None = None,
                          lights_time: str | None = None,
                          errors: dict[str, str] | None = None) -> CalibrationSummary:
    groups = {k: _group(k, [m for m in metrics if m.kind == k]) for k in KINDS
              if any(m.kind == k for m in metrics)}
    summary = CalibrationSummary(groups, [], errors or {})
    notes = summary.notes

    def first(kind: str) -> CalMetrics | None:
        g = groups.get(kind)
        return (g.frames or g.masters or [None])[0] if g else None

    # --- headers that disagree with the folder (ASIAIR names flat darks "Flat")
    for kind, g in groups.items():
        wrong = [m for m in g.frames if m.header_type
                 and HEADER_KIND.get(m.header_type) not in (kind, None)]
        if wrong:
            said = Counter(m.header_type for m in wrong).most_common(1)[0][0]
            notes.append(CalNote("info", kind, f"{len(wrong)} {_name(kind)} are labelled "
                                 f"'{said}' in their headers; the folder and the data say "
                                 f"{_name(kind)}, so AdvAstro uses them as {_name(kind)}."))

    # --- darks against the lights
    darks = groups.get("darks")
    if darks and lights is not None:
        problems = []
        exp = darks.setting("exposure_s")
        if exp and lights.exposure_s and abs(exp - lights.exposure_s) > 0.01 * lights.exposure_s:
            problems.append(f"exposure {exp:g} s vs lights {lights.exposure_s:g} s")
        for attr, label in (("gain", "gain"), ("offset", "offset"), ("binning", "binning")):
            dv, lv = darks.setting(attr), getattr(lights, attr)
            if dv is not None and lv is not None and dv != lv:
                problems.append(f"{label} {dv:g} vs lights {lv:g}")
        dt = _median(m.temperature_c for m in darks.frames)
        if dt is not None and lights.temperature_c is not None \
                and abs(dt - lights.temperature_c) > 2.0:
            problems.append(f"temperature {dt:.0f} °C vs lights {lights.temperature_c:.0f} °C")
        if problems:
            notes.append(CalNote("bad", "darks", "Darks do not match the lights: "
                                 + "; ".join(problems) + "."))
        else:
            parts = [f"{exp:g} s" if exp else None,
                     f"gain {darks.setting('gain'):g}" if darks.setting("gain") is not None
                     else None,
                     f"offset {darks.setting('offset'):g}" if darks.setting("offset") is not None
                     else None,
                     f"{dt:.0f} °C" if dt is not None else None]
            notes.append(CalNote("good", "darks", "Darks match the lights ("
                                 + ", ".join(p for p in parts if p) + ")."))
        d_time, l_time = _time(first("darks").time if first("darks") else None), \
            _time(lights_time)
        if d_time and l_time and abs((l_time - d_time).days) > 180:
            notes.append(CalNote("info", "darks", f"The darks are {abs((l_time - d_time).days)} "
                                 "days older than the lights. A dark library is fine, but "
                                 "refresh it about once a year: sensors change slowly."))

    # --- flats
    flats = groups.get("flats")
    if flats:
        lvl = flats.medians.get("level_pct")
        if lvl is not None:
            if lvl < 15:
                notes.append(CalNote("warn", "flats", f"Flats are dim ({lvl:.0f} % of full "
                                     "scale). Aim for 30–60 % so their noise does not add to "
                                     "the lights."))
            elif lvl > 75:
                notes.append(CalNote("bad", "flats", f"Flats are very bright ({lvl:.0f} % of "
                                     "full scale) and may be non-linear. Aim for 30–60 %."))
            elif lvl < 25:
                notes.append(CalNote("info", "flats", f"Flats reach {lvl:.0f} % of full scale: "
                                     "usable, though 30–60 % gives cleaner masters."))
            else:
                notes.append(CalNote("good", "flats", f"Flat brightness is good ({lvl:.0f} % "
                                     "of full scale)."))
        chans = [m.channel_levels for m in flats.frames if m.channel_levels]
        if chans and len(chans[0]) == 3:
            avg = np.mean(np.array(chans), axis=0)
            sat = flats.frames[0].saturation_adu or 65535.0
            lo, hi = int(np.argmin(avg)), int(np.argmax(avg))
            names = ("red", "green", "blue")
            if avg[lo] < 0.45 * avg[hi]:
                notes.append(CalNote("info", "flats", f"The flats are much dimmer in "
                                     f"{names[lo]} ({avg[lo] / sat * 100:.0f} %) than in "
                                     f"{names[hi]} ({avg[hi] / sat * 100:.0f} %). That is normal "
                                     "for many light sources, but keep the dimmest channel above "
                                     "about 10 %."))
        vig = flats.medians.get("vignetting_pct")
        if vig is not None:
            notes.append(CalNote("info", "flats", f"Vignetting: the corners get about "
                                 f"{vig:.0f} % less light than the centre; the flats correct "
                                 "this."))
        dust = flats.medians.get("dust_spots")
        if dust:
            depth = flats.medians.get("dust_depth_pct") or 0
            notes.append(CalNote("info", "flats", f"About {dust:.0f} dust shadows show in the "
                                 f"flats (deepest {depth:.1f} %). They are corrected as long as "
                                 "nothing in the optical train moved between lights and flats."))
        f_time, l_time = _time(first("flats").time if first("flats") else None), \
            _time(lights_time)
        if f_time and l_time:
            days = abs((l_time - f_time).total_seconds()) / 86400
            if days > 1.5:
                notes.append(CalNote("warn", "flats", f"The flats are from a different night "
                                     f"({days:.0f} days apart). They only match if the camera "
                                     "was not rotated, refocused or cleaned in between."))
            else:
                notes.append(CalNote("good", "flats", "Flats are from the same night as the "
                                     "lights."))
        if lights is not None:
            fb = flats.setting("binning")
            if fb is not None and lights.binning is not None and fb != lights.binning:
                notes.append(CalNote("bad", "flats", f"Flats are binned {fb:g}x but the lights "
                                     f"{lights.binning:g}x."))

    # --- flat darks against the flats, or bias as the substitute
    fd = groups.get("darkflats")
    bias = groups.get("bias")
    if flats and fd:
        fe, de = flats.setting("exposure_s"), fd.setting("exposure_s")
        fg, dg = flats.setting("gain"), fd.setting("gain")
        problems = []
        if fe and de and abs(fe - de) > 0.05 * fe:
            problems.append(f"exposure {de:g} s vs flats {fe:g} s")
        if fg is not None and dg is not None and fg != dg:
            problems.append(f"gain {dg:g} vs flats {fg:g}")
        notes.append(CalNote("bad", "darkflats", "Flat darks do not match the flats: "
                             + "; ".join(problems) + ".") if problems else
                     CalNote("good", "darkflats", f"Flat darks match the flats "
                             f"({fe:g} s, gain {fg:g})." if fe and fg is not None else
                             "Flat darks match the flats."))
    elif flats and not fd and not bias:
        notes.append(CalNote("bad", "flats", "Neither flat darks nor bias were found, so the "
                             "flats cannot be calibrated properly."))
    if bias:
        be = bias.setting("exposure_s")
        if be and be > 0.1:
            notes.append(CalNote("info", "bias", f"The bias frames are {be:g} s exposures, so "
                                 "they behave as short darks. That is fine with flats of the "
                                 "same exposure."))
        if lights is not None:
            for attr, label in (("gain", "gain"), ("offset", "offset")):
                bv, lv = bias.setting(attr), getattr(lights, attr)
                if bv is not None and lv is not None and bv != lv:
                    notes.append(CalNote("warn", "bias", f"Bias {label} {bv:g} differs from the "
                                         f"lights ({lv:g})."))

    # --- light leaks: dark-type frames whose level climbs during the series
    for kind in ("darks", "darkflats", "bias"):
        g = groups.get(kind)
        if not g or len(g.frames) < 3:
            continue
        noise = g.medians.get("noise_adu") or 0
        levels = [m.median_adu for m in g.frames]
        if noise and max(levels) - min(levels) > 2.0 * noise:
            ordered = sorted(g.frames, key=lambda m: m.time or m.file)
            rising = ordered[-1].median_adu - ordered[0].median_adu > noise
            notes.append(CalNote("warn", kind, f"The {_name(kind)} vary in level from "
                                 f"{min(levels):.0f} to {max(levels):.0f} ADU"
                                 + (", rising through the series" if rising else "") +
                                 ". That points to light reaching the sensor (a light leak, or "
                                 "darks taken in daylight). Cap the telescope and cover the "
                                 "camera, and leave the brightest frames out."))

    # --- dark current features
    for kind in ("darks", "darkflats", "bias"):
        g = groups.get(kind)
        if not g or not g.frames:
            continue
        noise = g.medians.get("noise_adu") or 0
        glow = g.medians.get("glow_adu") or 0
        if kind == "darks" and noise and glow > 3 * noise:
            where = Counter(m.glow_where for m in g.frames if m.glow_where).most_common(1)
            side = where[0][0] if where else "edge"
            notes.append(CalNote("info", "darks", f"Amp glow: the {side} is {glow:.0f} ADU "
                                 "brighter than the centre. Matching darks remove it; avoid "
                                 "dark scaling or optimization."))
        band = g.medians.get("banding_adu") or 0
        if noise and band > 0.3 * noise:
            notes.append(CalNote("warn", kind, f"Row or column banding of {band:.1f} ADU in the "
                                 f"{_name(kind)}; more frames give a smoother master."))
        hot = g.medians.get("hot_pct")
        if kind == "darks" and hot is not None:
            notes.append(CalNote("info", "darks", f"{g.medians['hot_pixels']:.0f} hot pixels "
                                 f"({hot:.3f} % of the sensor) at this exposure and temperature."))

    # --- frame counts
    for kind, minimum, ideal in (("darks", 15, 30), ("flats", 15, 30), ("bias", 20, 50),
                                 ("darkflats", 15, 30)):
        g = groups.get(kind)
        if g and g.frames and len(g.frames) < minimum and not g.masters:
            notes.append(CalNote("warn", kind, f"Only {len(g.frames)} {_name(kind)}: {ideal} or "
                                 "more give a master with less noise."))
    return summary


def _name(kind: str) -> str:
    return {"bias": "bias frames", "darks": "darks", "flats": "flats",
            "darkflats": "flat darks"}[kind]
