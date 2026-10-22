"""Per-session analysis: run per-sub metrics in parallel and compare subs.

Subs are judged relative to each other within the session, never against a
single absolute quality score. Each flag carries the measured value, the
threshold and the reason, so the advisor (and the user) can see why.
"""

from __future__ import annotations

import multiprocessing
from collections.abc import Callable, Iterable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from advastro.engine.metrics import MeasureOptions, SubMetrics, measure_frame
from advastro.i18n import tr
from advastro.readers import read_frame

MAD_TO_SIGMA = 1.4826


@dataclass
class SubFlag:
    file: str
    metric: str
    value: float
    threshold: float
    reason: str


@dataclass
class SessionSummary:
    subs: list[SubMetrics]
    flags: list[SubFlag] = field(default_factory=list)
    medians: dict[str, float | None] = field(default_factory=dict)
    sampling: str | None = None  # undersampled / well sampled / oversampled
    errors: dict[str, str] = field(default_factory=dict)
    dithered: bool | None = None   # None = could not tell
    dither_px: float | None = None  # median shift between consecutive subs
    drift_px: float | None = None   # total shift first to last sub

    def flagged_files(self) -> set[str]:
        return {f.file for f in self.flags}


@dataclass
class SessionThresholds:
    """Relative thresholds in robust sigmas (MAD) from the session median."""

    fwhm_sigma: float = 3.0
    eccentricity_max: float = 0.6
    star_count_fraction: float = 0.6  # flag subs with fewer stars than this x median
    background_sigma: float = 4.0


def _measure_path(path: str, options: MeasureOptions) -> SubMetrics:
    return measure_frame(read_frame(path), options)


