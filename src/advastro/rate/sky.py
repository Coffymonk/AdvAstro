"""Sky checks for a finished picture: where it is, how deep it goes, how true its colours are.

* Plate solution: from the file (PixInsight and Siril store one) or ASTAP on a copy.
* Depth: detected stars matched against Gaia DR3 (through the CDS VizieR TAP service)
  give the limiting magnitude, the faintest magnitude at which half of the catalogue
  stars are visible.
* Colour truth: the colour of each star in the picture compared with its Gaia BP-RP.
* Survey image: the same field from DSS2, Pan-STARRS or Mellinger (CDS hips2fits),
  on exactly the same pixel grid, for blinking against the picture.
* Comparisons with other photographers: AstroBin (with the user's own API key), or
  search pages opened in the browser.

Everything that needs the network fails gracefully and says why.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from dataclasses import field as dc_field

import numpy as np

from advastro.rate.judge import Finding
from advastro.rate.measure import Measurements
from advastro.rate.picture import Picture
from advastro.sky.solve import SkyField

USER_AGENT = "AdvAstroAnalyzer/0.1 (+https://miklosoft.se/main)"
TAP = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync"
HIPS2FITS = "https://alasky.cds.unistra.fr/hips-image-services/hips2fits"
ASTROBIN = "https://www.astrobin.com/api/v1/"


class SkyError(RuntimeError):
    pass


def _get(url: str, timeout: float = 40.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception as exc:  # network, TLS, HTTP errors
        raise SkyError(f"{urllib.parse.urlsplit(url).netloc}: {exc}") from exc


def _cache_dir():
    from advastro.config import user_config_dir

    d = user_config_dir() / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------- WCS
def make_wcs(keys: dict):
    from astropy.io import fits
    from astropy.wcs import WCS

    hdr = fits.Header()
    for k, v in keys.items():
        try:
            hdr[k] = v
        except (ValueError, KeyError):
            pass
    hdr["NAXIS"] = 2
    return WCS(hdr, naxis=2)


def solve_picture(pic: Picture, cfg, hint: tuple[float, float] | None = None,
                  scale_hint: float | None = None) -> SkyField:
    """The picture's position on the sky: from its own header, else ASTAP."""
    from advastro.frame import Frame, FrameMeta
    from advastro.sky.solve import SolveError, detect_astap, field_from_wcs_header, solve_astap

    if pic.header:
        f = field_from_wcs_header(pic.header, pic.width, pic.height)
        if f is not None and f.wcs:
            return f
    install = detect_astap(cfg.get("solver", "astap_path", ""),
                           cfg.get("solver", "database_path", ""))
    if not install.ready:
        raise SkyError("astap_missing" if install.executable is None else "astap_no_database")
    meta = FrameMeta()
    if hint:
        meta.ra_deg, meta.dec_deg = hint
    frame = Frame(path=pic.path, data=pic.luminance * 65535.0, meta=meta, format="picture")
    try:
        return solve_astap(frame, install, scale_hint=scale_hint,
                           radius_deg=15.0 if hint else 180.0,
                           timeout_s=max(120.0, cfg.get("solver", "timeout_s", 90.0)),
                           auto_fov=scale_hint is None)
    except SolveError as exc:
        raise SkyError(str(exc)) from exc


# ---------------------------------------------------------------------------- Gaia
def _mag_limit(area_deg2: float) -> float:
    for area, mag in ((0.15, 20.5), (0.6, 19.5), (2.0, 18.5), (6.0, 17.5), (20.0, 16.0),
                      (80.0, 14.0)):
        if area_deg2 <= area:
            return mag
    return 12.0


