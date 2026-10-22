"""One calibration frame in detail: opened by double-clicking it in the Calibration table.

Shows the frame, a hot-pixel map, every measurement next to the set's median with a
plain explanation, and why the frame was flagged. For darks, bias and flat darks there is
a section that explains hot pixels: how many, how strong, where on the sensor, and what
that means for your pictures.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QObject, QPointF, Qt, QThread, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from advastro.gui.advice_panels import _label, _scroll
from advastro.gui.help_window import show_help
from advastro.gui.theme import Theme
from advastro.gui.widgets import PreviewView
from advastro.i18n import tr

DARK_KINDS = ("bias", "darks", "darkflats")
GLOW_REGION = {"top left": "upper_left", "top right": "upper_right", "bottom left": "lower_left",
               "bottom right": "lower_right", "left edge": "left", "right edge": "right",
               "top edge": "top", "bottom edge": "bottom"}


class _Loader(QObject):
    done = Signal(object, object)      # preview QImage, HotPixelDetails | None
    failed = Signal(str)

    def __init__(self, path: str, kind: str) -> None:
        super().__init__()
        self.path, self.kind = path, kind

    def run(self) -> None:
        from advastro.display import preview_rgb
        from advastro.engine.calibration import hot_pixel_details
        from advastro.readers import read_frame

        try:
            frame = read_frame(self.path)
            rgb = preview_rgb(frame)
            h, w, _ = rgb.shape
            img = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
            details = hot_pixel_details(frame.data) if self.kind in DARK_KINDS else None
            self.done.emit(img, details)
        except Exception as exc:
            self.failed.emit(str(exc))


def hot_map(details, w: int, h: int, theme: Theme) -> QImage:
    """Hot pixels drawn as dots on a dark sensor outline; brighter and larger = stronger."""
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(theme.bg))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    k = w / max(details.width, 1)
    p.setPen(QPen(QColor(theme.border), 1, Qt.PenStyle.DashLine))
    for i in (1, 2):
        p.drawLine(QPointF(i * w / 3, 0), QPointF(i * w / 3, h))
        p.drawLine(QPointF(0, i * h / 3), QPointF(w, i * h / 3))
    p.setPen(Qt.PenStyle.NoPen)
    for x, y, s in zip(details.xs[:6000], details.ys[:6000], details.strength[:6000],
                       strict=False):
        t = min(1.0, math.log10(max(s, 10)) - 1.0)          # 10σ -> 0, 100σ+ -> 1
        col = QColor.fromHsvF(0.16 * (1 - t), 0.9, 1.0, 0.6 + 0.4 * t)
        p.setBrush(col)
        r = 1.6 + 2.4 * t
        p.drawEllipse(QPointF(x * k, y * k), r, r)
    f = p.font()
    f.setPointSizeF(max(9.0, w / 70))
    f.setBold(True)
    p.setFont(f)
    for j in range(3):
        for i in range(3):
            p.setPen(QColor(255, 255, 255, 200))
            p.drawText(int(i * w / 3 + 8), int(j * h / 3 + f.pointSizeF() * 1.8),
                       f"{details.grid[j, i]:,}")
    p.end()
    return img


class CalibrationFrameDialog(QDialog):
    def __init__(self, metrics, group, theme: Theme, parent=None) -> None:
        super().__init__(parent)
        self.m, self.group, self.theme = metrics, group, theme
        self.details = None
        self.frame_image: QImage | None = None
        self.setWindowTitle(f"{metrics.file} — {tr(f'gui.frames.{metrics.kind}')}")
        self.resize(1180, 760)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(1)
        lay.addWidget(split, 1)

        left = QFrame()
        left.setObjectName("panel")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        chips = QHBoxLayout()
        chips.setContentsMargins(14, 10, 12, 8)
        self.view_group = QButtonGroup(self)
        self.view_buttons = {}
        views = ("frame", "hot") if metrics.kind in DARK_KINDS else ("frame",)
        for key in views:
            b = QPushButton(tr(f"gui.calinfo.view.{key}"))
            b.setObjectName("chip")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key: self._show_view(k))
            self.view_group.addButton(b)
            self.view_buttons[key] = b
            chips.addWidget(b)
        chips.addStretch(1)
        lv.addLayout(chips)
        self.view = PreviewView()
        self.view.theme = theme
        self.view.set_placeholder(tr("gui.preview.loading"))
        lv.addWidget(self.view, 1)
        self.legend = QLabel("")
        self.legend.setObjectName("statLabel")
        self.legend.setWordWrap(True)
        self.legend.setContentsMargins(14, 6, 14, 10)
        lv.addWidget(self.legend)
        split.addWidget(left)

        inner = QWidget()
        self.info = QVBoxLayout(inner)
        self.info.setContentsMargins(20, 16, 20, 16)
        self.info.setSpacing(10)
        split.addWidget(_scroll(inner))
        split.setSizes([640, 540])

        bar = QHBoxLayout()
        bar.setContentsMargins(16, 8, 16, 12)
        helpb = QPushButton(tr("gui.calinfo.manual"))
        helpb.setObjectName("link")
        helpb.clicked.connect(lambda: show_help(
            "calibration.check.hot" if metrics.kind in DARK_KINDS else
            "calibration.check.flatlevel", self))
        bar.addWidget(helpb)
        bar.addStretch(1)
        close = QPushButton(tr("gui.calinfo.close"))
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        bar.addWidget(close)
        lay.addLayout(bar)

        self._fill()
        self.view_buttons["frame"].setChecked(True)
        self._thread = QThread(self)
        self._loader = _Loader(metrics.path, metrics.kind)
        self._loader.moveToThread(self._thread)
        self._thread.started.connect(self._loader.run)
        self._loader.done.connect(self._loaded)
        self._loader.failed.connect(lambda msg: self.view.set_placeholder(msg))
        self._loader.done.connect(self._thread.quit)
        self._loader.failed.connect(self._thread.quit)
        self._thread.start()

    # ---- picture -------------------------------------------------------------------
    def _loaded(self, image: QImage, details) -> None:
        self.frame_image, self.details = image, details
        self._show_view("frame")
        if details is not None:
            self._fill()               # now with the hot-pixel numbers

    def _show_view(self, key: str) -> None:
        self.view_buttons[key].setChecked(True)
        if self.frame_image is None:
            return
        if key == "hot" and self.details is not None:
            w = self.frame_image.width()
            h = self.frame_image.height()
            self.view.set_image(hot_map(self.details, w, h, self.theme))
            self.legend.setText(tr("gui.calinfo.hot_legend"))
        else:
            self.view.set_image(self.frame_image)
            self.legend.setText(tr("gui.calinfo.frame_legend"))

    # ---- text ----------------------------------------------------------------------
    def _section(self, text: str) -> None:
        self.info.addWidget(_label(text.upper(), "section"))

    def _fill(self) -> None:
        lay = self.info
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        m, g, t = self.m, self.group, self.theme
        title = _label(m.file, "title")
        lay.addWidget(title)
        sub = [tr(f"gui.frames.{m.kind}")]
        if m.is_master:
            sub.append(tr("gui.calinfo.master"))
        if m.time:
            sub.append(m.time.replace("T", " ")[:19])
        lay.addWidget(_label(" · ".join(sub), "statLabel"))

        flags = [f for f in (g.flags if g else []) if f.file == m.file]
        if flags:
            lay.addWidget(_label(
                "".join(f"<p style='margin:2px 0'><span style='color:{t.warn}'>⚑</span>&nbsp; "
                        f"{f.reason}</p>" for f in flags)))
        else:
            lay.addWidget(_label(f"<span style='color:{t.good}'>✓</span>&nbsp; "
                                 + tr("gui.calinfo.not_flagged")))

        self._section(tr("gui.calinfo.settings"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        settings = [
            (tr("gui.cal.exposure"), f"{m.exposure_s:g} s" if m.exposure_s is not None else "–"),
            (tr("gui.calinfo.gain"), f"{m.gain:g}" if m.gain is not None else "–"),
            (tr("gui.calinfo.offset"), f"{m.offset:g}" if m.offset is not None else "–"),
            (tr("gui.calinfo.temp"), f"{m.temperature_c:.1f} °C"
             if m.temperature_c is not None else "–"),
            (tr("gui.calinfo.binning"), f"{m.binning}×{m.binning}" if m.binning else "–"),
            (tr("gui.calinfo.size"), f"{m.width} × {m.height}"),
        ]
        for i, (a, b) in enumerate(settings):
            grid.addWidget(_label(a, "statLabel"), i // 2, (i % 2) * 2)
            grid.addWidget(_label(b), i // 2, (i % 2) * 2 + 1)
        lay.addLayout(grid)

        self._section(tr("gui.calinfo.measured"))
        med = g.medians if g else {}

        def row(label, value, ref, spec, unit, why):
            v = "–" if value is None else format(value, spec) + unit
            r = "–" if ref is None else format(ref, spec) + unit
            return (label, v, r, why)

        if m.kind == "flats":
            rows = [
                row(tr("gui.cal.level_pct"), m.level_pct, med.get("level_pct"), ".0f", " %",
                    tr("gui.calinfo.why.level_pct")),
                row(tr("gui.cal.clipped"), m.clipped_pct, med.get("clipped_pct"), ".3f", " %",
                    tr("gui.calinfo.why.clipped")),
                row(tr("gui.cal.vignetting"), m.vignetting_pct, med.get("vignetting_pct"), ".0f",
                    " %", tr("gui.calinfo.why.vignetting")),
                row(tr("gui.cal.dust"), m.dust_spots, med.get("dust_spots"), ".0f", "",
                    tr("gui.calinfo.why.dust")),
            ]
            if m.channel_levels and len(m.channel_levels) == 3 and m.saturation_adu:
                ch = " / ".join(f"{c / m.saturation_adu * 100:.0f} %" for c in m.channel_levels)
                rows.append((tr("gui.calinfo.channels"), ch, "", tr("gui.calinfo.why.channels")))
        else:
            rows = [
                row(tr("gui.cal.level"), m.median_adu, med.get("median_adu"), ",.0f", " ADU",
                    tr("gui.calinfo.why.level")),
                row(tr("gui.cal.noise"), m.noise_adu, med.get("noise_adu"), ".1f", " ADU",
                    tr("gui.calinfo.why.noise")),
                row(tr("gui.cal.hot"), m.hot_pixels, med.get("hot_pixels"), ",.0f", "",
                    tr("gui.calinfo.why.hot")),
                row(tr("gui.cal.glow"), m.glow_adu, med.get("glow_adu"), ".0f", " ADU",
                    tr("gui.calinfo.why.glow_where", where=tr(
                        f"gui.calinfo.region.{GLOW_REGION.get(m.glow_where, 'centre')}"))
                    if m.glow_where
                    else tr("gui.calinfo.why.glow")),
                row(tr("gui.calinfo.banding"), m.banding_adu, med.get("banding_adu"), ".2f",
                    " ADU", tr("gui.calinfo.why.banding")),
            ]
        table = QGridLayout()
        table.setHorizontalSpacing(14)
        table.setVerticalSpacing(8)
        for c, head in enumerate((tr("gui.calinfo.col.what"), tr("gui.calinfo.col.this"),
                                  tr("gui.calinfo.col.set"))):
            table.addWidget(_label(f"<b>{head}</b>", "statLabel"), 0, c)
        for i, (a, v, r, why) in enumerate(rows, 1):
            cell = QVBoxLayout()
            cell.setSpacing(1)
            cell.addWidget(_label(f"<b>{a}</b>"))
            cell.addWidget(_label(why, "statLabel"))
            table.addLayout(cell, i, 0)
            table.addWidget(_label(v), i, 1, Qt.AlignmentFlag.AlignTop)
            table.addWidget(_label(r, "statLabel"), i, 2, Qt.AlignmentFlag.AlignTop)
        table.setColumnStretch(0, 1)
        lay.addLayout(table)

        if m.kind in DARK_KINDS:
            self._hot_section()
        lay.addStretch(1)

    def _hot_section(self) -> None:
        m, d, lay = self.m, self.details, self.info
        self._section(tr("gui.calinfo.hot_title"))
        if d is None:
            lay.addWidget(_label(tr("gui.calinfo.hot_loading"), "muted"))
            lay.addWidget(_label(tr("gui.calinfo.hot_what"), "statLabel"))
            return
        strong = int((d.strength >= 50).sum())
        lay.addWidget(_label(tr("gui.calinfo.hot_numbers", count=f"{d.count:,}",
                                share=f"{d.share_pct:.3f}", warm=f"{d.warm:,}",
                                strong=f"{strong:,}", noise=f"{d.noise:.1f}")))
        lay.addWidget(_label(tr("gui.calinfo.hot_what"), "statLabel"))
        # Where on the sensor: even spread, or clustered (glow, a warm edge)?
        grid = d.grid.astype(float)
        mean = grid.mean() if grid.size else 0
        if d.count >= 30 and mean > 0:
            worst = np.unravel_index(np.argmax(grid), grid.shape)
            ratio = grid[worst] / mean
            names = [["upper left", "top", "upper right"], ["left", "centre", "right"],
                     ["lower left", "bottom", "lower right"]]
            where = tr(f"gui.calinfo.region.{names[worst[0]][worst[1]].replace(' ', '_')}")
            key = "gui.calinfo.hot_even" if ratio < 1.6 else "gui.calinfo.hot_cluster"
            lay.addWidget(_label(tr(key, where=where, ratio=f"{ratio:.1f}")))
        # Compared with the rest of the set.
        med = self.group.medians.get("hot_pixels") if self.group else None
        if med:
            ratio = (m.hot_pixels or 0) / med
            key = "gui.calinfo.hot_vs_high" if ratio > 1.3 else \
                "gui.calinfo.hot_vs_low" if ratio < 0.7 else "gui.calinfo.hot_vs_same"
            lay.addWidget(_label(tr(key, ratio=f"{ratio:.1f}", median=f"{med:,.0f}")))
        lay.addWidget(_label(tr("gui.calinfo.hot_temp",
                                temp=f"{m.temperature_c:.0f}" if m.temperature_c is not None
                                else "?")))
        card = QFrame()
        card.setObjectName("card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(12, 10, 12, 10)
        cv.addWidget(_label(f"<b>{tr('gui.calinfo.hot_todo_title')}</b>"))
        cv.addWidget(_label(tr("gui.calinfo.hot_todo"), "statLabel"))
        lay.addWidget(card)
        self._show_view("hot" if self.view_buttons.get("hot") and
                        self.view_buttons["hot"].isChecked() else "frame")

    def done(self, result: int) -> None:
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        super().done(result)


__all__ = ["CalibrationFrameDialog", "hot_map"]
