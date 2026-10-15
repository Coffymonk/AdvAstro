import math

import pytest
from synthetic import star_field, write_fits

from advastro.engine.metrics import measure_frame
from advastro.readers import read_frame


@pytest.mark.parametrize("fwhm", [2.5, 3.5, 5.0])
def test_fwhm_recovered_within_5_percent(tmp_path, fwhm):
    path = write_fits(tmp_path / "sub.fits", star_field(fwhm_px=fwhm, seed=3))
    m = measure_frame(read_frame(path))
    assert m.fwhm_px == pytest.approx(fwhm, rel=0.05)


def test_fwhm_arcsec_uses_header_scale(tmp_path):
    path = write_fits(tmp_path / "sub.fits", star_field(fwhm_px=3.0))
    m = measure_frame(read_frame(path))
    scale = 206.264806 * 2.9 / 350.0  # RedCat 71 + ASI585
    assert m.pixel_scale_arcsec == pytest.approx(scale, rel=1e-6)
    assert m.fwhm_arcsec == pytest.approx(m.fwhm_px * scale)


def test_round_stars_have_low_eccentricity(tmp_path):
    path = write_fits(tmp_path / "sub.fits", star_field(eccentricity=0.0))
    assert measure_frame(read_frame(path)).eccentricity < 0.25


def test_elongated_stars_detected(tmp_path):
    path = write_fits(tmp_path / "sub.fits", star_field(fwhm_px=4.0, eccentricity=0.7))
    assert measure_frame(read_frame(path)).eccentricity == pytest.approx(0.7, abs=0.06)


def test_noise_and_background(tmp_path):
    path = write_fits(tmp_path / "sub.fits", star_field(background=1500, noise=12))
    m = measure_frame(read_frame(path))
    assert m.background_adu == pytest.approx(1500, rel=0.01)
    assert m.noise_adu == pytest.approx(12, rel=0.10)


def test_star_count_close_to_truth(tmp_path):
    path = write_fits(tmp_path / "sub.fits", star_field(n_stars=120, seed=9))
    count = measure_frame(read_frame(path)).star_count
    assert 100 <= count <= 125  # a few blends are expected


def test_saturation_reported(tmp_path):
    data = star_field(peak_range=(30000, 90000))
    path = write_fits(tmp_path / "sub.fits", data)
    m = measure_frame(read_frame(path))
    assert m.saturated_fraction > 0
    assert any("saturation" in w for w in m.warnings)
    assert m.fwhm_px is not None and math.isfinite(m.fwhm_px)  # clipped stars are skipped


def test_osc_cfa_measured_in_native_pixels(tmp_path):
    path = write_fits(tmp_path / "osc.fits", star_field(shape=(600, 600), fwhm_px=5.0),
                      BAYERPAT="RGGB")
    m = measure_frame(read_frame(path))
    assert m.fwhm_px == pytest.approx(5.0, rel=0.12)  # 2x2 binning costs some precision
