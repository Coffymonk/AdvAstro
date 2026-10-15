import pytest
from synthetic import dark_frame, flat_frame, write_fits

from advastro.engine.calibration import (
    analyze_calibration,
    measure_calibration,
    summarize_calibration,
)
from advastro.frame import FrameMeta
from advastro.readers import read_frame
from advastro.session_context import find_calibration


def cal(path, data, kind, **hdr):
    defaults = {"IMAGETYP": kind, "EXPTIME": 300.0, "GAIN": 201, "OFFSET": 15,
                "CCD-TEMP": -10.0, "XBINNING": 1}
    return write_fits(path, data, **{**defaults, **hdr})


def test_dark_metrics(tmp_path):
    p = cal(tmp_path / "d.fits", dark_frame(hot=120, noise=18, glow=300), "Dark")
    m = measure_calibration(read_frame(p), "darks")
    assert m.median_adu == pytest.approx(1120, abs=16)
    assert m.noise_adu == pytest.approx(18, rel=0.25)  # not stuck at the 16 ADU step
    assert 100 <= m.hot_pixels <= 140
    assert m.glow_where in ("left edge", "top left", "bottom left") and m.glow_adu > 50


def test_flat_metrics(tmp_path):
    data = flat_frame(vignetting=0.2, dust=[(200, 150, 9, 0.06), (420, 260, 12, 0.05)])
    m = measure_calibration(read_frame(cal(tmp_path / "f.fits", data, "Flat", EXPTIME=2.0)),
                            "flats")
    assert m.level_pct == pytest.approx(34.5, abs=2)  # median of a vignetted flat
    assert 5 < m.vignetting_pct < 25
    assert m.dust_spots == 2 and m.dust_depth_pct > 3


def _session(tmp_path, dark_kw=None, leak=False):
    root = tmp_path / "session"
    for name in ("DARK", "FLAT", "FLAT DARK", "BIAS"):
        (root / name).mkdir(parents=True)
    for i in range(6):
        level = 1120 + (400 if leak and i == 5 else 0)
        cal(root / "DARK" / f"dark_{i}.fits", dark_frame(level=level, seed=i), "Dark",
            **(dark_kw or {}))
        cal(root / "FLAT" / f"flat_{i}.fits", flat_frame(seed=i), "Flat", EXPTIME=2.0)
        cal(root / "FLAT DARK" / f"fd_{i}.fits", dark_frame(seed=10 + i), "Flat",
            EXPTIME=2.0)  # ASIAIR labels flat darks "Flat"
        cal(root / "BIAS" / f"bias_{i}.fits", dark_frame(seed=20 + i), "Bias", EXPTIME=0.001)
    files = find_calibration(root).all_files()
    metrics, errors = analyze_calibration(files, jobs=1)
    lights = FrameMeta(exposure_s=300.0, gain=201, offset=15, temperature_c=-10.0, binning=1)
    return summarize_calibration(metrics, lights, "2026-10-14T21:00:00", errors)


def test_session_checks_all_good(tmp_path):
    s = _session(tmp_path)
    assert set(s.groups) == {"darks", "flats", "darkflats", "bias"}
    texts = " ".join(n.text for n in s.notes)
    assert "Darks match the lights" in texts and "Flat darks match the flats" in texts
    assert "labelled 'flat'" in texts  # header said Flat, folder said flat darks
    assert not any(n.level == "bad" for n in s.notes)


def test_mismatched_darks_and_light_leak(tmp_path):
    s = _session(tmp_path, dark_kw={"EXPTIME": 120.0, "GAIN": 100}, leak=True)
    bad = [n.text for n in s.notes if n.level == "bad"]
    assert any("exposure 120 s vs lights 300 s" in t and "gain 100" in t for t in bad)
    assert "dark_5.fits" in s.groups["darks"].flagged_files()
    assert any("light reaching the sensor" in n.text for n in s.notes)
