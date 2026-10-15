"""PDF report for Rate my pic, laid out by Qt's text engine (no extra dependencies)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from advastro import APP_NAME
from advastro.rate.judge import Rating
from advastro.rate.report import to_html


def _qimage(rgb: np.ndarray):
    from PySide6.QtGui import QImage

    a = np.ascontiguousarray((np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8))
    h, w, _ = a.shape
    img = QImage(a.data, w, h, 3 * w, QImage.Format.Format_RGB888)
    return img.copy()


def preview_array(r: Rating, max_side: int = 1400) -> np.ndarray:
    """(h, w, 3) display version of the picture (auto-stretched when still linear)."""
    rgb = r.picture.rgb
    step = max(1, int(np.ceil(max(rgb.shape[1:]) / max_side)))
    small = rgb[:, ::step, ::step]
    if r.measurements.linear:
        from advastro.display import auto_stretch

        small = auto_stretch(small, target_bkg=0.12, linked=True)
    return np.moveaxis(small, 0, -1)


def write_pdf(r: Rating, path: str | Path, picture_image=None, survey_image=None) -> Path:
    from PySide6.QtCore import QMarginsF, QSizeF, QUrl
    from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument

    path = Path(path)
    doc = QTextDocument()
    images = {}
    pic = picture_image if picture_image is not None else _qimage(preview_array(r))
    doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl("advastro://picture"), pic)
    images["picture"] = "advastro://picture"
    if survey_image is None and r.sky is not None and r.sky.survey is not None:
        survey_image = _qimage(r.sky.survey)
    if survey_image is not None:
        doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl("advastro://survey"),
                        survey_image)
        images["survey"] = "advastro://survey"
    doc.setHtml(to_html(r, images))
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Unit.Millimeter)
    writer.setResolution(110)
    writer.setTitle(f"Rate my pic: {r.picture.path.name}")
    writer.setCreator(APP_NAME)
    doc.setPageSize(QSizeF(writer.width(), writer.height()))
    doc.print_(writer)
    return path
