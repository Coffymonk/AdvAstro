import json
import shutil
from pathlib import Path

import pytest
from synthetic import star_field, write_fits

from advastro.cli import main
from advastro.config import load_config
from advastro.engine.session import analyze_paths, summarize
from advastro.integrations.miklosoft import load_mksession, load_mktargets
from advastro.readers import find_frames

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def session(tmp_path):
    """Eight good subs, one blurred, one cloudy, one with trailed stars."""
    for i in range(8):
        write_fits(tmp_path / f"light_{i:03d}.fits", star_field(fwhm_px=3.0, seed=i))
    write_fits(tmp_path / "light_100_blurred.fits", star_field(fwhm_px=5.5, seed=20))
    write_fits(tmp_path / "light_101_cloudy.fits", star_field(n_stars=30, seed=21))
    write_fits(tmp_path / "light_102_trailed.fits",
               star_field(fwhm_px=4.0, eccentricity=0.8, seed=22))
    return tmp_path


def test_session_flags_the_bad_subs(session):
    subs, errors = analyze_paths(find_frames(session), jobs=1)
    summary = summarize(subs, errors=errors)
    assert not errors
    flagged = summary.flagged_files()
    assert "light_100_blurred.fits" in flagged
    assert "light_101_cloudy.fits" in flagged
    assert "light_102_trailed.fits" in flagged
    assert not any(f.startswith("light_00") for f in flagged)
    assert summary.sampling == "well sampled"


def test_cli_json_report(session, tmp_path):
    out = tmp_path / "report.json"
    code = main(["analyze", str(session), "-f", "json", "-o", str(out), "-q", "-j", "2",
                 "--no-user-config"])
    assert code == 0
    report = json.loads(out.read_text("utf-8"))
    assert len(report["subs"]) == 11
    assert report["pixel_scale_source"] == "FITS headers"
    assert {f["file"] for f in report["flags"]} >= {"light_101_cloudy.fits"}


def test_cli_table_runs(session, capsys):
    assert main(["analyze", str(session), "-q", "-j", "1", "--no-user-config"]) == 0
    text = capsys.readouterr().out
    assert "light_100_blurred.fits" in text and "!" in text


def test_scale_falls_back_to_mksession(tmp_path):
    for i in range(3):
        write_fits(tmp_path / f"s{i}.fits", star_field(seed=i), XPIXSZ=None, FOCALLEN=None)
    shutil.copy(FIXTURES / "session-2026-10-14.mksession", tmp_path)
    out = tmp_path / "r.json"
    main(["analyze", str(tmp_path), "-f", "json", "-o", str(out), "-q", "-j", "1",
          "--no-user-config"])
    report = json.loads(out.read_text("utf-8"))
    assert report["pixel_scale_arcsec"] == pytest.approx(1.709, abs=0.001)
    assert report["pixel_scale_source"] == "session-2026-10-14.mksession"


def test_config_layering_and_warnings(tmp_path):
    (tmp_path / "advastro.toml").write_text(
        "[reject]\nfwhm_sigma = 2\nbogus = 1\n[measure]\ndetect_sigma = 'high'\n")
    extra = tmp_path / "mine.toml"
    extra.write_text("[reject]\nfwhm_sigma = 2.5\n")
    cfg = load_config(tmp_path, [extra], ["profile.skill=advanced"], use_user_config=False)
    assert cfg.get("reject", "fwhm_sigma") == 2.5
    assert cfg.sources["reject.fwhm_sigma"] == str(extra)
    assert cfg.get("profile", "skill") == "advanced"
    assert cfg.get("measure", "detect_sigma") == 5.0  # wrong type ignored
    assert any("bogus" in w for w in cfg.warnings)
    assert any("detect_sigma" in w for w in cfg.warnings)


def test_mksession_reader_catches_flat_exposure_bug():
    s = load_mksession(FIXTURES / "session-2026-10-14.mksession")
    assert s.gear.pixel_scale_arcsec == pytest.approx(1.709, abs=0.001)
    w, h = s.gear.field_arcmin
    assert w == pytest.approx(109.4, abs=0.2) and h == pytest.approx(61.5, abs=0.2)
    flat = next(e for e in s.entries if e.kind == "flat")
    assert flat.exposure_s is None and flat.warnings
    lights = next(e for e in s.entries if e.type == "lights")
    assert lights.exposure_s == 300 and lights.count == 40


def test_mktargets_reader():
    targets, gear = load_mktargets(FIXTURES / "targets-2026-10-15.mktargets")
    assert targets[0].id == "NGC 7380" and "Sh2-142" in targets[0].aliases
    assert gear.focal_length_mm == 350


def _shifted_session(tmp_path, shifts):
    import numpy as np
    base = star_field(shape=(300, 400), n_stars=70, seed=5, noise=6)
    for i, (dx, dy) in enumerate(shifts):
        img = np.roll(np.roll(base, dy, axis=0), dx, axis=1)
        write_fits(tmp_path / f"s{i:02d}.fits", img,
                   **{"DATE-OBS": f"2026-10-14T21:{i:02d}:00.000"})
    subs, _ = analyze_paths(find_frames(tmp_path), jobs=1)
    return summarize(subs)


def test_dithering_detected(tmp_path):
    s = _shifted_session(tmp_path, [(0, 0), (9, -4), (-6, 7), (12, 3), (-3, -10), (5, 8)])
    assert s.dithered is True and s.dither_px > 5
    assert s.subs[1].offset_px == pytest.approx((9, -4), abs=0.3)


def test_steady_drift_is_not_dithering(tmp_path):
    s = _shifted_session(tmp_path, [(i, i // 2) for i in range(0, 12, 2)])
    assert s.dithered is False
    assert s.drift_px == pytest.approx(11.2, abs=1.0)


def test_save_user_config_round_trip(tmp_path):
    from advastro.config import save_user_config

    path = tmp_path / "cfg" / "config.toml"
    path.parent.mkdir()
    path.write_text("[custom]\nmine = 1\n[reject]\nfwhm_sigma = 2.0\n")
    save_user_config({"reject": {"eccentricity_max": 0.5},
                      "profile": {"software": ["Siril"], "aesthetic": "HOO"}}, path)
    import tomllib
    data = tomllib.loads(path.read_text())
    assert data["custom"]["mine"] == 1 and data["reject"]["fwhm_sigma"] == 2.0
    assert data["reject"]["eccentricity_max"] == 0.5 and data["profile"]["software"] == ["Siril"]
    cfg = load_config(extra_files=[path], use_user_config=False)
    assert cfg.get("profile", "aesthetic") == "HOO"
