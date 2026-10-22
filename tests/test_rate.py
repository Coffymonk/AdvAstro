"""Rate my pic: loading, measuring, judging, sky checks (offline) and the command line."""

from __future__ import annotations

import json

import numpy as np
import pytest
import tifffile
from PIL import Image
from synthetic import star_field, write_xisf

from advastro.rate import sky as sky_mod
from advastro.rate.judge import judge, plan_for, verdict_for
from advastro.rate.measure import measure
from advastro.rate.picture import PictureError, load_picture

SHAPE = (600, 900)


def finished(seed=1, sky=0.10, noise=0.004, fwhm=2.6, ecc=0.0, cast=(0.0, 0.0, 0.0),
             gradient=0.0, n_stars=500) -> np.ndarray:
    """A stretched-looking colour picture in [0, 1], (3, h, w): stars, a soft nebula, grain."""
    rng = np.random.default_rng(seed)
    stars = star_field(SHAPE, n_stars=n_stars, fwhm_px=fwhm, eccentricity=ecc, background=0.0,
                       noise=0.0, seed=seed, peak_range=(0.08, 0.85), saturate_adu=1.0)
    h, w = SHAPE
    yy, xx = np.mgrid[0:h, 0:w]
    neb = 0.12 * np.exp(-(((xx - w * 0.55) / (w * 0.18)) ** 2 + ((yy - h * 0.5) / (h * 0.22)) ** 2))
    tint = rng.uniform(0.85, 1.15, 3)
    out = []
    for i, gain in enumerate((1.0, 0.45, 0.55)):
        ch = sky + neb * gain + stars * tint[i] + gradient * (1 - xx / w) + cast[i]
        ch = ch + rng.normal(0, noise, SHAPE)
        out.append(ch)
    return np.clip(np.stack(out), 0, 1).astype(np.float32)


def write_float_fits(path, data):
    from astropy.io import fits

    fits.PrimaryHDU(data.astype(np.float32)).writeto(path, overwrite=True)
    return path


def save_tiff(path, rgb):
    tifffile.imwrite(path, (np.moveaxis(rgb, 0, -1) * 65535 + 0.5).astype(np.uint16))
    return path


def rate(path, **profile):
    pic = load_picture(path)
    m = measure(pic)
    return judge(pic, m, {"skill": "intermediate", **profile})


@pytest.fixture(scope="module")
def good(tmp_path_factory):
    return save_tiff(tmp_path_factory.mktemp("rate") / "good.tif", finished())


