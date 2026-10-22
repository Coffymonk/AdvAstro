"""XISF reader (PixInsight's native format), written from the XISF 1.0 specification.

Supports monolithic files with attached or inline image data, all common sample
formats, planar and normal pixel storage, and zlib / LZ4 / LZ4HC / Zstandard
compression with optional byte shuffling. Metadata comes from embedded FITS
keywords (normalized by the FITS reader's rules) and XISF properties.
"""

from __future__ import annotations

import base64
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import numpy as np
from astropy.io import fits as afits

from advastro.frame import Frame, FrameMeta
from advastro.i18n import tr
from advastro.readers.fits import parse_header

SIGNATURE = b"XISF0100"
_NS = "{http://www.pixinsight.com/xisf}"
_DTYPES = {
    "UInt8": np.uint8, "UInt16": np.uint16, "UInt32": np.uint32, "UInt64": np.uint64,
    "Float32": np.float32, "Float64": np.float64,
}
_SATURATION = {"UInt8": 255.0, "UInt16": 65535.0, "UInt32": 4294967295.0}


class XISFError(ValueError):
    pass


def _tag(el: ET.Element) -> str:
    return el.tag.replace(_NS, "")


def _unshuffle(data: bytes, item_size: int) -> bytes:
    if item_size <= 1:
        return data
    arr = np.frombuffer(data, dtype=np.uint8)
    n = len(arr) // item_size
    body = arr[: n * item_size].reshape(item_size, n).T.ravel()
    return body.tobytes() + arr[n * item_size:].tobytes()


def _decompress(raw: bytes, spec: str | None) -> bytes:
    if not spec:
        return raw
    parts = spec.split(":")
    codec, size = parts[0], int(parts[1])
    shuffled = codec.endswith("+sh")
    codec = codec.removesuffix("+sh")
    if codec == "zlib":
        out = zlib.decompress(raw)
    elif codec in ("lz4", "lz4hc"):
        try:
            import lz4.block
        except ImportError as exc:
            raise XISFError(tr("read.err.package", codec="LZ4", package="lz4")) from exc
        out = lz4.block.decompress(raw, uncompressed_size=size)
    elif codec == "zstd":
        try:
            import zstandard
        except ImportError as exc:
            raise XISFError(tr("read.err.package", codec="Zstandard", package="zstandard")) from exc
        out = zstandard.ZstdDecompressor().decompress(raw, max_output_size=size)
    else:
        raise XISFError(tr("read.err.compression", codec=codec))
    if shuffled:
        out = _unshuffle(out, int(parts[2]) if len(parts) > 2 else 1)
    return out


def _block(fh, location: str, image_el: ET.Element) -> bytes:
    kind, *rest = location.split(":")
    if kind == "attachment":
        pos, size = int(rest[0]), int(rest[1])
        fh.seek(pos)
        data = fh.read(size)
        if len(data) != size:
            raise XISFError(tr("read.err.truncated"))
        return data
    if kind == "inline":
        encoding = rest[0] if rest else "base64"
        text = (image_el.text or "").strip()
        return base64.b64decode(text) if encoding == "base64" else bytes.fromhex(text)
    if kind == "embedded":
        data_el = next((c for c in image_el if _tag(c) == "Data"), None)
        if data_el is None:
            raise XISFError(tr("read.err.block"))
        return base64.b64decode((data_el.text or "").strip())
    raise XISFError(tr("read.err.location", kind=kind))


def _keyword_value(text: str):
    text = text.strip()
    if text.startswith("'") and text.endswith("'"):
        return text[1:-1].strip()
    if text in ("T", "F"):
        return text == "T"
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def _properties(image_el: ET.Element) -> dict[str, str]:
    props = {}
    for child in image_el:
        if _tag(child) == "Property" and child.get("id"):
            props[child.get("id")] = child.get("value", (child.text or "").strip())
    return props