def analyze_paths(
    paths: Iterable[str | Path],
    options: MeasureOptions | None = None,
    jobs: int | None = None,
    progress: Callable[[int, int, str], None] | None = None,
    on_result: Callable[[SubMetrics], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[list[SubMetrics], dict[str, str]]:
    """Measure every file. Returns metrics sorted by file name and per-file errors.

    on_result is called as each sub finishes (for live UIs); should_stop is
    polled between subs so a long analysis can be cancelled.
    """
    options = options or MeasureOptions()
    paths = [str(p) for p in paths]
    results: list[SubMetrics] = []
    errors: dict[str, str] = {}
    stop = should_stop or (lambda: False)

    def handle(i: int, path: str, get) -> None:
        try:
            metrics = get()
            results.append(metrics)
            if on_result:
                on_result(metrics)
        except Exception as exc:
            errors[Path(path).name] = str(exc)
        if progress:
            progress(i, len(paths), Path(path).name)

    if jobs == 1 or len(paths) <= 1:
        for i, p in enumerate(paths, 1):
            if stop():
                break
            handle(i, p, lambda p=p: _measure_path(p, options))
    else:
        # spawn (not fork) on every platform: forking a process that runs threads,
        # such as the desktop app, can deadlock on Linux.
        pool = ProcessPoolExecutor(max_workers=jobs,
                                   mp_context=multiprocessing.get_context("spawn"))
        try:
            futures = {pool.submit(_measure_path, p, options): p for p in paths}
            for i, fut in enumerate(as_completed(futures), 1):
                if stop():
                    break
                handle(i, futures[fut], fut.result)
        finally:
            pool.shutdown(wait=not stop(), cancel_futures=True)
    results.sort(key=lambda m: m.file)
    return results, errors


def resolve_pixel_scale(summary: SessionSummary, equipment: dict,
                        session_file: Path | None) -> tuple[float | None, str]:
    """Pixel scale from FITS headers, then the [equipment] config, then a .mksession.

    Fills fwhm_arcsec for subs that lacked it and updates the session median.
    Returns (scale, source description).
    """
    from advastro.integrations.miklosoft import load_mksession

    scale, source = None, ""
    header_scales = [s.pixel_scale_arcsec for s in summary.subs if s.pixel_scale_arcsec]
    if header_scales:
        scale, source = header_scales[0], "FITS headers"
    elif equipment.get("focal_length_mm") and equipment.get("pixel_size_um"):
        scale = 206.264806 * equipment["pixel_size_um"] / equipment["focal_length_mm"]
        source = "config [equipment]"
    elif session_file:
        scale = load_mksession(session_file).gear.pixel_scale_arcsec
        source = session_file.name if scale else ""
    if scale:
        for s in summary.subs:
            if s.fwhm_px and not s.fwhm_arcsec:
                s.pixel_scale_arcsec = scale
                s.fwhm_arcsec = s.fwhm_px * scale
        vals = [s.fwhm_arcsec for s in summary.subs if s.fwhm_arcsec]
        if vals:
            summary.medians["fwhm_arcsec"] = float(np.median(vals))
    return scale, source


def _robust(values: list[float]) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float)
    med = float(np.median(arr))
    return med, MAD_TO_SIGMA * float(np.median(np.abs(arr - med)))


def classify_sampling(fwhm_px: float | None) -> str | None:
    """Nyquist-style rule of thumb on star FWHM in pixels."""
    if fwhm_px is None:
        return None
    if fwhm_px < 2.0:
        return "undersampled"
    if fwhm_px > 5.0:
        return "oversampled"
    return "well sampled"


def summarize(
    subs: list[SubMetrics],
    thresholds: SessionThresholds | None = None,
    errors: dict[str, str] | None = None,
) -> SessionSummary:
    t = thresholds or SessionThresholds()
    summary = SessionSummary(subs=subs, errors=errors or {})
    if not subs:
        return summary

    def vals(attr: str) -> list[float]:
        return [getattr(s, attr) for s in subs if getattr(s, attr) is not None]

    for attr in ("fwhm_px", "fwhm_arcsec", "eccentricity", "star_count",
                 "background_adu", "noise_adu", "snr_estimate"):
        v = vals(attr)
        summary.medians[attr] = float(np.median(v)) if v else None
    summary.sampling = classify_sampling(summary.medians["fwhm_px"])
    v = vals("gradient_pct")
    summary.medians["gradient_pct"] = float(np.median(v)) if v else None
    measure_offsets(summary)

    fwhm = vals("fwhm_px")
    if len(fwhm) >= 3:
        med, sig = _robust(fwhm)
        limit = med + t.fwhm_sigma * max(sig, 0.05 * med)
        for s in subs:
            if s.fwhm_px is not None and s.fwhm_px > limit:
                summary.flags.append(SubFlag(
                    s.file, "fwhm_px", s.fwhm_px, limit,
                    tr("flag.fwhm", value=f"{s.fwhm_px:.2f}", median=f"{med:.2f}")))

    for s in subs:
        if s.eccentricity is not None and s.eccentricity > t.eccentricity_max:
            summary.flags.append(SubFlag(
                s.file, "eccentricity", s.eccentricity, t.eccentricity_max,
                tr("flag.ecc", value=f"{s.eccentricity:.2f}")))

    stars = vals("star_count")
    if len(stars) >= 3:
        med = float(np.median(stars))
        limit = t.star_count_fraction * med
        for s in subs:
            if s.star_count < limit:
                summary.flags.append(SubFlag(
                    s.file, "star_count", s.star_count, limit,
                    tr("flag.stars", value=s.star_count, median=f"{med:.0f}")))

    bg = vals("background_adu")
    if len(bg) >= 3:
        med, sig = _robust(bg)
        limit = med + t.background_sigma * max(sig, 0.02 * med)
        for s in subs:
            if s.background_adu > limit:
                summary.flags.append(SubFlag(
                    s.file, "background_adu", s.background_adu, limit,
                    tr("flag.sky", value=f"{s.background_adu:.0f}", median=f"{med:.0f}")))
    return summary


def _match_shift(ref: np.ndarray, cur: np.ndarray, tol: float = 2.0) -> tuple[float, float] | None:
    """Translation between two star lists: the shift that most star pairs agree on."""
    if len(ref) < 4 or len(cur) < 4:
        return None
    diffs = (cur[:, None, :] - ref[None, :, :]).reshape(-1, 2)
    dist = np.linalg.norm(diffs[:, None, :] - diffs[None, :, :], axis=2)
    votes = (dist < tol).sum(axis=1)
    best = int(np.argmax(votes))
    if votes[best] < 4:
        return None
    agree = diffs[dist[best] < tol]
    dx, dy = np.median(agree, axis=0)
    return float(dx), float(dy)


def measure_offsets(summary: SessionSummary) -> None:
    """Star shifts between subs: tells dithering (random jumps) from drift (steady creep)."""
    subs = [s for s in summary.subs if s.ref_stars]
    if len(subs) < 3:
        return
    subs.sort(key=lambda s: (s.time or "", s.file))
    ref = np.asarray(subs[0].ref_stars)
    offsets = []
    for s in subs:
        shift = _match_shift(ref, np.asarray(s.ref_stars))
        s.offset_px = shift
        if shift is not None:
            offsets.append(shift)
    if len(offsets) < 3:
        return
    pts = np.asarray(offsets)
    jumps = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    drift = float(np.linalg.norm(pts[-1] - pts[0]))
    per_frame = drift / (len(pts) - 1)
    summary.dither_px = float(np.median(jumps))
    summary.drift_px = drift
    summary.dithered = bool(summary.dither_px > max(2.5, 2.0 * per_frame))