def gaia_stars(ra: float, dec: float, radius_deg: float, mag_limit: float,
               rows: int = 80000) -> np.ndarray:
    """(n, 4): ra, dec, G, BP-RP (nan when unknown). Cached on disk."""
    key = hashlib.sha1(f"{ra:.4f}{dec:.4f}{radius_deg:.4f}{mag_limit:.1f}{rows}".encode()
                       ).hexdigest()[:16]
    path = _cache_dir() / f"gaia_{key}.npy"
    if path.exists():
        return np.load(path)
    query = (f'SELECT TOP {rows} RA_ICRS, DE_ICRS, Gmag, BPmag, RPmag FROM "I/355/gaiadr3" '
             f"WHERE 1=CONTAINS(POINT('ICRS', RA_ICRS, DE_ICRS), "
             f"CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, {radius_deg:.5f})) AND Gmag < {mag_limit:.2f} "
             "ORDER BY Gmag")
    url = TAP + "?" + urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL",
                                              "FORMAT": "csv", "QUERY": query})
    text = _get(url, timeout=90).decode("utf-8", "replace")
    out = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 5:
            continue
        try:
            bp = float(row[3]) if row[3].strip() else math.nan
            rp = float(row[4]) if row[4].strip() else math.nan
            out.append((float(row[0]), float(row[1]), float(row[2]), bp - rp))
        except ValueError:
            continue  # header line
    arr = np.array(out, dtype=np.float64).reshape(-1, 4)
    np.save(path, arr)
    return arr


@dataclass
class DepthResult:
    limit_mag: float | None              # 50 % completeness
    catalogue_limit: float               # faintest catalogue star used
    matched: int
    completeness: list[tuple[float, float]]  # (mag, fraction)
    lower_bound: bool = False            # the image goes deeper than the catalogue query


@dataclass
class ColourResult:
    stars: int
    r: float                             # correlation of picture colour with BP-RP
    slope: float
    sun_offset: float                    # picture colour index of a Sun-like star (0 = white)
    points: np.ndarray | None = None     # (n, 2): BP-RP, picture colour


def _project(wcs, cat: np.ndarray, binned: int) -> tuple[np.ndarray, np.ndarray]:
    px, py = wcs.all_world2pix(cat[:, 0], cat[:, 1], 0)
    # Work pixels: the analysis may have binned the picture.
    return (px + 0.5) / binned - 0.5, (py + 0.5) / binned - 0.5


def depth_and_colour(m: Measurements, field_: SkyField, progress=None
                     ) -> tuple[DepthResult | None, ColourResult | None, list[str]]:
    from scipy.spatial import cKDTree

    notes = []
    if not field_.wcs or m.detections is None or len(m.detections) < 20:
        return None, None, ["no stars or no plate solution"]
    wcs = make_wcs(field_.wcs)
    area = field_.width_deg * field_.height_deg
    limit = _mag_limit(area)
    if progress:
        progress("gaia")
    cat = gaia_stars(field_.ra, field_.dec, field_.radius_deg * 1.02, limit)
    if len(cat) < 20:
        return None, None, ["too few catalogue stars"]
    b = m.work_binned
    w, h = m.width / b, m.height / b
    x, y = _project(wcs, cat, b)
    inside = (x > 12) & (x < w - 12) & (y > 12) & (y < h - 12)
    cat, x, y = cat[inside], x[inside], y[inside]
    det = m.detections
    tree = cKDTree(det[:, :2])
    radius = max(1.6, 0.6 * (m.fwhm or 3.0) / b)
    d, _ = tree.query(np.column_stack([x, y]), distance_upper_bound=radius)
    hit = np.isfinite(d)
    # Chance coincidences in crowded fields: the same test with the catalogue shifted.
    d2, _ = tree.query(np.column_stack([x + 7 * radius, y - 5 * radius]),
                       distance_upper_bound=radius)
    chance = np.isfinite(d2)
    g = cat[:, 2]
    bins = np.arange(np.floor(g.min() * 2) / 2, limit + 0.5, 0.5)
    comp = []
    for lo in bins:
        sel = (g >= lo) & (g < lo + 0.5)
        if sel.sum() >= 8:
            frac = (hit[sel].mean() - chance[sel].mean()) / max(1e-6, 1 - chance[sel].mean())
            comp.append((float(lo + 0.25), float(np.clip(frac, 0, 1))))
    lim = None
    for (m1, f1), (m2, f2) in zip(comp, comp[1:], strict=False):
        if f1 >= 0.5 > f2 and m1 > 8:
            lim = m1 + (f1 - 0.5) / max(f1 - f2, 1e-6) * (m2 - m1)
    lower = False
    if lim is None and comp and comp[-1][1] >= 0.5:
        lim, lower = comp[-1][0], True
    depth = DepthResult(lim, float(g.max()), int(hit.sum()), comp, lower)

    colour = None
    if m.star_colors is not None and len(m.star_colors) >= 20:
        st = cKDTree(m.star_colors[:, :2])
        d3, idx = st.query(np.column_stack([x, y]), distance_upper_bound=radius)
        ok = np.isfinite(d3) & np.isfinite(cat[:, 3]) & (cat[:, 3] > -0.2) & (cat[:, 3] < 3.0)
        if ok.sum() >= 20:
            bp = cat[ok, 3]
            ci = m.star_colors[idx[ok], 2]
            good = np.abs(ci) < 2.5
            bp, ci = bp[good], ci[good]
            if bp.size >= 20 and np.std(bp) > 0.05 and np.std(ci) > 1e-3:
                r = float(np.corrcoef(bp, ci)[0, 1])
                slope, icpt = np.polyfit(bp, ci, 1)
                colour = ColourResult(int(bp.size), r, float(slope),
                                      float(slope * 0.82 + icpt),
                                      np.column_stack([bp, ci]).astype(np.float32))
    return depth, colour, notes


