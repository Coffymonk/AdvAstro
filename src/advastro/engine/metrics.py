"""Per-sub measurements.

Method summary (documented so results can be checked against PixInsight
SubframeSelector and Siril):

1. Colour (CFA) data is binned 2x2 into a luminance superpixel image, which
   avoids debayer interpolation; star sizes are converted back to native pixels.
2. Background and its RMS are modelled on a sigma-clipped median mesh
   (photutils Background2D).
3. Stars are detected at a sigma threshold on the background-subtracted image
   (photutils segmentation).
4. FWHM and eccentricity come from 2-D elliptical Gaussian fits to the
   brightest isolated, unsaturated stars; the median is reported.
5. Noise is the MAD of background pixels outside stars, scaled to sigma.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
from astropy.stats import SigmaClip
from photutils.background import Background2D, MedianBackground
from photutils.segmentation import SourceCatalog, detect_sources
from scipy.optimize import least_squares

from advastro.frame import Frame

MAD_TO_SIGMA = 1.4826
GAUSS_SIGMA_TO_FWHM = 2.0 * math.sqrt(2.0 * math.log(2.0))


@dataclass
class SubMetrics:
    file: str
    filter: str | None
    exposure_s: float | None
    width: int
    height: int
    star_count: int
    fwhm_px: float | None
    fwhm_arcsec: float | None
    eccentricity: float | None
    background_adu: float
    noise_adu: float
    snr_estimate: float | None
    saturated_fraction: float
    stars_measured: int
    pixel_scale_arcsec: float | None
    warnings: list[str]
    path: str = ""
    gradient_pct: float | None = None      # background spread across the frame, % of level
    time: str | None = None                # DATE-OBS, ISO format
    ref_stars: list[tuple[float, float]] | None = None  # brightest star positions (native px)
    offset_px: tuple[float, float] | None = None        # shift vs the session reference

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MeasureOptions:
    detect_sigma: float = 5.0
    min_star_area_px: int = 5
    max_fit_stars: int = 150
    fit_box_fwhm: float = 4.0  # fit box half-size in units of a first FWHM guess
    background_box_px: int = 64
    saturation_level: float = 0.98  # fraction of saturation ADU treated as clipped


def luminance_plane(frame: Frame) -> tuple[np.ndarray, int]:
    """Return a 2-D measurement image and the factor back to native pixels."""
    data = frame.data
    if data.ndim == 3:  # already debayered colour: average channels
        return data.mean(axis=0).astype(np.float32), 1
    if frame.meta.bayer_pattern:
        h, w = (data.shape[0] // 2) * 2, (data.shape[1] // 2) * 2
        d = data[:h, :w]
        binned = d[0::2, 0::2] + d[0::2, 1::2] + d[1::2, 0::2] + d[1::2, 1::2]
        return np.ascontiguousarray(binned, dtype=np.float32), 2
    return np.ascontiguousarray(data, dtype=np.float32), 1


def _gauss2d(params, yy, xx):
    amp, x0, y0, sx, sy, theta, offset = params
    ct, st = math.cos(theta), math.sin(theta)
    xr = (xx - x0) * ct + (yy - y0) * st
    yr = -(xx - x0) * st + (yy - y0) * ct
    return amp * np.exp(-0.5 * ((xr / sx) ** 2 + (yr / sy) ** 2)) + offset


def _gauss2d_jac(params, yy, xx):
    """Analytic Jacobian of _gauss2d (about 4x faster than numeric differences)."""
    amp, x0, y0, sx, sy, theta, _ = params
    ct, st = math.cos(theta), math.sin(theta)
    dx, dy = xx - x0, yy - y0
    xr = dx * ct + dy * st
    yr = -dx * st + dy * ct
    g = np.exp(-0.5 * ((xr / sx) ** 2 + (yr / sy) ** 2))
    a, b = xr / sx**2, yr / sy**2
    ag = amp * g
    return np.stack([
        g,
        ag * (a * ct - b * st),
        ag * (a * st + b * ct),
        ag * xr**2 / sx**3,
        ag * yr**2 / sy**3,
        ag * xr * yr * (1.0 / sy**2 - 1.0 / sx**2),
        np.ones_like(g),
    ], axis=-1).reshape(-1, 7)


def _fit_star(img: np.ndarray, x: float, y: float, half: int) -> tuple[float, float] | None:
    """Fit an elliptical Gaussian. Returns (fwhm_px, eccentricity) or None."""
    xi, yi = int(round(x)), int(round(y))
    y0, y1, x0, x1 = yi - half, yi + half + 1, xi - half, xi + half + 1
    if y0 < 0 or x0 < 0 or y1 > img.shape[0] or x1 > img.shape[1]:
        return None
    cut = img[y0:y1, x0:x1].astype(np.float64)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    peak = float(cut.max() - np.median(cut))
    if peak <= 0:
        return None
    guess = [peak, x, y, half / 3, half / 3, 0.0, float(np.median(cut))]
    lower = [0, x - 2, y - 2, 0.3, 0.3, -math.pi, -np.inf]
    upper = [np.inf, x + 2, y + 2, half, half, math.pi, np.inf]
    try:
        res = least_squares(
            lambda p: (_gauss2d(p, yy, xx) - cut).ravel(), guess, bounds=(lower, upper),
            jac=lambda p: _gauss2d_jac(p, yy, xx), max_nfev=200,
        )
    except (ValueError, RuntimeError):
        return None
    if not res.success:
        return None
    _, _, _, sx, sy, _, _ = res.x
    a, b = max(sx, sy), min(sx, sy)
    fwhm = GAUSS_SIGMA_TO_FWHM * math.sqrt(a * b)
    ecc = math.sqrt(max(0.0, 1.0 - (b / a) ** 2))
    return fwhm, ecc


def _isolated(segmap: np.ndarray, label: int, x: float, y: float, half: int) -> bool:
    """True if no other detected source falls inside the star's fit box."""
    xi, yi = int(round(x)), int(round(y))
    box = segmap[max(0, yi - half):yi + half + 1, max(0, xi - half):xi + half + 1]
    others = box[(box != 0) & (box != label)]
    return others.size == 0


