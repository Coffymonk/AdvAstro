"""Display stretch for previews. Never used for measurements.

Implements the PixInsight ScreenTransferFunction auto-stretch: per channel,
clip shadows a fixed number of MADs below the median, then apply a midtones
transfer function that brings the median to a target background level.
Colour (CFA) frames are previewed as 2x2 superpixel RGB, which needs no
interpolation and halves the size.
"""

from __future__ import annotations

import numpy as np

from advastro.frame import Frame

MAD_TO_SIGMA = 1.4826
_CFA_OFFSETS = {  # (row, col) of R, G1, G2, B in each 2x2 cell
    "RGGB": ((0, 0), (0, 1), (1, 0), (1, 1)),
    "BGGR": ((1, 1), (0, 1), (1, 0), (0, 0)),
    "GRBG": ((0, 1), (0, 0), (1, 1), (1, 0)),
    "GBRG": ((1, 0), (0, 0), (1, 1), (0, 1)),
}


def mtf(m: float, x: np.ndarray) -> np.ndarray:
    """Midtones transfer function: maps m to 0.5, keeps 0 and 1 fixed."""
    return ((m - 1.0) * x) / ((2.0 * m - 1.0) * x - m)


def _stf_params(ch: np.ndarray, shadows_mad: float, target_bkg: float) -> tuple[float, float]:
    sample = ch[:: max(1, ch.size // 500_000 + 1)] if ch.ndim == 1 else ch
    med = float(np.median(sample))
    mad = MAD_TO_SIGMA * float(np.median(np.abs(sample - med)))
    c0 = min(max(med + shadows_mad * mad, 0.0), 1.0) if mad > 0 else 0.0
    x = (med - c0) / (1.0 - c0) if c0 < 1 else 0.5
    m = float(mtf(target_bkg, np.float64(x))) if 0 < x < 1 else 0.5
    return c0, m


def auto_stretch(channels: np.ndarray, shadows_mad: float = -2.8,
                 target_bkg: float = 0.25, linked: bool = False) -> np.ndarray:
    """Stretch float data in [0, 1] of shape (c, h, w). Returns float32 in [0, 1]."""
    out = np.empty_like(channels, dtype=np.float32)
    if linked:
        c0, m = _stf_params(channels.ravel(), shadows_mad, target_bkg)
        params = [(c0, m)] * channels.shape[0]
    else:
        params = [_stf_params(ch.ravel(), shadows_mad, target_bkg) for ch in channels]
    for i, (c0, m) in enumerate(params):
        x = np.clip((channels[i] - c0) / max(1e-9, 1.0 - c0), 0.0, 1.0)
        out[i] = mtf(m, x)
    return out


def _bin_to(data: np.ndarray, max_side: int) -> np.ndarray:
    """Integer block-average downsampling so the longest side is <= max_side."""
    factor = max(1, int(np.ceil(max(data.shape[-2:]) / max_side)))
    if factor == 1:
        return data
    h = (data.shape[-2] // factor) * factor
    w = (data.shape[-1] // factor) * factor
    d = data[..., :h, :w]
    shape = d.shape[:-2] + (h // factor, factor, w // factor, factor)
    return d.reshape(shape).mean(axis=(-3, -1))


def preview_rgb(frame: Frame, max_side: int = 2048) -> np.ndarray:
    """Auto-stretched 8-bit preview, shape (h, w, 3), C-contiguous."""
    data = frame.data.astype(np.float32, copy=False)
    scale = frame.meta.saturation_adu or float(np.max(data)) or 1.0

    if data.ndim == 3:  # already RGB (c, h, w)
        rgb = data[:3] if data.shape[0] >= 3 else np.repeat(data[:1], 3, axis=0)
    elif frame.meta.bayer_pattern in _CFA_OFFSETS:
        h, w = (data.shape[0] // 2) * 2, (data.shape[1] // 2) * 2
        (rr, rc), (g1r, g1c), (g2r, g2c), (br, bc) = _CFA_OFFSETS[frame.meta.bayer_pattern]
        d = data[:h, :w]
        rgb = np.stack([
            d[rr::2, rc::2],
            0.5 * (d[g1r::2, g1c::2] + d[g2r::2, g2c::2]),
            d[br::2, bc::2],
        ])
    else:
        rgb = np.repeat(data[None], 3, axis=0)

    rgb = _bin_to(rgb, max_side) / scale
    stretched = auto_stretch(np.clip(rgb, 0, 1), linked=frame.meta.bayer_pattern is None
                             and data.ndim == 2)
    img = (np.moveaxis(stretched, 0, -1) * 255.0 + 0.5).astype(np.uint8)
    return np.ascontiguousarray(img)