# ---------------------------------------------------------------------------- survey image
GAIA_CREDIT = "Gaia DR3: ESA/Gaia/DPAC, via VizieR (CDS, Strasbourg)"
SURVEY_CREDITS = {
    "DSS2 colour": "DSS2: STScI / Palomar & UK Schmidt telescopes, via CDS hips2fits",
    "Pan-STARRS DR1": "Pan-STARRS1 Surveys (PS1), via CDS hips2fits",
    "Mellinger all-sky": "© Axel Mellinger, via CDS hips2fits",
}


def survey_credit(name: str | None) -> str:
    return SURVEY_CREDITS.get(name or "", "via CDS hips2fits")


def survey_for(field_: SkyField) -> tuple[str, str]:
    if field_.width_deg > 12:
        return "CDS/P/Mellinger/color", "Mellinger all-sky"
    if field_.width_deg < 1.2 and field_.dec > -29:
        return "CDS/P/PanSTARRS/DR1/color-z-zg-g", "Pan-STARRS DR1"
    return "CDS/P/DSS2/color", "DSS2 colour"


def survey_image(field_: SkyField, width: int, height: int, max_side: int = 1600,
                 hips: str | None = None) -> np.ndarray:
    """The survey's view of exactly this field, as float RGB (h, w, 3), rows like the picture."""
    if not field_.wcs:
        raise SkyError("no plate solution")
    s = max(1.0, max(width, height) / max_side)
    ow, oh = int(round(width / s)), int(round(height / s))
    k = dict(field_.wcs)
    for c in ("1", "2"):
        if f"CRPIX{c}" in k:
            k[f"CRPIX{c}"] = (float(k[f"CRPIX{c}"]) - 0.5) / s + 0.5
    for key in ("CD1_1", "CD1_2", "CD2_1", "CD2_2", "CDELT1", "CDELT2"):
        if key in k:
            k[key] = float(k[key]) * s
    k = {kk: v for kk, v in k.items() if not kk.startswith(("A_", "B_"))}
    k["CTYPE1"], k["CTYPE2"] = "RA---TAN", "DEC--TAN"
    k.update({"NAXIS": 2, "NAXIS1": ow, "NAXIS2": oh})
    params = {"hips": hips or survey_for(field_)[0], "wcs": json.dumps(k), "width": ow,
              "height": oh, "format": "png", "stretch": "linear"}
    data = _get(HIPS2FITS + "?" + urllib.parse.urlencode(params), timeout=90)
    from PIL import Image

    img = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.float32) / 255.0
    # Row order of the PNG is checked against the picture itself (see orient_survey).
    return np.ascontiguousarray(img)


def _structure(lum: np.ndarray) -> np.ndarray:
    from scipy import ndimage as ndi

    hp = lum - ndi.gaussian_filter(lum, 4)
    return (hp - hp.mean()) / (hp.std() + 1e-9)