def measure_frame(frame: Frame, options: MeasureOptions | None = None) -> SubMetrics:
    opt = options or MeasureOptions()
    warnings: list[str] = []
    img, native_factor = luminance_plane(frame)
    img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)

    # Saturation is judged on the original data, not the binned plane.
    sat_adu = frame.meta.saturation_adu or float(np.max(frame.data))
    clipped = frame.data >= opt.saturation_level * sat_adu
    saturated_fraction = float(np.count_nonzero(clipped)) / frame.data.size

    box = min(opt.background_box_px, img.shape[0] // 2, img.shape[1] // 2)
    bkg = Background2D(img, box, filter_size=(3, 3), sigma_clip=SigmaClip(sigma=3.0),
                       bkg_estimator=MedianBackground())
    resid = img - bkg.background
    rms = float(bkg.background_rms_median)
    mesh = np.asarray(bkg.background_mesh, dtype=float)
    level = float(np.median(mesh))
    gradient_pct = (float(np.percentile(mesh, 95) - np.percentile(mesh, 5)) / level * 100.0
                    if level > 0 else None)

    segm = detect_sources(resid, opt.detect_sigma * rms, n_pixels=opt.min_star_area_px)
    segmap = segm.data if segm is not None else np.zeros(img.shape, dtype=np.int32)

    star_mask = segmap > 0
    bg_pixels = resid[~star_mask]
    noise = MAD_TO_SIGMA * float(np.median(np.abs(bg_pixels - np.median(bg_pixels))))
    background = float(np.median(img[~star_mask]))
    if native_factor == 2:  # four pixels were summed; report per native pixel
        noise /= 2.0
        background /= 4.0

    star_count = int(segm.n_labels) if segm is not None else 0
    fwhm_px = ecc = snr = None
    ref_stars: list[tuple[float, float]] = []
    measured = 0
    if star_count:
        cat = SourceCatalog(resid, segm)
        xs, ys = np.asarray(cat.x_centroid), np.asarray(cat.y_centroid)
        peaks, fluxes = np.asarray(cat.max_value), np.asarray(cat.segment_flux)
        labels = np.asarray(cat.labels)
        moment_fwhm = np.asarray(cat.fwhm.value)
        sat_bin = opt.saturation_level * sat_adu * (4 if native_factor == 2 else 1)
        bg_level = float(np.median(bkg.background))
        ok = np.isfinite(xs) & np.isfinite(ys) & (peaks + bg_level < sat_bin)
        guess_fwhm = float(np.median(moment_fwhm[ok])) if ok.any() else 3.0
        half = int(max(4, min(25, math.ceil(opt.fit_box_fwhm * guess_fwhm / 2))))

        fits_: list[tuple[float, float]] = []
        for i in np.argsort(fluxes)[::-1]:
            if len(fits_) >= opt.max_fit_stars:
                break
            if not ok[i] or not _isolated(segmap, labels[i], xs[i], ys[i], half):
                continue
            if (r := _fit_star(resid, xs[i], ys[i], half)) is not None:
                fits_.append(r)
        measured = len(fits_)
        bright = [i for i in np.argsort(fluxes)[::-1] if ok[i]][:30]
        ref_stars = [(float(xs[i]) * native_factor, float(ys[i]) * native_factor)
                     for i in bright]
        if fits_:
            fwhm_px = float(np.median([f[0] for f in fits_])) * native_factor
            ecc = float(np.median([f[1] for f in fits_]))
        if ok.any() and noise > 0:
            # Median star peak over per-pixel noise: a simple, comparable SNR proxy.
            snr = float(np.median(peaks[ok]) / (noise * (4 if native_factor == 2 else 1)))
    if star_count < 10:
        warnings.append("very few stars detected; clouds, dew or a non-light frame?")
    if saturated_fraction > 0.0001:  # 0.01 %: roughly 800 px on an 8 MP sensor
        warnings.append(f"{saturated_fraction:.2%} of pixels at or near saturation")

    scale = frame.meta.pixel_scale_arcsec
    return SubMetrics(
        file=frame.path.name,
        filter=frame.meta.filter_name,
        exposure_s=frame.meta.exposure_s,
        width=int(frame.data.shape[-1]),
        height=int(frame.data.shape[-2]),
        star_count=star_count,
        fwhm_px=fwhm_px,
        fwhm_arcsec=fwhm_px * scale if (fwhm_px and scale) else None,
        eccentricity=ecc,
        background_adu=background,
        noise_adu=noise,
        snr_estimate=snr,
        saturated_fraction=saturated_fraction,
        stars_measured=measured,
        pixel_scale_arcsec=scale,
        warnings=warnings,
        path=str(frame.path),
        gradient_pct=gradient_pct,
        time=frame.meta.date_obs.isoformat() if frame.meta.date_obs else None,
        ref_stars=ref_stars or None,
    )