# ---------------------------------------------------------------------------- loading
def test_loads_every_format(tmp_path):
    rgb = finished()
    hwc8 = (np.moveaxis(rgb, 0, -1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(hwc8).save(tmp_path / "a.jpg", quality=90)
    Image.fromarray(hwc8).save(tmp_path / "a.png")
    save_tiff(tmp_path / "a.tif", rgb)
    write_float_fits(tmp_path / "a.fits", rgb)
    write_xisf(tmp_path / "a.xisf", rgb, sample_format="Float32")
    for name, depth in (("a.jpg", "8-bit"), ("a.png", "8-bit"), ("a.tif", "16-bit"),
                        ("a.fits", "float"), ("a.xisf", "float")):
        pic = load_picture(tmp_path / name)
        assert pic.rgb.shape == (3, *SHAPE), name
        assert depth in pic.bit_depth, (name, pic.bit_depth)
        assert 0.08 < float(np.median(pic.luminance)) < 0.2, name
    assert load_picture(tmp_path / "a.jpg").jpeg_quality in range(85, 96)


def test_rejects_unsupported_and_tiny(tmp_path):
    (tmp_path / "x.txt").write_text("hi")
    with pytest.raises(PictureError):
        load_picture(tmp_path / "x.txt")
    Image.fromarray(np.zeros((20, 20, 3), np.uint8)).save(tmp_path / "tiny.png")
    with pytest.raises(PictureError):
        load_picture(tmp_path / "tiny.png")


def test_16bit_file_holding_8bit_data_is_seen_as_8bit(tmp_path):
    rgb8 = np.round(finished() * 255) / 255
    pic = load_picture(save_tiff(tmp_path / "padded.tif", rgb8))
    assert pic.levels == 256


# ---------------------------------------------------------------------------- measuring
def test_good_picture_measures_clean(good):
    m = measure(load_picture(good))
    assert not m.linear
    assert abs(m.sky - 0.10) < 0.02
    assert m.star_count > 200
    assert 2.0 < m.fwhm < 4.0
    assert m.ellipticity < 0.25
    assert m.gradient_pct < 4
    assert m.hot_pixels == 0
    assert not m.edges


def test_detects_typical_processing_faults(tmp_path):
    rgb = finished(gradient=0.08, cast=(0.0, 0.03, 0.0))
    rgb[:, :, :40] = 0                                   # uncropped stacking edge
    rng = np.random.default_rng(3)
    ys, xs = rng.integers(30, 570, 80), rng.integers(60, 870, 80)
    rgb[0, ys, xs] = 1.0                                 # hot pixels
    r = rate(save_tiff(tmp_path / "bad.tif", rgb))
    ids = {f.id for f in r.issues}
    assert {"gradient", "green_cast", "edges", "hot_pixels"} <= ids
    assert r.verdict in ("fixable", "needs_work")
    m = r.measurements
    assert "left" in m.edges
    assert m.hot_pixels >= 60


def test_trailed_stars_and_rings(tmp_path):
    r = rate(save_tiff(tmp_path / "trail.tif", finished(ecc=0.9, fwhm=3.5)))
    assert any(f.id == "trailed_stars" for f in r.issues)
    sharp = finished()
    from scipy import ndimage as ndi

    blur = np.stack([ndi.gaussian_filter(c, 2.0) for c in sharp])
    r2 = rate(save_tiff(tmp_path / "sharp.tif", np.clip(sharp + 2.5 * (sharp - blur), 0, 1)))
    assert r2.measurements.ring_fraction > 0.2
    assert any(f.id == "star_rings" for f in r2.issues)


def test_linear_data_is_recognised(tmp_path):
    lin = finished(sky=0.004, noise=0.0004) * 0.08
    write_float_fits(tmp_path / "lin.fits", lin)
    r = rate(tmp_path / "lin.fits")
    assert r.measurements.linear
    assert r.verdict == "needs_work"
    assert r.issues[0].id == "linear"


def test_banding_and_jpeg(tmp_path):
    q = np.round(finished(noise=0.001) * 255) / 255
    restretched = np.clip((q - 0.08) * 3.0, 0, 1)
    hwc = (np.moveaxis(restretched, 0, -1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(hwc).save(tmp_path / "band.png")
    r = rate(tmp_path / "band.png")
    assert r.measurements.comb_pct > 20
    assert any(f.id == "banding" for f in r.issues)
    hwc = (np.moveaxis(finished(), 0, -1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(hwc).save(tmp_path / "low.jpg", quality=30)
    r2 = rate(tmp_path / "low.jpg")
    assert r2.measurements.jpeg_quality < 45
    assert any(f.id == "jpeg" for f in r2.issues)


# ---------------------------------------------------------------------------- judging
def test_good_beats_flawed(good, tmp_path):
    a = rate(good)
    b = rate(save_tiff(tmp_path / "noisy.tif", finished(noise=0.03, gradient=0.1)))
    assert a.score > b.score + 10
    assert a.verdict in ("excellent", "ready")
    assert {"noise", "gradient"} <= {f.id for f in b.issues}


def test_verdict_depends_on_skill_and_majors():
    assert verdict_for(88, "beginner") == "excellent"
    assert verdict_for(88, "advanced") == "ready"
    from advastro.rate.judge import Finding

    major = [Finding("x", "stars", "major", "t", "t")]
    assert verdict_for(99, "intermediate", major) == "fixable"


def test_plan_is_tailored_and_complete(tmp_path):
    r = rate(save_tiff(tmp_path / "n.tif", finished(noise=0.03)),
             software=["PixInsight", "Siril"], paid_addons=["NoiseXTerminator"])
    step = next(s for s in r.plan if s.finding.id == "noise")
    assert "NoiseXTerminator" in " ".join(step.steps["PixInsight"])
    assert step.steps["Siril"]
    for s in r.plan:                       # every placeholder was filled in
        text = s.why + " ".join(x for v in s.steps.values() for x in v)
        assert "{" not in text and "?" not in text.replace("? ", ""), (s.finding.id, text)
    steps, _ = plan_for(r.findings, r.measurements, ["Siril"], [])
    assert all(set(s.steps) <= {"Siril"} for s in steps)


# ---------------------------------------------------------------------------- sky (offline)
def _wcs(w, h, scale_deg=0.0005):
    return {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": 150.0, "CRVAL2": 30.0,
            "CRPIX1": w / 2 + 0.5, "CRPIX2": h / 2 + 0.5, "CD1_1": -scale_deg, "CD1_2": 0.0,
            "CD2_1": 0.0, "CD2_2": scale_deg}


def test_depth_and_colour_against_a_fake_catalogue(good, monkeypatch):
    from advastro.sky.solve import SkyField

    pic = load_picture(good)
    m = measure(pic)
    w, h = pic.width, pic.height
    wcs = sky_mod.make_wcs(_wcs(w, h))
    det = m.detections
    # Catalogue: every detected star, brighter = smaller magnitude, plus faint stars
    # that the picture does not show.
    order = np.argsort(-det[:, 2])
    ra, dec = wcs.all_pix2world(det[order, 0], det[order, 1], 0)
    mags = np.linspace(9, 16, len(order))
    rng = np.random.default_rng(0)
    fra, fdec = wcs.all_pix2world(rng.uniform(20, w - 20, 900), rng.uniform(20, h - 20, 900), 0)
    cat = np.vstack([np.column_stack([ra, dec, mags, np.full(len(order), np.nan)]),
                     np.column_stack([fra, fdec, rng.uniform(16.5, 19, 900),
                                      np.full(900, np.nan)])])
    monkeypatch.setattr(sky_mod, "gaia_stars", lambda *a, **k: cat)
    field = SkyField(ra=150, dec=30, width_deg=w * 0.0005, height_deg=h * 0.0005,
                     scale_arcsec=1.8, rotation_deg=0, level="solved", source="test",
                     wcs=_wcs(w, h))
    depth, colour, _ = sky_mod.depth_and_colour(m, field)
    assert depth is not None and 15.5 < depth.limit_mag < 17.0


def test_survey_request_matches_the_picture_grid(monkeypatch):
    from advastro.sky.solve import SkyField

    calls = {}

    def fake_get(url, timeout=0):
        calls["url"] = url
        import io

        buf = io.BytesIO()
        Image.fromarray(np.zeros((450, 800, 3), np.uint8)).save(buf, format="PNG")
        return buf.getvalue()

    monkeypatch.setattr(sky_mod, "_get", fake_get)
    field = SkyField(ra=150, dec=30, width_deg=2.0, height_deg=1.1, scale_arcsec=1.8,
                     rotation_deg=0, level="solved", source="test", wcs=_wcs(4000, 2250))
    img = sky_mod.survey_image(field, 4000, 2250, max_side=800)
    assert img.shape == (450, 800, 3)
    from urllib.parse import parse_qs, urlsplit

    q = parse_qs(urlsplit(calls["url"]).query)
    wcs = json.loads(q["wcs"][0])
    assert (wcs["NAXIS1"], wcs["NAXIS2"]) == (800, 450)
    assert abs(wcs["CD2_2"] - 0.0005 * 5) < 1e-9
    assert q["hips"][0] == "CDS/P/DSS2/color"


def test_survey_orientation_is_found_from_the_stars(good):
    pic = load_picture(good)
    lum = pic.luminance
    small = lum[::2, ::2]
    survey = np.repeat(small[::-1, :, None], 3, axis=-1)        # delivered upside down
    fixed, score = sky_mod.orient_survey(survey, lum)
    assert score > 0.3
    assert np.allclose(fixed[..., 0], small)


def test_astrobin_results_are_parsed_and_sorted(monkeypatch):
    payload = {"objects": [
        {"hash": "abc", "title": "M31 HaRGB", "user": "anna", "likes": 12,
         "url_thumb": "https://x/t1.jpg"},
        {"id": 77, "title": "Andromeda", "user": "bo", "likes": 40, "url_gallery": "https://x/t2"},
    ]}
    monkeypatch.setattr(sky_mod, "_get", lambda url, timeout=0: json.dumps(payload).encode())
    found = sky_mod.astrobin_images("M31", "k", "s")
    assert [f.author for f in found] == ["bo", "anna"]
    assert found[0].url == "https://www.astrobin.com/77/"
    links = dict(sky_mod.browser_links("NGC 7000"))
    assert "NGC+7000" in links["AstroBin"]


# ---------------------------------------------------------------------------- command line
def test_cli_rate_json(good, capsys):
    from advastro.cli import main

    assert main(["rate", str(good), "-f", "json", "--no-user-config"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["kind"] == "rate-my-pic"
    assert set(data["categories"]) >= {"stars", "background", "colour"}
    assert 0 <= data["score"] <= 100


def test_pdf_report(good, tmp_path):
    pytest.importorskip("PySide6")
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])  # noqa: F841
    from advastro.rate.pdf import write_pdf

    out = write_pdf(rate(good), tmp_path / "r.pdf")
    assert out.read_bytes()[:4] == b"%PDF" and out.stat().st_size > 20_000


# ---------------------------------------------------------------------------- object types
def test_starless_pictures_are_recognised_and_skip_star_checks(tmp_path):
    from scipy import ndimage as ndi

    from advastro.rate.objects import looks_starless

    rgb = finished(n_stars=900)
    starless = np.stack([ndi.grey_opening(c, size=(9, 9)) for c in rgb])
    path = save_tiff(tmp_path / "starless.tif", starless)
    pic = load_picture(path)
    m = measure(pic)
    assert looks_starless(m)
    r = judge(pic, m, {"skill": "intermediate"})
    assert r.context.starless and "stars" not in r.categories
    assert any(f.id == "starless" for f in r.findings)
    assert not any(f.category == "stars" and f.id != "starless" for f in r.findings)
    # A normal star field is not starless, and the choice can be overridden.
    pic2 = load_picture(save_tiff(tmp_path / "stars.tif", rgb))
    m2 = measure(pic2)
    assert not looks_starless(m2)
    forced = judge(pic2, m2, {}, starless="yes")
    assert forced.context.starless and forced.context.starless_source == "manual"


def test_object_type_changes_the_judgement(good):
    pic = load_picture(good)
    m = measure(pic)
    plain = judge(pic, m, {})
    assert plain.context.kind == "unknown"
    named = judge(pic, m, {}, object_name="M 31")
    assert named.context.kind == "galaxy" and named.context.kind_source == "name"
    cluster = judge(pic, m, {}, object_kind="cluster")
    assert cluster.context.kind == "cluster"
    assert not any(f.id in ("muted", "low_contrast", "low_detail", "star_dominance")
                   for f in cluster.findings)
    neb = judge(pic, m, {}, object_name="NGC 7000")
    assert neb.context.kind == "emission" and neb.context.fills_frame


def test_target_workflow_and_mask_recipes(good):
    from advastro.rate.judge import _load_tips, load_masks
    from advastro.rate.workflow import target_workflow, workflow_markdown

    masks = load_masks()
    for key, entry in _load_tips().items():
        for name in entry.get("masks", []):
            assert name in masks, (key, name)
    for m in masks.values():
        assert m["pixinsight"] and m["siril"] and m["title"]
    pic = load_picture(good)
    meas = measure(pic)
    for kind in ("galaxy", "emission", "cluster", "globular", "milkyway", "auto"):
        r = judge(pic, meas, {}, object_kind=kind)
        for tool in ("PixInsight", "Siril"):
            wf = target_workflow(r, tool, ["BlurXTerminator"])
            assert len(wf.stages) >= 8 and all(s.steps for s in wf.stages)
            ids = [s.id for s in wf.stages]
            if kind in ("cluster", "globular"):
                assert "stars_off" not in ids and "cluster_stars" in ids
            text = workflow_markdown(wf, tool)
            assert "{" not in text, text[:200]
    r = judge(pic, meas, {}, object_kind="galaxy", starless="yes")
    assert "stars_on" not in [s.id for s in target_workflow(r).stages]
