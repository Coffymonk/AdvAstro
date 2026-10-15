"""Synthetic star fields with known properties, for testing metrics in isolation."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from astropy.io import fits

SIGMA_TO_FWHM = 2.0 * math.sqrt(2.0 * math.log(2.0))


def star_field(
    shape=(512, 512),
    n_stars=120,
    fwhm_px=3.0,
    eccentricity=0.0,
    background=1000.0,
    noise=10.0,
    seed=1,
    peak_range=(300.0, 8000.0),
    saturate_adu=65535.0,
) -> np.ndarray:
    """Gaussian stars (optionally elongated along x) on a flat background with Gaussian noise."""
    rng = np.random.default_rng(seed)
    h, w = shape
    img = np.full(shape, background, dtype=np.float64)
    sigma = fwhm_px / SIGMA_TO_FWHM
    # Elongation keeps the geometric-mean FWHM equal to fwhm_px.
    ratio = math.sqrt(1.0 - eccentricity ** 2)  # b / a
    sx, sy = sigma / math.sqrt(ratio), sigma * math.sqrt(ratio)
    yy, xx = np.mgrid[0:h, 0:w]
    margin = 20
    for _ in range(n_stars):
        x = rng.uniform(margin, w - margin)
        y = rng.uniform(margin, h - margin)
        peak = rng.uniform(*peak_range)
        r = int(6 * max(sx, sy)) + 2
        y0, y1, x0, x1 = int(y) - r, int(y) + r + 1, int(x) - r, int(x) + r + 1
        sub_y, sub_x = yy[y0:y1, x0:x1], xx[y0:y1, x0:x1]
        img[y0:y1, x0:x1] += peak * np.exp(
            -0.5 * (((sub_x - x) / sx) ** 2 + ((sub_y - y) / sy) ** 2))
    img += rng.normal(0.0, noise, shape)
    return np.clip(img, 0, saturate_adu)


def write_fits(path: Path, data: np.ndarray, **header) -> Path:
    hdr = fits.Header()
    defaults = {"IMAGETYP": "Light Frame", "EXPTIME": 300.0, "FILTER": "L",
                "XPIXSZ": 2.9, "FOCALLEN": 350.0, "GAIN": 201,
                "DATE-OBS": "2026-10-14T21:00:00.000"}
    for key, value in {**defaults, **header}.items():
        if value is not None:
            hdr[key] = value
    fits.PrimaryHDU(np.round(data).astype(np.uint16), header=hdr).writeto(path, overwrite=True)
    return path


def write_xisf(path: Path, data: np.ndarray, compression: str | None = None,
               shuffle: bool = False, keywords: dict | None = None,
               properties: dict | None = None, cfa: str | None = None,
               sample_format: str = "UInt16", normal_storage: bool = False) -> Path:
    """Minimal XISF 1.0 writer, used only to test the reader."""
    import struct
    import zlib

    dtype = {"UInt16": np.uint16, "Float32": np.float32, "UInt8": np.uint8}[sample_format]
    arr = data if data.ndim == 3 else data[None]
    channels, height, width = arr.shape
    if sample_format == "Float32":
        arr = (arr / max(float(arr.max()), 1.0)).astype("<f4")
    else:
        arr = np.round(arr).astype(np.dtype(dtype).newbyteorder("<"))
    if normal_storage:
        arr = np.ascontiguousarray(arr.transpose(1, 2, 0))
    raw = arr.tobytes()
    item = arr.dtype.itemsize
    attrs = ""
    if compression:
        payload = raw
        if shuffle:
            b = np.frombuffer(raw, np.uint8)
            n = len(b) // item
            payload = b[: n * item].reshape(n, item).T.tobytes() + b[n * item:].tobytes()
        if compression == "zlib":
            block = zlib.compress(payload)
        elif compression == "lz4":
            import lz4.block
            block = lz4.block.compress(payload, store_size=False)
        else:
            import zstandard
            block = zstandard.ZstdCompressor().compress(payload)
        codec = compression + ("+sh" if shuffle else "")
        attrs = f' compression="{codec}:{len(raw)}' + (f':{item}"' if shuffle else '"')
    else:
        block = raw
    children = ""
    for k, v in (keywords or {}).items():
        val = f"'{v}'" if isinstance(v, str) else str(v)
        children += f'<FITSKeyword name="{k}" value="{val}" comment=""/>'
    for k, v in (properties or {}).items():
        children += f'<Property id="{k}" type="Float64" value="{v}"/>'
    if cfa:
        children += f'<ColorFilterArray pattern="{cfa}" width="2" height="2"/>'
    storage = ' pixelStorage="Normal"' if normal_storage else ""
    color = "RGB" if channels == 3 else "Gray"

    def header(pos: int) -> bytes:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<xisf version="1.0" xmlns="http://www.pixinsight.com/xisf">'
            f'<Image geometry="{width}:{height}:{channels}" sampleFormat="{sample_format}" '
            f'colorSpace="{color}" location="attachment:{pos}:{len(block)}"{attrs}{storage}>'
            f'{children}</Image></xisf>').encode()

    pos = 0
    for _ in range(3):  # the header length depends on the position digits
        xml = header(pos)
        pos = 16 + len(xml)
    xml = header(pos)
    with open(path, "wb") as fh:
        fh.write(b"XISF0100" + struct.pack("<I", len(xml)) + b"\0" * 4 + xml + block)
    return path


def dark_frame(shape=(400, 600), level=1120.0, noise=18.0, hot=60, glow=0.0, seed=0,
               step=16):
    """A dark/bias frame: offset level, read noise, hot pixels and optional amp glow
    on the left edge, quantized like a 12-bit ADC scaled to 16 bits."""
    rng = np.random.default_rng(seed)
    h, w = shape
    img = level + rng.normal(0, noise, shape)
    if glow:
        x = np.arange(w)
        img += glow * np.exp(-x / (0.05 * w))[None, :]
    ys, xs = rng.integers(0, h, hot), rng.integers(0, w, hot)
    img[ys, xs] = level + rng.uniform(800, 6000, hot)
    return np.clip(np.round(img / step) * step, 0, 65535)


def flat_frame(shape=(400, 600), level=24000.0, vignetting=0.15, dust=(), seed=0):
    """A flat: radial vignetting (fraction lost in the corners) and dust shadows
    given as (x, y, radius, depth) tuples."""
    rng = np.random.default_rng(seed)
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)) / np.sqrt(2)
    img = level * (1 - vignetting * r ** 2)
    for x, y, rad, depth in dust:
        d = np.hypot(xx - x, yy - y)
        img *= 1 - depth * np.exp(-0.5 * (d / rad) ** 2)
    img += rng.normal(0, np.sqrt(level) * 0.5, shape)
    return np.clip(img, 0, 65535)