def read_header(path: Path) -> tuple[ET.Element, int]:
    with open(path, "rb") as fh:
        if fh.read(8) != SIGNATURE:
            raise XISFError(tr("read.err.not_xisf", name=path.name))
        (length,) = struct.unpack("<I", fh.read(4))
        fh.read(4)  # reserved
        xml = fh.read(length)
    root = ET.fromstring(xml.split(b"\x00", 1)[0])
    return root, 16 + length


def read(path: Path) -> Frame:
    path = Path(path)
    root, _ = read_header(path)
    image_el = next((el for el in root.iter() if _tag(el) == "Image"), None)
    if image_el is None:
        raise XISFError(tr("read.err.no_image", name=path.name))

    geometry = [int(x) for x in image_el.get("geometry", "").split(":")]
    if len(geometry) < 3:
        geometry += [1] * (3 - len(geometry))
    width, height, channels = geometry[0], geometry[1], geometry[2]
    fmt = image_el.get("sampleFormat", "UInt16")
    if fmt not in _DTYPES:
        raise XISFError(tr("read.err.sample", fmt=fmt))
    dtype = np.dtype(_DTYPES[fmt]).newbyteorder("<")

    with open(path, "rb") as fh:
        raw = _block(fh, image_el.get("location", ""), image_el)
    data = np.frombuffer(_decompress(raw, image_el.get("compression")), dtype=dtype)
    expected = width * height * channels
    if data.size != expected:
        raise XISFError(tr("read.err.samples", name=path.name, expected=expected, found=data.size))
    if image_el.get("pixelStorage", "Planar") == "Normal":
        data = data.reshape(height, width, channels).transpose(2, 0, 1)
    else:
        data = data.reshape(channels, height, width)
    data = data.astype(np.float32)
    if channels == 1:
        data = data[0]

    header = afits.Header()
    for child in image_el:
        if _tag(child) == "FITSKeyword" and child.get("name"):
            name = child.get("name").upper()
            if name in ("COMMENT", "HISTORY", "") or len(name) > 8:
                continue
            try:
                header[name] = _keyword_value(child.get("value", ""))
            except (ValueError, KeyError):
                continue
    meta = parse_header(header)
    _apply_properties(meta, _properties(image_el))

    cfa = next((c for c in image_el if _tag(c) == "ColorFilterArray"), None)
    if cfa is not None and channels == 1 and cfa.get("pattern", "").upper() in {
            "RGGB", "BGGR", "GRBG", "GBRG"}:
        meta.bayer_pattern = cfa.get("pattern").upper()
    if fmt.startswith("Float"):
        meta.saturation_adu = 1.0  # PixInsight floating-point images are normalized to [0, 1]
    else:
        meta.saturation_adu = meta.saturation_adu or _SATURATION.get(fmt)
    return Frame(path=path, data=data, meta=meta, format="xisf")


def _apply_properties(meta: FrameMeta, props: dict[str, str]) -> None:
    """Fill gaps left by FITS keywords from standard XISF properties."""

    def num(key: str) -> float | None:
        try:
            return float(props[key])
        except (KeyError, ValueError):
            return None

    if meta.exposure_s is None:
        meta.exposure_s = num("Instrument:ExposureTime")
    if meta.focal_length_mm is None and (fl := num("Instrument:Telescope:FocalLength")):
        meta.focal_length_mm = fl * 1000.0 if fl < 20 else fl  # the spec uses metres
    if meta.pixel_size_um is None:
        meta.pixel_size_um = num("Instrument:Sensor:XPixelSize")
    if meta.temperature_c is None:
        meta.temperature_c = num("Instrument:Sensor:Temperature")
    if meta.filter_name is None and props.get("Instrument:Filter:Name"):
        meta.filter_name = props["Instrument:Filter:Name"]
    if meta.object_name is None and props.get("Observation:Object:Name"):
        meta.object_name = props["Observation:Object:Name"]
    if meta.camera is None and props.get("Instrument:Camera:Name"):
        meta.camera = props["Instrument:Camera:Name"]
    if meta.ra_deg is None:
        meta.ra_deg = num("Observation:Center:RA")
    if meta.dec_deg is None:
        meta.dec_deg = num("Observation:Center:Dec")
