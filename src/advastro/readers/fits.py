"""FITS reader based on astropy.

Reads common keywords written by NINA, ASIAIR, SharpCap, KStars/Ekos,
Sequence Generator Pro and APT, and normalizes them into FrameMeta.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
from astropy.io import fits as afits

from advastro.frame import Frame, FrameMeta

# Keyword aliases in priority order. Different capture programs use different names.
_KEYS = {
    "image_type": ("IMAGETYP", "FRAME", "FRAMETYP"),
    "object_name": ("OBJECT", "OBJNAME"),
    "filter_name": ("FILTER", "FILTNAME"),
    "exposure_s": ("EXPTIME", "EXPOSURE"),
    "gain": ("GAIN", "EGAIN_SET"),
    "offset": ("OFFSET", "BLKLEVEL"),
    "temperature_c": ("CCD-TEMP", "CCD_TEMP", "SET-TEMP", "SENSORTEMP"),
    "binning": ("XBINNING", "BINNING"),
    "pixel_size_um": ("XPIXSZ", "PIXSIZE1", "PIXSIZE"),
    "focal_length_mm": ("FOCALLEN", "FOCAL", "FOCLEN"),
    "bayer_pattern": ("BAYERPAT", "COLORTYP", "CFA-PAT"),
    "date_obs": ("DATE-OBS", "DATE-LOC"),
    "ra_deg": ("RA", "OBJCTRA"),
    "dec_deg": ("DEC", "OBJCTDEC"),
    "camera": ("INSTRUME", "CAMERA"),
    "telescope": ("TELESCOP",),
    "saturation_adu": ("DATAMAX", "SATURATE"),
}

_IMAGE_TYPES = {
    "light": "light", "light frame": "light", "lights": "light",
    "flat": "flat", "flat field": "flat", "flat frame": "flat", "flats": "flat",
    "dark": "dark", "dark frame": "dark", "darks": "dark",
    "bias": "bias", "bias frame": "bias", "offset": "bias",
    "darkflat": "darkflat", "dark flat": "darkflat", "flatdark": "darkflat",
    "master light": "light", "master flat": "flat", "master dark": "dark",
    "master bias": "bias", "master darkflat": "darkflat",
}


def _first(header: afits.Header, names: tuple[str, ...]):
    for name in names:
        if name in header and header[name] not in (None, ""):
            return header[name]
    return None


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sexagesimal_to_deg(value, hours: bool) -> float | None:
    """Accept numbers in degrees or strings like '20 58 47' / '+44:19:48'."""
    number = _to_float(value)
    if number is not None:
        return number
    if not isinstance(value, str):
        return None
    parts = value.replace(":", " ").split()
    try:
        sign = -1.0 if parts[0].strip().startswith("-") else 1.0
        d, m, s = (abs(float(parts[0])), float(parts[1]), float(parts[2]))
    except (IndexError, ValueError):
        return None
    deg = sign * (d + m / 60 + s / 3600)
    return deg * 15 if hours else deg


def _parse_date(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip().rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_header(header: afits.Header) -> FrameMeta:
    g = {key: _first(header, names) for key, names in _KEYS.items()}

    image_type = None
    if isinstance(g["image_type"], str):
        image_type = _IMAGE_TYPES.get(g["image_type"].strip().lower(), g["image_type"].lower())

    bayer = g["bayer_pattern"]
    bayer = bayer.strip().upper() if isinstance(bayer, str) and bayer.strip() else None
    if bayer and bayer not in {"RGGB", "BGGR", "GRBG", "GBRG"}:
        bayer = None

    binning = _to_float(g["binning"])
    saturation = _to_float(g["saturation_adu"])
    if saturation is None:
        bitpix = header.get("BITPIX")
        if bitpix == 16:
            saturation = 65535.0
        elif bitpix == 8:
            saturation = 255.0

    return FrameMeta(
        image_type=image_type,
        object_name=str(g["object_name"]).strip() if g["object_name"] else None,
        filter_name=str(g["filter_name"]).strip() if g["filter_name"] else None,
        exposure_s=_to_float(g["exposure_s"]),
        gain=_to_float(g["gain"]),
        offset=_to_float(g["offset"]),
        temperature_c=_to_float(g["temperature_c"]),
        binning=int(binning) if binning else None,
        pixel_size_um=_to_float(g["pixel_size_um"]),
        focal_length_mm=_to_float(g["focal_length_mm"]),
        bayer_pattern=bayer,
        date_obs=_parse_date(g["date_obs"]),
        ra_deg=_sexagesimal_to_deg(g["ra_deg"], hours=isinstance(g["ra_deg"], str)),
        dec_deg=_sexagesimal_to_deg(g["dec_deg"], hours=False),
        camera=str(g["camera"]).strip() if g["camera"] else None,
        telescope=str(g["telescope"]).strip() if g["telescope"] else None,
        saturation_adu=saturation,
        raw_header={k: header[k] for k in header if k and k not in ("COMMENT", "HISTORY")},
    )


def read(path: Path) -> Frame:
    """Read the first image HDU of a FITS file as float32 linear data."""
    # memmap is off: camera files are almost always 16-bit with BZERO=32768,
    # which astropy cannot memory-map, and the data is converted to float32 anyway.
    with afits.open(path, memmap=False) as hdul:
        hdu = next((h for h in hdul if h.data is not None and h.data.ndim >= 2), None)
        if hdu is None:
            raise ValueError(f"No image data in {path.name}")
        meta = parse_header(hdu.header)
        data = np.asarray(hdu.data, dtype=np.float32)
    if data.ndim == 3 and data.shape[0] == 1:
        data = data[0]
    return Frame(path=Path(path), data=data, meta=meta, format="fits")