def orient_survey(survey: np.ndarray, picture_lum: np.ndarray) -> tuple[np.ndarray, float]:
    """Return the survey the right way up (as is, or flipped top-bottom) and the match score.

    Stars sit in the same places in both images, so the orientation with the higher
    correlation of fine structure is the correct one.
    """
    from scipy import ndimage as ndi

    h, w = survey.shape[:2]
    zoom = (h / picture_lum.shape[0], w / picture_lum.shape[1])
    pic = _structure(ndi.zoom(picture_lum, zoom, order=1)[:h, :w])
    lum = survey.mean(axis=-1)
    best, score = survey, -1.0
    for cand in (survey, survey[::-1]):
        s = _structure(cand.mean(axis=-1) if cand is not survey else lum)
        hh, ww = min(s.shape[0], pic.shape[0]), min(s.shape[1], pic.shape[1])
        c = float((s[:hh, :ww] * pic[:hh, :ww]).mean())
        if c > score:
            best, score = cand, c
    return np.ascontiguousarray(best), score


# ---------------------------------------------------------------------------- comparisons
@dataclass
class OtherImage:
    title: str
    author: str
    url: str
    thumb: str
    likes: int | None = None
    integration: str | None = None


def _designations(name: str, aliases: list[str] | None = None) -> list[str]:
    out = []
    for n in [name, *(aliases or [])]:
        if not n:
            continue
        compact = n.replace(" ", "")
        for v in (n, compact):
            if v not in out:
                out.append(v)
    return out[:6]


def astrobin_images(name: str, key: str, secret: str, aliases: list[str] | None = None,
                    limit: int = 24) -> list[OtherImage]:
    """Public images of the object on AstroBin, best liked first. Needs the user's API key."""
    seen, found = set(), []
    for subject in _designations(name, aliases):
        params = {"subjects": subject, "api_key": key, "api_secret": secret, "format": "json",
                  "limit": limit}
        raw = _get(ASTROBIN + "image/?" + urllib.parse.urlencode(params), timeout=30)
        try:
            objs = json.loads(raw).get("objects", [])
        except ValueError as exc:
            raise SkyError("AstroBin returned an unexpected answer") from exc
        for o in objs:
            ident = o.get("hash") or o.get("id")
            if not ident or ident in seen:
                continue
            seen.add(ident)
            thumb = o.get("url_thumb") or o.get("url_gallery") or o.get("url_regular") or ""
            found.append(OtherImage(
                title=str(o.get("title") or name), author=str(o.get("user") or ""),
                url=f"https://www.astrobin.com/{ident}/", thumb=thumb,
                likes=o.get("likes") if isinstance(o.get("likes"), int) else None))
        if len(found) >= limit:
            break
    found.sort(key=lambda i: -(i.likes or 0))
    return found[:limit]


def thumbnail(url: str) -> bytes:
    return _get(url, timeout=20)


def browser_links(name: str) -> list[tuple[str, str]]:
    q = urllib.parse.quote_plus(name)
    return [
        ("AstroBin", f"https://www.astrobin.com/search/?q={q}"),
        ("Wikimedia Commons",
         f"https://commons.wikimedia.org/w/index.php?search={q}&title=Special:MediaSearch&type=image"),
        ("NASA APOD", f"https://www.google.com/search?q=site%3Aapod.nasa.gov+{q}"),
    ]


