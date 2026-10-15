import numpy as np
import pytest
from synthetic import star_field, write_fits, write_xisf

from advastro.engine.metrics import measure_frame
from advastro.readers import read_frame


@pytest.fixture(scope="module")
def image():
    return np.round(star_field(shape=(120, 200), n_stars=30, seed=4))


@pytest.mark.parametrize("compression,shuffle", [
    (None, False), ("zlib", False), ("zlib", True), ("lz4", True), ("zstd", True)])
def test_pixels_identical_for_every_compression(tmp_path, image, compression, shuffle):
    path = write_xisf(tmp_path / "a.xisf", image, compression, shuffle)
    frame = read_frame(path)
    assert frame.format == "xisf"
    assert frame.data.shape == image.shape
    np.testing.assert_array_equal(frame.data, image.astype(np.float32))
    assert frame.meta.saturation_adu == 65535.0


def test_normal_pixel_storage_and_rgb(tmp_path, image):
    rgb = np.stack([image, image * 0.5, image * 0.25])
    path = write_xisf(tmp_path / "rgb.xisf", np.round(rgb), normal_storage=True)
    frame = read_frame(path)
    np.testing.assert_array_equal(frame.data, np.round(rgb).astype(np.float32))


def test_keywords_properties_and_cfa(tmp_path, image):
    path = write_xisf(
        tmp_path / "meta.xisf", image,
        keywords={"IMAGETYP": "Light Frame", "EXPTIME": 300.0, "FILTER": "Dual",
                  "GAIN": 201},
        properties={"Instrument:Telescope:FocalLength": 0.35,
                    "Instrument:Sensor:XPixelSize": 2.9},
        cfa="RGGB")
    m = read_frame(path).meta
    assert (m.image_type, m.exposure_s, m.filter_name, m.gain) == ("light", 300.0, "Dual", 201)
    assert m.focal_length_mm == pytest.approx(350.0)
    assert m.pixel_size_um == pytest.approx(2.9)
    assert m.bayer_pattern == "RGGB"
    assert m.pixel_scale_arcsec == pytest.approx(1.709, abs=0.001)


def test_float_images_are_normalized(tmp_path, image):
    m = read_frame(write_xisf(tmp_path / "f.xisf", image, sample_format="Float32")).meta
    assert m.saturation_adu == 1.0


def test_same_metrics_as_fits(tmp_path):
    data = star_field(shape=(300, 400), n_stars=80, fwhm_px=3.0, seed=2)
    a = measure_frame(read_frame(write_fits(tmp_path / "s.fits", data)))
    b = measure_frame(read_frame(write_xisf(tmp_path / "s.xisf", data, "zlib", True,
                                            keywords={"XPIXSZ": 2.9, "FOCALLEN": 350.0})))
    assert b.fwhm_px == pytest.approx(a.fwhm_px, rel=1e-6)
    assert b.star_count == a.star_count


def test_not_xisf(tmp_path):
    bad = tmp_path / "bad.xisf"
    bad.write_bytes(b"hello world, definitely not xisf")
    with pytest.raises(ValueError):
        read_frame(bad)
