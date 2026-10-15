"""Load a finished astrophoto in any common format as normalized RGB.

Finished pictures arrive as FITS or XISF straight from PixInsight or Siril, as 16-bit
TIFF from DeepSkyStacker, Astro Pixel Processor or Photoshop, or as JPEG, PNG and WebP
for sharing. All of them become a Picture: float32 data in [0, 1], shape (3, h, w)
(mono pictures repeat one plane), plus what the file says about how it was saved.

Array row 0 is FITS pixel y = 1, the same convention the rest of AdvAstro uses, so a
plate solution of the picture maps straight onto the array.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

RASTER = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".jfif"}
TIFF = {".tif", ".tiff"}
ASTRO = {".fits", ".fit", ".fts", ".xisf"}
SUPPORTED = RASTER | TIFF | ASTRO


@dataclass
class Picture:
    path: Path
    rgb: np.ndarray                  # float32 (3, h, w) in [0, 1]
    mono: bool
    format: str                      # jpeg, png, tiff, fits, xisf, ...
    bit_depth: str                   # "8-bit", "16-bit", "32-bit float", ...
    levels: int | None               # distinct levels per channel the file can hold
    header: dict = field(default_factory=dict)   # FITS keywords, when there are any
    software: str | None = None
    jpeg_quality: int | None = None  # estimated from the quantization tables
    icc: str | None = None           # colour profile description
    object_name: str | None = None

    @property
    def width(self) -> int:
        return self.rgb.shape[2]

    @property
    def height(self) -> int:
        return self.rgb.shape[1]

    @property
    def luminance(self) -> np.ndarray:
        if self.mono:
            return self.rgb[0]
        r, g, b = self.rgb
        return (0.2126 * r + 0.7152 * g + 0.0722 * b).astype(np.float32)


class PictureError(ValueError):
    pass


def _to_unit(data: np.ndarray) -> tuple[np.ndarray, str, int | None]:
    """Scale integer or float samples to [0, 1]. Returns data, bit-depth label, levels."""
    kind = data.dtype.kind
    if kind == "b":
        return data.astype(np.float32), "1-bit", 2
    if kind in "ui":
        bits = data.dtype.itemsize * 8
        info = np.iinfo(data.dtype)
        out = (data.astype(np.float64) - info.min) / (info.max - info.min) \
            if kind == "i" else data.astype(np.float64) / info.max
        # 16-bit containers that only hold 8-bit values (common after conversions)
        return out.astype(np.float32), f"{bits}-bit", 2 ** bits
    out = data.astype(np.float32)
    finite = np.isfinite(out)
    if not finite.all():
        out = np.where(finite, out, 0).astype(np.float32)
    lo, hi = float(out.min()), float(out.max())
    label = f"{data.dtype.itemsize * 8}-bit float"
    if lo >= -1e-3 and hi <= 1.0 + 1e-3:
        return np.clip(out, 0, 1), label, None
    # Not normalized (some FITS writers store 0–65535 as float): rescale to the data range.
    scale = 65535.0 if hi <= 65535.5 and lo >= -0.5 and hi > 255.5 else (
        255.0 if hi <= 255.5 and lo >= -0.5 else hi)
    return np.clip((out - min(lo, 0)) / max(scale - min(lo, 0), 1e-12), 0, 1), label, None


def _planes(data: np.ndarray, channels_last: bool) -> np.ndarray:
    """(3, h, w) or (1, h, w) from any common layout."""
    if data.ndim == 2:
        return data[None]
    if channels_last:
        data = np.moveaxis(data, -1, 0)
    if data.shape[0] == 4:          # RGBA / CMYK-less alpha: drop alpha
        data = data[:3]
    if data.shape[0] == 2:          # grey + alpha
        data = data[:1]
    if data.shape[0] not in (1, 3):
        raise PictureError(f"Unsupported channel layout {data.shape}")
    return data


def _effective_levels(planes: np.ndarray, levels: int | None) -> int | None:
    """A 16-bit file holding only 256 distinct steps behaves like an 8-bit one."""
    if levels is None or levels <= 256:
        return levels
    sample = planes[0].ravel()[:: max(1, planes[0].size // 200_000)]
    steps = np.unique(np.round(sample * (levels - 1)).astype(np.int64))
    if steps.size > 1:
        gcd = int(np.gcd.reduce(np.diff(steps)))
        if gcd >= 200:  # e.g. 257 = 65535 / 255: 8-bit data padded to 16 bits
            return (levels - 1) // gcd + 1
    return levels


def _jpeg_quality(img) -> int | None:
    """Estimate libjpeg quality from the luminance quantization table."""
    tables = getattr(img, "quantization", None)
    if not tables or 0 not in tables:
        return None
    std = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40,
           57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35,
           55, 64, 81, 104, 113, 92, 49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112,
           100, 103, 99]
    q = list(tables[0])
    pairs = zip(sorted(q), sorted(std), strict=False)
    scale = float(np.mean([qi * 100.0 / si for qi, si in pairs]))
    quality = (200 - scale) / 2 if scale <= 100 else 5000 / scale
    return int(round(min(100, max(1, quality))))


def _load_raster(path: Path) -> Picture:
    from PIL import Image, ImageCms

    with Image.open(path) as img:
        fmt = (img.format or path.suffix.lstrip(".")).lower()
        quality = _jpeg_quality(img) if fmt in ("jpeg", "mpo") else None
        software = None
        try:
            exif = img.getexif()
            software = exif.get(0x0131) or None
        except Exception:
            pass
        icc = None
        if img.info.get("icc_profile"):
            try:
                import io

                prof = ImageCms.ImageCmsProfile(io.BytesIO(img.info["icc_profile"]))
                icc = ImageCms.getProfileDescription(prof).strip() or None
            except Exception:
                icc = "embedded profile"
        mode = img.mode
        if mode in ("P", "PA", "CMYK", "YCbCr", "LAB", "HSV"):
            img = img.convert("RGB")
        elif mode == "LA":
            img = img.convert("L")
        elif mode == "I;16" or mode.startswith("I;16"):
            data = np.asarray(img, dtype=np.uint16)
            img = None
        if img is not None:
            if img.mode == "I":
                data = np.asarray(img, dtype=np.int32).clip(0, 65535).astype(np.uint16)
            elif img.mode == "F":
                data = np.asarray(img, dtype=np.float32)
            else:
                data = np.asarray(img)
    unit, depth, levels = _to_unit(data)
    planes = _planes(unit, channels_last=True)
    return _finish(path, planes, fmt, depth, levels, software=software, quality=quality, icc=icc)


def _load_tiff(path: Path) -> Picture:
    import tifffile

    try:
        with tifffile.TiffFile(path) as tif:
            page = tif.pages[0]
            data = page.asarray()
            software = page.software or None
            photometric = getattr(page.photometric, "name", "")
            planar = page.planarconfig == tifffile.PLANARCONFIG.SEPARATE \
                if hasattr(tifffile, "PLANARCONFIG") else False
            icc = "embedded profile" if 34675 in page.tags else None
    except Exception:
        return _load_raster(path)  # Pillow handles a few odd variants tifffile does not
    if photometric == "MINISWHITE":
        data = data.max() - data
    unit, depth, levels = _to_unit(data)
    planes = _planes(unit, channels_last=not planar and unit.ndim == 3 and unit.shape[-1] <= 4)
    return _finish(path, planes, "tiff", depth, levels, software=software, icc=icc)


def _load_astro(path: Path) -> Picture:
    from advastro.readers import read_frame

    frame = read_frame(path)
    header = dict(frame.meta.raw_header)
    data = frame.data
    depth, levels = "32-bit float", None
    bitpix = header.get("BITPIX")
    if path.suffix.lower() == ".xisf":
        from advastro.readers.xisf import _tag, read_header

        root, _ = read_header(path)
        el = next((e for e in root.iter() if _tag(e) == "Image"), None)
        fmt = el.get("sampleFormat", "Float32") if el is not None else "Float32"
        depth = {"UInt8": "8-bit", "UInt16": "16-bit", "UInt32": "32-bit",
                 "Float32": "32-bit float", "Float64": "64-bit float"}.get(fmt, fmt)
        levels = {"UInt8": 256, "UInt16": 65536}.get(fmt)
    elif bitpix in (8, 16, 32):
        depth, levels = f"{bitpix}-bit", (2 ** bitpix if bitpix < 32 else None)
    elif bitpix in (-32, -64):
        depth = f"{abs(bitpix)}-bit float"
    if data.ndim == 2 and frame.meta.bayer_pattern:
        raise PictureError("This file is undebayered camera data, not a finished picture. "
                           "Use the main window to analyze subs.")
    if levels:
        unit = np.clip(data / float(levels - 1), 0, 1).astype(np.float32)
    else:
        unit, _, _ = _to_unit(data)
    planes = _planes(unit, channels_last=False)
    fmt = "xisf" if path.suffix.lower() == ".xisf" else "fits"
    pic = _finish(path, planes, fmt, depth, levels,
                  software=str(header.get("SWCREATE") or header.get("PROGRAM") or "") or None)
    pic.header = header
    pic.object_name = frame.meta.object_name
    return pic


def _finish(path: Path, planes: np.ndarray, fmt: str, depth: str, levels: int | None,
            software=None, quality=None, icc=None) -> Picture:
    mono = planes.shape[0] == 1
    if not mono and np.allclose(planes[0], planes[1], atol=1e-4) and \
            np.allclose(planes[1], planes[2], atol=1e-4):
        mono = True
    rgb = np.repeat(planes[:1], 3, axis=0) if planes.shape[0] == 1 else planes
    rgb = np.ascontiguousarray(rgb, dtype=np.float32)
    if min(rgb.shape[1:]) < 64:
        raise PictureError("The picture is too small to analyze (under 64 pixels).")
    eff = _effective_levels(rgb, levels)
    if eff and levels and eff < levels:
        depth = f"{depth} (holding 8-bit data)" if eff <= 256 else depth
    return Picture(path=Path(path), rgb=rgb, mono=mono, format=fmt, bit_depth=depth,
                   levels=eff, software=str(software) if software else None,
                   jpeg_quality=quality, icc=icc)


def load_picture(path: str | Path) -> Picture:
    path = Path(path)
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        raise PictureError(f"Unsupported picture type: {ext or path.name}")
    if ext in ASTRO:
        return _load_astro(path)
    if ext in TIFF:
        return _load_tiff(path)
    return _load_raster(path)