# ---------------------------------------------------------------------------- result
@dataclass
class SkyResult:
    field: SkyField | None = None
    target: object | None = None          # sky.identify.TargetReport
    target_xy: tuple[float, float] | None = None   # 0–1 position in the frame
    depth: DepthResult | None = None
    colour: ColourResult | None = None
    survey: np.ndarray | None = None
    survey_name: str | None = None
    survey_match: float | None = None     # correlation with the picture (alignment check)
    errors: dict[str, str] = dc_field(default_factory=dict)

    def findings(self) -> list[Finding]:
        F = []
        d = self.depth
        if d and d.limit_mag is not None:
            lim = d.limit_mag
            mag_txt = f"{'at least ' if d.lower_bound else ''}{lim:.1f}"
            wide = self.field is not None and self.field.width_deg > 3
            good, fine = (15.5, 13.5) if wide else (18.0, 16.0)
            if lim >= good:
                sev, text = "good", "That is deep for this field of view."
            elif lim >= fine:
                sev, text = "info", "Typical depth for a few hours of integration."
            else:
                sev, text = "minor", "Fairly shallow: more integration time would show more."
            title = {"good": "Deep image", "info": "Moderate depth", "minor": "Shallow image"}[sev]
            F.append(Finding("depth", "depth", sev, title,
                             f"Stars are visible down to Gaia magnitude {mag_txt} (half of the "
                             f"catalogue stars at that brightness are detected). {text}",
                             facts={"limit_mag": mag_txt, "depth_text": text}))
        c = self.colour
        if c:
            if c.r >= 0.6:
                hue = "neutral"
                if c.sun_offset > 0.15:
                    hue = "a little warm (red)"
                elif c.sun_offset < -0.15:
                    hue = "a little cool (blue)"
                F.append(Finding("color_calibration_ok", "colour",
                                 "good" if hue == "neutral" else "info",
                                 "Star colours follow their true colours",
                                 f"Picture star colours track Gaia colours well (r = {c.r:.2f}); "
                                 f"a Sun-like star appears {hue}."))
            elif c.r >= 0.3:
                F.append(Finding("color_calibration", "colour", "minor", "Star colours partly off",
                                 f"Star colours only loosely follow Gaia (r = {c.r:.2f}).",
                                 facts={"color_r": f"{c.r:.2f}",
                                        "color_text": "Colour calibration can be improved."}))
            else:
                F.append(Finding("color_calibration", "colour", "minor" if c.r > 0 else "major",
                                 "Star colours do not match reality",
                                 f"Star colours do not follow Gaia (r = {c.r:.2f}). With "
                                 "narrowband or dual-band data that is expected.",
                                 facts={"color_r": f"{c.r:.2f}",
                                        "color_text": "With broadband data, colour calibration "
                                                      "needs another look."}))
        t = self.target
        if t is not None and getattr(t, "target", None) is not None:
            cov = t.coverage
            if cov is not None:
                if cov > 1.3:
                    text = "The object is larger than the frame; you show a part of it."
                elif cov < 0.05:
                    text = "The object is small in the frame; a crop or longer focal length " \
                           "would show it better."
                else:
                    text = f"The object fills about {cov * 100:.0f} % of the frame width."
                F.append(Finding("framing", "presentation", "info",
                                 f"Framing of {t.target.label}", text))
        return F


def sky_checks(pic: Picture, m: Measurements, cfg, hint_name: str | None = None,
               want_survey: bool = True, progress=None) -> SkyResult:
    from advastro.sky.catalog import load
    from advastro.sky.identify import identify

    res = SkyResult()
    catalog = load()
    hint_obj = catalog.by_name(hint_name) if hint_name else None
    hint = (hint_obj.ra, hint_obj.dec) if hint_obj else None
    if progress:
        progress("solve")
    try:
        res.field = solve_picture(pic, cfg, hint)
    except SkyError as exc:
        res.errors["solve"] = str(exc)
    names = [n for n in (hint_name, pic.object_name, pic.path.stem) if n]
    res.target = identify(res.field, names)
    if res.field is None:
        return res
    tgt = getattr(res.target, "target", None)
    if tgt is not None and res.field.wcs:
        try:
            wcs = make_wcs(res.field.wcs)
            px, py = wcs.all_world2pix([tgt.ra], [tgt.dec], 0)
            res.target_xy = (float(px[0]) / pic.width, float(py[0]) / pic.height)
        except Exception:
            pass
    try:
        res.depth, res.colour, _ = depth_and_colour(m, res.field, progress)
    except SkyError as exc:
        res.errors["gaia"] = str(exc)
    except Exception as exc:  # catalogue parsing, WCS edge cases
        res.errors["gaia"] = f"{type(exc).__name__}: {exc}"
    if want_survey:
        if progress:
            progress("survey")
        try:
            survey = survey_image(res.field, pic.width, pic.height)
            res.survey, res.survey_match = orient_survey(survey, pic.luminance)
            res.survey_name = survey_for(res.field)[1]
        except SkyError as exc:
            res.errors["survey"] = str(exc)
        except Exception as exc:
            res.errors["survey"] = f"{type(exc).__name__}: {exc}"
    return res
