"""The common data structure every reader produces.

Readers hide file-format differences: FITS, XISF and camera raw files all
become a Frame, so the analysis engine never needs to know the format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

ARCSEC_PER_RADIAN = 206_264.806


@dataclass
class FrameMeta:
    """Normalized metadata. None means 'not known from the file'."""

    image_type: str | None = None  # light, flat, dark, bias, darkflat
    object_name: str | None = None
    filter_name: str | None = None
    exposure_s: float | None = None
    gain: float | None = None
    offset: float | None = None
    temperature_c: float | None = None
    binning: int | None = None
    pixel_size_um: float | None = None  # physical pixel size incl. binning
    focal_length_mm: float | None = None
    bayer_pattern: str | None = None  # RGGB, GRBG, ... or None for mono
    date_obs: datetime | None = None
    ra_deg: float | None = None
    dec_deg: float | None = None
    camera: str | None = None
    telescope: str | None = None
    saturation_adu: float | None = None
    raw_header: dict = field(default_factory=dict)

    @property
    def pixel_scale_arcsec(self) -> float | None:
        """Image scale in arcsec per pixel, if pixel size and focal length are known."""
        if not self.pixel_size_um or not self.focal_length_mm:
            return None
        return ARCSEC_PER_RADIAN * self.pixel_size_um * 1e-3 / self.focal_length_mm

    @property
    def is_colour(self) -> bool:
        return self.bayer_pattern is not None


@dataclass
class Frame:
    """Linear image data plus metadata. Data is float32, never stretched."""

    path: Path
    data: np.ndarray  # 2-D (mono or undebayered CFA) or 3-D (channels, y, x)
    meta: FrameMeta
    format: str  # "fits", "xisf", "raw"
