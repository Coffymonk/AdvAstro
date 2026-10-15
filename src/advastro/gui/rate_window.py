"""Rate my pic: a separate window that judges a finished astrophoto.

The main window and its loaded session stay untouched; this window has its own
picture, workers and export. Layout: the picture with switchable overlays on the
left, and Verdict / Findings / Improve / Compare / Details tabs on the right.
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QPointF, QRectF, QSize, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QFont,
    QGuiApplication,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGraphicsPixmapItem,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from advastro import APP_NAME
from advastro.config import Config
from advastro.gui import icons
from advastro.gui.advice_panels import _clear, _label, _scroll
from advastro.gui.help_window import add_help_shortcut, show_help
from advastro.gui.theme import DARK, Theme
from advastro.gui.widgets import ElidedLabel, PreviewView
from advastro.help import finding_topic
from advastro.i18n import tr
from advastro.rate.picture import SUPPORTED
from advastro.rate.sky import GAIA_CREDIT, survey_credit

PREVIEW_MAX = 2400
OVERLAYS = ("none", "stars", "background", "noise", "cast", "clipping", "problems")


# ============================================================================ workers
class RateWorker(QObject):
    progress = Signal(str)
    finished = Signal(object, object, float)     # Rating, preview QImage, seconds
    failed = Signal(str)

    def __init__(self, path: Path, cfg: Config) -> None:
        super().__init__()
        self.path, self.cfg = path, cfg

    def run(self) -> None:
        from advastro.rate.judge import judge
        from advastro.rate.measure import measure
        from advastro.rate.picture import load_picture

        started = time.monotonic()
        try:
            self.progress.emit("load")
            pic = load_picture(self.path)
            m = measure(pic, progress=self.progress.emit)
            rating = judge(pic, m, self.cfg.section("profile"))
            from advastro.rate.pdf import preview_array

            arr = preview_array(rating, PREVIEW_MAX)
            a = np.ascontiguousarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))
            img = QImage(a.data, a.shape[1], a.shape[0], 3 * a.shape[1],
                         QImage.Format.Format_RGB888).copy()
            self.finished.emit(rating, img, time.monotonic() - started)
        except Exception as exc:
            self.failed.emit(str(exc))


class SkyWorker(QObject):
    progress = Signal(str)
    finished = Signal(object)                    # new Rating with sky
    failed = Signal(str)

    def __init__(self, rating, cfg: Config, hint: str | None) -> None:
        super().__init__()
        self.rating, self.cfg, self.hint = rating, cfg, hint

    def run(self) -> None:
        from advastro.rate.judge import judge
        from advastro.rate.sky import sky_checks

        try:
            r = self.rating
            sky = sky_checks(r.picture, r.measurements, self.cfg, self.hint,
                             want_survey=bool(self.cfg.get("compare", "survey", True)),
                             progress=self.progress.emit)
            self.finished.emit(judge(r.picture, r.measurements, self.cfg.section("profile"),
                                     sky))
        except Exception as exc:
            self.failed.emit(str(exc))


class AstroBinWorker(QObject):
    finished = Signal(list)                      # [(OtherImage, bytes | None)]
    failed = Signal(str)

    def __init__(self, name: str, aliases: list[str], key: str, secret: str) -> None:
        super().__init__()
        self.name, self.aliases, self.key, self.secret = name, aliases, key, secret

    def run(self) -> None:
        from advastro.rate.sky import SkyError, astrobin_images, thumbnail

        try:
            found = astrobin_images(self.name, self.key, self.secret, self.aliases)
            out = []
            for img in found:
                try:
                    data = thumbnail(img.thumb) if img.thumb else None
                except SkyError:
                    data = None
                out.append((img, data))
            self.finished.emit(out)
        except Exception as exc:
            self.failed.emit(str(exc))


# ============================================================================ widgets
class ScoreRing(QWidget):
    """The overall score as a ring that fills up, with the number inside."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.score: int | None = None
        self.color = QColor("#6aa8ff")
        self.theme: Theme = DARK
        self.setFixedSize(112, 112)

    def set(self, score: int | None, color: str) -> None:
        self.score, self.color = score, QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(8, 8, self.width() - 16, self.height() - 16)
        p.setPen(QPen(QColor(self.theme.raised), 9, Qt.PenStyle.SolidLine,
                      Qt.PenCapStyle.RoundCap))
        p.drawEllipse(r)
        if self.score is not None:
            p.setPen(QPen(self.color, 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(r, 90 * 16, -int(360 * 16 * self.score / 100))
            f = QFont(self.font())
            f.setPointSizeF(24)
            f.setWeight(QFont.Weight.DemiBold)
            p.setFont(f)
            p.setPen(QColor(self.theme.text))
            p.drawText(r.adjusted(0, -8, 0, -8), Qt.AlignmentFlag.AlignCenter, str(self.score))
            f.setPointSizeF(8)
            f.setWeight(QFont.Weight.Normal)
            p.setFont(f)
            p.setPen(QColor(self.theme.muted))
            p.drawText(r.adjusted(0, 34, 0, 0), Qt.AlignmentFlag.AlignCenter, "/ 100")
        p.end()


class CategoryBar(QWidget):
    """Name, a thin bar, the score and a one-word verdict."""

    def __init__(self, name: str, parent=None) -> None:
        super().__init__(parent)
        self.name, self.score, self.word = name, 0, ""
        self.theme: Theme = DARK
        self.setMinimumHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set(self, score: int, word: str) -> None:
        self.score, self.word = score, word
        self.update()

    def paintEvent(self, event) -> None:
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QColor(t.text))
        p.drawText(QRectF(0, 0, 110, h), Qt.AlignmentFlag.AlignVCenter, self.name)
        bar = QRectF(112, h / 2 - 3, max(40, w - 112 - 130), 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t.raised))
        p.drawRoundedRect(bar, 3, 3)
        col = t.good if self.score >= 75 else t.warn if self.score >= 55 else t.bad
        p.setBrush(QColor(col))
        p.drawRoundedRect(QRectF(bar.x(), bar.y(), bar.width() * self.score / 100, 6), 3, 3)
        p.setPen(QColor(t.text))
        p.drawText(QRectF(bar.right() + 10, 0, 34, h),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, str(self.score))
        p.setPen(QColor(col))
        p.drawText(QRectF(bar.right() + 52, 0, 80, h), Qt.AlignmentFlag.AlignVCenter, self.word)
        p.end()


class CompletenessChart(QWidget):
    """Share of Gaia stars detected per magnitude, with the 50 % limit marked."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.points: list[tuple[float, float]] = []
        self.limit: float | None = None
        self.theme: Theme = DARK
        self.setMinimumHeight(130)

    def set(self, points, limit) -> None:
        self.points, self.limit = points, limit
        self.update()

    def paintEvent(self, event) -> None:
        if not self.points:
            return
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        L, R, T, B = 34, 10, 8, 22
        w, h = self.width() - L - R, self.height() - T - B
        m0, m1 = self.points[0][0] - 0.25, self.points[-1][0] + 0.25

        def X(mag):
            return L + (mag - m0) / max(m1 - m0, 1e-6) * w

        def Y(f):
            return T + (1 - f) * h

        p.setPen(QColor(t.border))
        for f in (0, 0.5, 1):
            p.drawLine(QPointF(L, Y(f)), QPointF(L + w, Y(f)))
        p.setPen(QColor(t.muted))
        small = QFont(self.font())
        small.setPointSizeF(7.5)
        p.setFont(small)
        for f in (0, 0.5, 1):
            p.drawText(QRectF(0, Y(f) - 7, L - 6, 14),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       f"{int(f * 100)}%")
        for mag in range(int(math.ceil(m0)), int(m1) + 1, 2):
            p.drawText(QRectF(X(mag) - 14, T + h + 4, 28, 14), Qt.AlignmentFlag.AlignCenter,
                       f"{mag}")
        p.setPen(QPen(QColor(t.accent), 2))
        for (a, fa), (b, fb) in zip(self.points, self.points[1:], strict=False):
            p.drawLine(QPointF(X(a), Y(fa)), QPointF(X(b), Y(fb)))
        if self.limit:
            p.setPen(QPen(QColor(t.warn), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(X(self.limit), T), QPointF(X(self.limit), T + h))
        p.end()


def _card(theme: Theme) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("card")
    v = QVBoxLayout(card)
    v.setContentsMargins(12, 10, 12, 10)
    v.setSpacing(4)
    return card, v


def _colormap(v: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Blue (low) through teal and yellow to red (high), (h, w, 3) uint8."""
    x = np.clip((v - lo) / max(hi - lo, 1e-9), 0, 1)
    stops = np.array([[40, 80, 200], [40, 180, 190], [240, 210, 60], [230, 60, 50]], float)
    pos = x * (len(stops) - 1)
    i = np.clip(pos.astype(int), 0, len(stops) - 2)
    f = (pos - i)[..., None]
    return (stops[i] * (1 - f) + stops[i + 1] * f).astype(np.uint8)


def _upscale(grid: np.ndarray, w: int, h: int, smooth: bool = True) -> QImage:
    """A small RGBA grid scaled to w x h as a QImage."""
    a = np.ascontiguousarray(grid.astype(np.uint8))
    gh, gw = a.shape[:2]
    img = QImage(a.data, gw, gh, 4 * gw, QImage.Format.Format_RGBA8888).copy()
    mode = Qt.TransformationMode.SmoothTransformation if smooth else \
        Qt.TransformationMode.FastTransformation
    return img.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, mode)


def render_overlay(kind: str, r, w: int, h: int, theme: Theme) -> QImage | None:
    """Transparent image (w x h, the preview size) showing one aspect of the analysis."""
    if r is None or kind == "none":
        return None
    m = r.measurements
    ov = m.overlays
    k = (w / (m.width / m.work_binned))       # work pixels -> preview pixels
    out = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    def grid_image(vals: np.ndarray, lo, hi, alpha=100):
        rgb = _colormap(np.nan_to_num(vals, nan=lo), lo, hi)
        a = np.where(np.isfinite(vals), alpha, 0).astype(np.uint8)[..., None]
        return _upscale(np.concatenate([rgb, a], -1), w, h)

    if kind == "background" and ov.background is not None:
        g = ov.background
        p.drawImage(0, 0, grid_image(g, 0, max(float(np.nanmax(g)), 0.02)))
    elif kind == "noise" and ov.noise is not None:
        g = ov.noise
        p.drawImage(0, 0, grid_image(g, float(np.nanpercentile(g, 5)),
                                     max(float(np.nanpercentile(g, 95)), 1e-4)))
    elif kind == "cast" and ov.cast is not None:
        c = ov.cast
        valid = np.isfinite(c).all(-1)
        rgb = np.clip(128 + np.nan_to_num(c) * 2500, 0, 255).astype(np.uint8)
        a = np.where(valid, 150, 0).astype(np.uint8)[..., None]
        p.drawImage(0, 0, _upscale(np.concatenate([rgb, a], -1), w, h))
    elif kind == "clipping":
        for mask, col in ((ov.clipped_white, QColor(255, 60, 60, 220)),
                          (ov.clipped_black, QColor(60, 140, 255, 200))):
            if mask is None or not mask.any():
                continue
            rgba = np.zeros(mask.shape + (4,), np.uint8)
            rgba[mask] = (col.red(), col.green(), col.blue(), col.alpha())
            p.drawImage(0, 0, _upscale(rgba, w, h, smooth=False))
    elif kind == "stars":
        fw = [s.fwhm for s in ov.stars] or [1.0]
        lo, hi = np.percentile(fw, 10), np.percentile(fw, 95)
        for s in ov.stars:
            x, y = s.x * k, s.y * k
            t = (s.fwhm - lo) / max(hi - lo, 1e-6)
            col = QColor.fromHsvF(max(0.0, 0.33 * (1 - min(max(t, 0), 1))), 0.85, 1.0, 0.95)
            length = (3 + 30 * s.ellipticity) * max(1.0, w / 1600)
            dx, dy = math.cos(s.angle) * length / 2, math.sin(s.angle) * length / 2
            p.setPen(QPen(col, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(x - dx, y - dy), QPointF(x + dx, y + dy))
        grid = m.fwhm_grid
        if grid is not None:
            f = QFont()
            f.setPointSizeF(max(9, w / 90))
            f.setWeight(QFont.Weight.DemiBold)
            p.setFont(f)
            for j in range(3):
                for i in range(3):
                    if np.isfinite(grid[j, i]):
                        rect = QRectF(i * w / 3, j * h / 3, w / 3, h / 3)
                        text = f"{grid[j, i]:.1f} px · e {m.ellipticity_grid[j, i]:.2f}"
                        p.setPen(QColor(0, 0, 0, 170))
                        p.drawText(rect.translated(1.5, 1.5), Qt.AlignmentFlag.AlignCenter, text)
                        p.setPen(QColor(255, 255, 255, 235))
                        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            p.setPen(QPen(QColor(255, 255, 255, 60), 1, Qt.PenStyle.DashLine))
            for i in (1, 2):
                p.drawLine(QPointF(i * w / 3, 0), QPointF(i * w / 3, h))
                p.drawLine(QPointF(0, i * h / 3), QPointF(w, i * h / 3))
    elif kind == "problems":
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(theme.warn), 2))
        for x, y, rr in ov.rings:
            p.drawEllipse(QPointF(x * k, y * k), max(6, rr * k * 2.2), max(6, rr * k * 2.2))
        p.setPen(QPen(QColor(theme.bad), 2))
        for x, y in ov.hot_pixels:
            p.drawEllipse(QPointF(x * k, y * k), 6, 6)
        band = max(6, min(w, h) * 0.02)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(239, 107, 107, 110))
        for side in ov.edges:
            rect = {"top": QRectF(0, 0, w, band), "bottom": QRectF(0, h - band, w, band),
                    "left": QRectF(0, 0, band, h), "right": QRectF(w - band, 0, band, h)}[side]
            p.drawRect(rect)
    p.end()
    return out


# ============================================================================ window
class RateWindow(QMainWindow):
    """Load a finished picture and get a verdict, a plan and comparisons."""

    def __init__(self, cfg: Config, theme: Theme, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.cfg, self.theme = cfg, theme
        self.rating = None
        self.preview_image: QImage | None = None
        self.path: Path | None = None
        self._thread: QThread | None = None
        self._worker = None
        self._sky_thread: QThread | None = None
        self._sky_worker = None
        self._ab_thread: QThread | None = None
        self._ab_worker = None
        self.tool = "pixinsight"
        self.overlay = "none"
        self.setWindowTitle(f"{tr('rate.title')} — {APP_NAME}")
        self.setWindowIcon(icons.app_icon())
        self.setAcceptDrops(True)
        self.resize(1440, 900)
        self._build()
        self.set_theme(theme)
        self._blink = QTimer(self)
        self._blink.setInterval(650)
        self._blink.timeout.connect(self._blink_step)

    # ---- construction ------------------------------------------------------
    def _build(self) -> None:
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        tb.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.addToolBar(tb)
        self.act_open = QAction(tr("rate.open"), self)
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.setToolTip(tr("rate.open_tip"))
        self.act_open.triggered.connect(self.choose)
        self.act_again = QAction(tr("rate.again"), self)
        self.act_again.setShortcut(QKeySequence("F5"))
        self.act_again.triggered.connect(lambda: self.analyze())
        self.act_sky = QAction(tr("rate.sky"), self)
        self.act_sky.setToolTip(tr("rate.sky_tip"))
        self.act_sky.triggered.connect(self.run_sky)
        tb.addAction(self.act_open)
        tb.addAction(self.act_again)
        tb.addAction(self.act_sky)
        tb.addSeparator()
        self.object_edit = QLineEdit()
        self.object_edit.setPlaceholderText(tr("rate.object_hint"))
        self.object_edit.setToolTip(tr("rate.object_tip"))
        self.object_edit.setFixedWidth(220)
        self.object_edit.editingFinished.connect(
            lambda: self._render_compare() if self.rating is not None else None)
        tb.addWidget(self.object_edit)
        self.export_menu = QMenu(self)
        self.act_pdf = self.export_menu.addAction(tr("rate.export_pdf"))
        self.act_md = self.export_menu.addAction(tr("rate.export_md"))
        self.act_json = self.export_menu.addAction(tr("rate.export_json"))
        self.act_pdf.triggered.connect(lambda: self.export("pdf"))
        self.act_md.triggered.connect(lambda: self.export("md"))
        self.act_json.triggered.connect(lambda: self.export("json"))
        self.export_btn = QToolButton()
        self.export_btn.setText(tr("gui.action.export"))
        self.export_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.export_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.export_btn.setMenu(self.export_menu)
        tb.addWidget(self.export_btn)
        spacer = QWidget()
        spacer.setObjectName("spacer")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)
        self.act_settings = QAction(tr("gui.action.settings"), self)
        self.act_settings.setToolTip(tr("rate.settings_tip"))
        self.act_settings.triggered.connect(self._open_settings)
        tb.addAction(self.act_settings)
        self.act_help = QAction(tr("gui.action.help"), self)
        self.act_help.setToolTip(tr("rate.help_tip"))
        self.act_help.triggered.connect(lambda: show_help(self.help_topic(), self))
        tb.addAction(self.act_help)
        add_help_shortcut(self, self.help_topic)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        self.setCentralWidget(split)

        # Left: the picture and its overlays.
        left = QFrame()
        left.setObjectName("panel")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        head = QHBoxLayout()
        head.setContentsMargins(16, 10, 12, 6)
        tv = QVBoxLayout()
        tv.setSpacing(1)
        self.name = ElidedLabel(tr("rate.no_picture"))
        self.name.setObjectName("title")
        self.info = QLabel(tr("rate.drop_hint"))
        self.info.setObjectName("statLabel")
        tv.addWidget(self.name)
        tv.addWidget(self.info)
        head.addLayout(tv, 1)
        lv.addLayout(head)
        chips = QHBoxLayout()
        chips.setContentsMargins(14, 0, 12, 8)
        chips.setSpacing(6)
        self.overlay_group = QButtonGroup(self)
        self.overlay_buttons = {}
        for key in OVERLAYS:
            b = QPushButton(tr(f"rate.overlay.{key}"))
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setToolTip(tr(f"rate.overlay_tip.{key}"))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self.set_overlay(k))
            self.overlay_group.addButton(b)
            self.overlay_buttons[key] = b
            chips.addWidget(b)
        self.overlay_buttons["none"].setChecked(True)
        chips.addStretch(1)
        lv.addLayout(chips)
        self.view = PreviewView()
        self.view.set_placeholder(tr("rate.drop_hint"))
        self.overlay_item = QGraphicsPixmapItem()
        self.overlay_item.setZValue(2)
        self.survey_item = QGraphicsPixmapItem()
        self.survey_item.setZValue(1)
        self.survey_item.setOpacity(0.0)
        self.survey_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.view.scene().addItem(self.survey_item)
        self.view.scene().addItem(self.overlay_item)
        lv.addWidget(self.view, 1)
        self.status = QLabel("")
        self.status.setObjectName("statLabel")
        self.status.setContentsMargins(16, 6, 16, 8)
        lv.addWidget(self.status)
        split.addWidget(left)

        # Right: tabs.
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.verdict_tab = QWidget()
        self.findings_tab = QWidget()
        self.improve_tab = QWidget()
        self.compare_tab = QWidget()
        self.details_tab = QWidget()
        for w, key in ((self.verdict_tab, "verdict"), (self.findings_tab, "findings"),
                       (self.improve_tab, "improve"), (self.compare_tab, "compare"),
                       (self.details_tab, "details")):
            lay = QVBoxLayout(w)
            lay.setContentsMargins(0, 0, 0, 0)
            inner = QWidget()
            v = QVBoxLayout(inner)
            v.setContentsMargins(18, 14, 18, 16)
            v.setSpacing(10)
            if key == "improve":
                bar = QHBoxLayout()
                bar.setContentsMargins(18, 10, 14, 0)
                self.tool_group = QButtonGroup(self)
                self.tool_buttons = {}
                for t in ("pixinsight", "siril"):
                    b = QPushButton({"pixinsight": "PixInsight", "siril": "Siril"}[t])
                    b.setObjectName("chip")
                    b.setCheckable(True)
                    b.clicked.connect(lambda _=False, k=t: self.set_tool(k))
                    self.tool_group.addButton(b)
                    self.tool_buttons[t] = b
                    bar.addWidget(b)
                bar.addStretch(1)
                self.copy_btn = QPushButton(tr("gui.workflow.copy"))
                self.copy_btn.setObjectName("link")
                self.copy_btn.clicked.connect(self.copy_plan)
                bar.addWidget(self.copy_btn)
                lay.addLayout(bar)
            lay.addWidget(_scroll(inner), 1)
            setattr(self, f"{key}_lay", v)
            self.tabs.addTab(w, tr(f"rate.tab.{key}"))
        split.addWidget(self.tabs)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setSizes([860, 560])
        for key in ("verdict", "findings", "improve", "compare", "details"):
            self._message(getattr(self, f"{key}_lay"), tr("rate.waiting"))
        self._update_actions()

    def _message(self, lay, text: str) -> None:
        _clear(lay)
        lab = _label(text, "muted")
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addStretch(1)
        lay.addWidget(lab)
        lay.addStretch(2)

    def set_theme(self, theme: Theme) -> None:
        self.theme = t = theme
        for act, name in ((self.act_open, "image"), (self.act_again, "analyze"),
                          (self.act_sky, "solve"), (self.act_pdf, "export"),
                          (self.act_md, "list"), (self.act_json, "code"),
                          (self.act_settings, "settings"), (self.act_help, "help")):
            act.setIcon(icons.icon(name, t.text, t.faint))
        self.export_btn.setIcon(icons.icon("export", t.text, t.faint))
        self.view.theme = t
        self.view.viewport().update()
        if self.rating is not None:
            self._render_all()

    def help_topic(self) -> str:
        if self.rating is None:
            return "rate"
        return ("rate.verdict", "rate.findings", "rate.improve", "rate.compare",
                "rate.details")[max(0, self.tabs.currentIndex())]

    def _open_settings(self) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "open_settings"):
            parent.open_settings("compare")

    def _update_actions(self) -> None:
        busy = self._worker is not None
        has = self.rating is not None
        self.act_again.setEnabled(self.path is not None and not busy)
        self.act_sky.setEnabled(has and not busy and self._sky_worker is None)
        self.export_btn.setEnabled(has and not busy)
        self.act_open.setEnabled(not busy)

    # ---- loading ------------------------------------------------------------
    def choose(self) -> None:
        exts = " ".join(f"*{e}" for e in sorted(SUPPORTED))
        path, _ = QFileDialog.getOpenFileName(self, tr("rate.open"), str(self.path.parent
                                              if self.path else Path.home()),
                                              f"{tr('rate.pictures')} ({exts})")
        if path:
            self.open_picture(Path(path))

    def dragEnterEvent(self, event) -> None:
        urls = event.mimeData().urls()
        if urls and Path(urls[0].toLocalFile()).suffix.lower() in SUPPORTED:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        self.open_picture(Path(event.mimeData().urls()[0].toLocalFile()))

    def open_picture(self, path: Path) -> None:
        if self._worker is not None:
            return
        self.path = path
        self.name.setText(path.name)
        self.info.setText(str(path.parent))
        self.object_edit.setText("")
        self.analyze()

    def analyze(self) -> None:
        if self.path is None or self._worker is not None:
            return
        self.rating = None
        self._ab_results = None
        self.survey_item.setPixmap(QPixmap())
        self.overlay_item.setPixmap(QPixmap())
        for key in ("verdict", "findings", "improve", "compare", "details"):
            self._message(getattr(self, f"{key}_lay"), tr("rate.analyzing"))
        self.status.setText(tr("rate.step.load"))
        self._thread = QThread(self)
        self._worker = RateWorker(self.path, self.cfg)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(lambda s: self.status.setText(tr(f"rate.step.{s}")))
        self._worker.finished.connect(self._on_rated)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup)
        self._thread.start()
        self._update_actions()

    def _cleanup(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = self._thread = None
        self._update_actions()

    def _on_failed(self, message: str) -> None:
        self.status.setText(tr("rate.failed"))
        for key in ("verdict", "findings", "improve", "compare", "details"):
            self._message(getattr(self, f"{key}_lay"), message)
        QMessageBox.warning(self, tr("rate.title"), message)

    def _on_rated(self, rating, image: QImage, seconds: float) -> None:
        self.rating = rating
        self.preview_image = image
        self.view.set_image(image)
        p = rating.picture
        self.info.setText(f"{p.width} × {p.height} · {p.format.upper()} {p.bit_depth}"
                          + (f" · {p.software}" if p.software else ""))
        self.status.setText(tr("rate.done", seconds=f"{seconds:.1f}"))
        if not self.object_edit.text() and p.object_name:
            self.object_edit.setText(p.object_name)
        self._render_all()
        self._update_actions()
        if self.cfg.get("compare", "auto_sky", True):
            QTimer.singleShot(50, self.run_sky)

    def rejudge(self) -> None:
        """Settings changed (skill, software): judge again without measuring again."""
        from advastro.rate.judge import judge

        r = self.rating
        self.rating = judge(r.picture, r.measurements, self.cfg.section("profile"), r.sky)
        self._render_all()

    # ---- sky checks ------------------------------------------------------------
    def run_sky(self) -> None:
        if self.rating is None or self._sky_worker is not None:
            return
        hint = self.object_edit.text().strip() or None
        self._sky_thread = QThread(self)
        self._sky_worker = SkyWorker(self.rating, self.cfg, hint)
        self._sky_worker.moveToThread(self._sky_thread)
        self._sky_thread.started.connect(self._sky_worker.run)
        self._sky_worker.progress.connect(lambda s: self.status.setText(tr(f"rate.step.{s}")))
        self._sky_worker.finished.connect(self._on_sky)
        self._sky_worker.failed.connect(lambda msg: self.status.setText(msg))
        self._sky_worker.finished.connect(self._sky_thread.quit)
        self._sky_worker.failed.connect(self._sky_thread.quit)
        self._sky_thread.finished.connect(self._cleanup_sky)
        self._sky_thread.start()
        self._update_actions()
        self._render_compare()

    def _cleanup_sky(self) -> None:
        if self._sky_worker is not None:
            self._sky_worker.deleteLater()
        if self._sky_thread is not None:
            self._sky_thread.deleteLater()
        self._sky_worker = self._sky_thread = None
        self._update_actions()
        self._render_compare()

    def _on_sky(self, rating) -> None:
        self.rating = rating
        sky = rating.sky
        t = getattr(sky.target, "target", None) if sky else None
        if t is not None and not self.object_edit.text():
            self.object_edit.setText(t.label)
        if sky is not None and sky.survey is not None and self.preview_image is not None:
            a = np.ascontiguousarray((np.clip(sky.survey, 0, 1) * 255 + 0.5).astype(np.uint8))
            img = QImage(a.data, a.shape[1], a.shape[0], 3 * a.shape[1],
                         QImage.Format.Format_RGB888).copy()
            pm = QPixmap.fromImage(img.scaled(self.preview_image.size(),
                                              Qt.AspectRatioMode.IgnoreAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation))
            self.survey_item.setPixmap(pm)
        if sky is not None and sky.field is not None:
            self.status.setText(tr("rate.solved", target=t.label if t else "–"))
        elif sky is not None and "solve" in sky.errors:
            err = sky.errors["solve"]
            key = {"astap_missing": "gui.target.note.astap_missing",
                   "astap_no_database": "gui.target.note.astap_no_database"}.get(err)
            self.status.setText(tr(key) if key else err)
        self._render_all()

    # ---- rendering -------------------------------------------------------------
    def _render_all(self) -> None:
        self._render_verdict()
        self._render_findings()
        self._render_improve()
        self._render_compare()
        self._render_details()
        self.set_overlay(self.overlay)

    def set_overlay(self, key: str) -> None:
        self.overlay = key
        self.overlay_buttons[key].setChecked(True)
        if self.preview_image is None or self.rating is None:
            return
        img = render_overlay(key, self.rating, self.preview_image.width(),
                             self.preview_image.height(), self.theme)
        self.overlay_item.setPixmap(QPixmap.fromImage(img) if img is not None else QPixmap())
        legend = tr(f"rate.overlay_tip.{key}") if key != "none" else ""
        self.status.setText(legend or self.status.text())

    def _verdict_color(self, verdict: str) -> str:
        t = self.theme
        return {"excellent": t.good, "ready": t.good, "fixable": t.warn,
                "needs_work": t.bad}[verdict]

    def _render_verdict(self) -> None:
        r, t, lay = self.rating, self.theme, self.verdict_lay
        _clear(lay)
        hero = QHBoxLayout()
        hero.setSpacing(18)
        ring = ScoreRing()
        ring.theme = t
        ring.set(r.score, self._verdict_color(r.verdict))
        hero.addWidget(ring, 0, Qt.AlignmentFlag.AlignTop)
        hv = QVBoxLayout()
        hv.setSpacing(4)
        title = _label(tr(f"rate.verdict.{r.verdict}"), "hero")
        title.setStyleSheet(f"color: {self._verdict_color(r.verdict)};")
        hv.addWidget(title)
        hv.addWidget(_label(tr(f"rate.headline.{r.verdict}")))
        hv.addWidget(_label(tr("rate.judged_as", skill=tr(f"gui.settings.skills.{r.skill}")),
                            "statLabel"))
        hv.addStretch(1)
        hero.addLayout(hv, 1)
        lay.addLayout(hero)
        lay.addWidget(_label(tr("rate.categories").upper(), "section"))
        for key, c in r.categories.items():
            bar = CategoryBar(tr(f"rate.cat.{key}"))
            bar.theme = t
            bar.set(c.score, tr(f"rate.word.{c.verdict}"))
            bar.setToolTip(tr(f"rate.cat_tip.{key}"))
            lay.addWidget(bar)
        issues = r.issues
        if issues:
            lay.addWidget(_label(tr("rate.top_issues").upper(), "section"))
            for f in issues[:4]:
                lay.addWidget(self._finding_card(f, compact=True))
        if r.strengths:
            lay.addWidget(_label(tr("rate.what_works").upper(), "section"))
            text = "<br>".join(f"<span style='color:{t.good}'>✓</span>&nbsp; {f.title}"
                               for f in r.strengths[:8])
            lay.addWidget(_label(text))
        lay.addStretch(1)

    def _finding_card(self, f, compact: bool = False) -> QFrame:
        t = self.theme
        card, v = _card(t)
        col = {"critical": t.bad, "major": t.bad, "minor": t.warn, "info": t.muted,
               "good": t.good}[f.severity]
        head = QHBoxLayout()
        head.setSpacing(8)
        icon = {"critical": "reject", "major": "flag", "minor": "flag", "info": "info",
                "good": "keep"}[f.severity]
        ic = QLabel()
        ic.setPixmap(icons.icon(icon, col).pixmap(QSize(16, 16)))
        head.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        head.addWidget(_label(f"<b>{f.title}</b>&nbsp;&nbsp;<span style='color:{col};"
                              f"font-size:8pt'>{tr(f'rate.sev.{f.severity}')} · "
                              f"{tr(f'rate.cat.{f.category}')}</span>"), 1)
        if not compact:
            q = QPushButton("?")
            q.setObjectName("link")
            q.setToolTip(tr("rate.what_is_this"))
            q.setCursor(Qt.CursorShape.PointingHandCursor)
            q.setFixedWidth(22)
            q.clicked.connect(lambda _=False, i=f.id: show_help(finding_topic(i), self))
            head.addWidget(q, 0, Qt.AlignmentFlag.AlignTop)
        if f.overlay and not compact:
            show = QPushButton(tr("rate.show"))
            show.setObjectName("link")
            show.setCursor(Qt.CursorShape.PointingHandCursor)
            key = {"rings": "problems", "hot": "problems", "edges": "problems"}.get(f.overlay,
                                                                                   f.overlay)
            show.clicked.connect(lambda _=False, k=key: self.set_overlay(k))
            head.addWidget(show, 0, Qt.AlignmentFlag.AlignTop)
        v.addLayout(head)
        v.addWidget(_label(f.text, "statLabel"))
        return card

    def _render_findings(self) -> None:
        r, lay = self.rating, self.findings_lay
        _clear(lay)
        if not r.issues:
            lay.addWidget(_label(tr("rate.no_issues")))
        for f in r.issues:
            lay.addWidget(self._finding_card(f))
        if r.strengths:
            lay.addWidget(_label(tr("rate.what_works").upper(), "section"))
            for f in r.strengths:
                lay.addWidget(self._finding_card(f))
        lay.addStretch(1)

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        self.tool_buttons[tool].setChecked(True)
        if self.rating is not None:
            self._render_improve()

    def _render_improve(self) -> None:
        r, t, lay = self.rating, self.theme, self.improve_lay
        _clear(lay)
        tools = [s.lower() for s in self.cfg.get("profile", "software", ["PixInsight", "Siril"])
                 if s.lower() in ("pixinsight", "siril")] or ["pixinsight", "siril"]
        for k, b in self.tool_buttons.items():
            b.setVisible(k in tools)
        if self.tool not in tools:
            self.tool = tools[0]
        self.tool_buttons[self.tool].setChecked(True)
        self.copy_btn.setText(tr("gui.workflow.copy"))
        if not r.plan:
            lay.addWidget(_label(tr("rate.nothing_to_fix")))
            lay.addStretch(1)
            return
        lay.addWidget(_label(tr("rate.plan_intro"), "muted"))
        groups = (("critical", "major"), ("minor",), ("info",))
        names = (tr("rate.plan.first"), tr("rate.plan.then"), tr("rate.plan.polish"))
        n = 0
        for sevs, name in zip(groups, names, strict=False):
            steps = [s for s in r.plan if s.finding.severity in sevs]
            if not steps:
                continue
            lay.addWidget(_label(name.upper(), "section"))
            for s in steps:
                n += 1
                card = QFrame()
                card.setObjectName("step")
                h = QHBoxLayout(card)
                h.setContentsMargins(4, 8, 4, 8)
                h.setSpacing(12)
                num = QLabel(str(n))
                num.setObjectName("stepNumber")
                num.setFixedSize(24, 24)
                num.setAlignment(Qt.AlignmentFlag.AlignCenter)
                h.addWidget(num, 0, Qt.AlignmentFlag.AlignTop)
                v = QVBoxLayout()
                v.setSpacing(4)
                v.addWidget(_label(f"<b>{s.finding.title}</b>"))
                if s.why:
                    v.addWidget(_label(s.why, "muted"))
                tool_name = {"pixinsight": "PixInsight", "siril": "Siril"}[self.tool]
                steps_ = s.steps.get(tool_name)
                if steps_:
                    v.addWidget(_label("".join(
                        f"<p style='margin:2px 0'><span style='color:{t.accent}'>{i}.</span>"
                        f"&nbsp; {x}</p>" for i, x in enumerate(steps_, 1))))
                h.addLayout(v, 1)
                lay.addWidget(card)
        if r.capture:
            lay.addWidget(_label(tr("rate.capture").upper(), "section"))
            lay.addWidget(_label("<br>".join(f"• {c}" for c in r.capture)))
        lay.addStretch(1)

    def copy_plan(self) -> None:
        if self.rating is None:
            return
        from advastro.rate.report import to_markdown

        QGuiApplication.clipboard().setText(to_markdown(self.rating, self.tool))
        self.copy_btn.setText(tr("gui.workflow.copied"))

    # ---- compare ----------------------------------------------------------------
    def _target_name(self) -> tuple[str | None, list[str]]:
        r = self.rating
        sky = r.sky if r else None
        t = getattr(sky.target, "target", None) if sky else None
        if t is not None:
            names = [n for n in (t.messier, t.id, t.common_name) if n]
            return (t.messier or t.id), names
        typed = self.object_edit.text().strip()
        if typed:
            from advastro.sky.catalog import load

            obj = load().by_name(typed)
            if obj:
                return (obj.messier or obj.id), [n for n in (obj.messier, obj.id,
                                                             obj.common_name) if n]
            return typed, [typed]
        return None, []

    def _render_compare(self) -> None:
        if self.rating is None:
            return
        r, t, lay = self.rating, self.theme, self.compare_lay
        _clear(lay)
        sky = r.sky
        # 1. Sky checks and the survey blink.
        lay.addWidget(_label(tr("rate.sky_section").upper(), "section"))
        if self._sky_worker is not None:
            lay.addWidget(_label(tr("rate.sky_running"), "muted"))
        elif sky is None:
            row = QHBoxLayout()
            row.addWidget(_label(tr("rate.sky_not_run"), "muted"), 1)
            b = QPushButton(tr("rate.sky"))
            b.setObjectName("primary")
            b.clicked.connect(self.run_sky)
            row.addWidget(b)
            lay.addLayout(row)
        else:
            if sky.field is not None:
                tgt = getattr(sky.target, "target", None)
                f = sky.field
                lay.addWidget(_label(
                    (f"<b>{tgt.label}</b><br>" if tgt else "") +
                    tr("rate.field", ra=f"{f.ra:.3f}", dec=f"{f.dec:+.3f}",
                       scale=f"{f.scale_arcsec:.2f}", w=f"{f.width_deg:.2f}",
                       h=f"{f.height_deg:.2f}", source=f.source)))
            for key, err in sky.errors.items():
                text = {"astap_missing": tr("gui.target.note.astap_missing"),
                        "astap_no_database": tr("gui.target.note.astap_no_database")
                        }.get(err, err)
                lay.addWidget(_label(f"{tr(f'rate.err.{key}')}: {text}", "statLabel"))
            if sky.depth and sky.depth.completeness:
                card, v = _card(t)
                lim = sky.depth.limit_mag
                v.addWidget(_label(f"<b>{tr('rate.depth')}</b>"))
                v.addWidget(_label(tr("rate.depth_text",
                                      mag=f"{lim:.1f}" if lim else "–",
                                      n=f"{sky.depth.matched:,}"), "statLabel"))
                chart = CompletenessChart()
                chart.theme = t
                chart.set(sky.depth.completeness, lim)
                v.addWidget(chart)
                v.addWidget(_label(GAIA_CREDIT, "statLabel"))
                lay.addWidget(card)
            if sky.colour:
                card, v = _card(t)
                v.addWidget(_label(f"<b>{tr('rate.colour_truth')}</b>"))
                v.addWidget(_label(tr("rate.colour_text", r=f"{sky.colour.r:.2f}",
                                      n=sky.colour.stars), "statLabel"))
                v.addWidget(_label(GAIA_CREDIT, "statLabel"))
                lay.addWidget(card)
            if sky.survey is not None:
                card, v = _card(t)
                v.addWidget(_label(f"<b>{tr('rate.survey', name=sky.survey_name)}</b>"))
                v.addWidget(_label(tr("rate.survey_text"), "statLabel"))
                v.addWidget(_label(tr("rate.credit", source=survey_credit(sky.survey_name)),
                                   "statLabel"))
                row = QHBoxLayout()
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(int(self.survey_item.opacity() * 100))
                slider.valueChanged.connect(lambda val: self.survey_item.setOpacity(val / 100))
                row.addWidget(QLabel(tr("rate.yours")))
                row.addWidget(slider, 1)
                row.addWidget(QLabel(tr("rate.survey_short")))
                v.addLayout(row)
                blink = QPushButton(tr("rate.blink"))
                blink.setObjectName("chip")
                blink.setCheckable(True)
                blink.setChecked(self._blink.isActive())
                blink.toggled.connect(self._toggle_blink)
                v.addWidget(blink, 0, Qt.AlignmentFlag.AlignLeft)
                self._blink_slider = slider
                lay.addWidget(card)

        # 2. Other photographers' images.
        lay.addWidget(_label(tr("rate.others").upper(), "section"))
        name, aliases = self._target_name()
        key = str(self.cfg.get("compare", "astrobin_api_key", "")).strip()
        secret = str(self.cfg.get("compare", "astrobin_api_secret", "")).strip()
        browser = bool(self.cfg.get("compare", "browser", True))
        if not name:
            lay.addWidget(_label(tr("rate.need_name"), "muted"))
        elif key and secret:
            if getattr(self, "_ab_results", None) is None:
                row = QHBoxLayout()
                row.addWidget(_label(tr("rate.astrobin_ready", name=name), "muted"), 1)
                b = QPushButton(tr("rate.astrobin_load"))
                b.setObjectName("primary")
                b.setEnabled(self._ab_worker is None)
                b.clicked.connect(lambda: self.load_astrobin(name, aliases, key, secret))
                row.addWidget(b)
                lay.addLayout(row)
            else:
                lay.addWidget(self._gallery(self._ab_results))
        elif browser:
            lay.addWidget(_label(tr("rate.browser_text", name=name), "statLabel"))
            from advastro.rate.sky import browser_links

            row = QHBoxLayout()
            for label, url in browser_links(name):
                b = QPushButton(label)
                b.setObjectName("chip")
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.clicked.connect(lambda _=False, u=url: QDesktopServices.openUrl(QUrl(u)))
                row.addWidget(b)
            row.addStretch(1)
            lay.addLayout(row)
        else:
            lay.addWidget(_label(tr("rate.compare_off"), "muted"))
        lay.addStretch(1)

    def _toggle_blink(self, on: bool) -> None:
        if on:
            self._blink.start()
        else:
            self._blink.stop()
            self.survey_item.setOpacity(getattr(self, "_blink_slider", None).value() / 100
                                        if getattr(self, "_blink_slider", None) else 0)

    def _blink_step(self) -> None:
        self.survey_item.setOpacity(0.0 if self.survey_item.opacity() > 0.5 else 1.0)

    def load_astrobin(self, name, aliases, key, secret) -> None:
        self._ab_thread = QThread(self)
        self._ab_worker = AstroBinWorker(name, aliases, key, secret)
        self._ab_worker.moveToThread(self._ab_thread)
        self._ab_thread.started.connect(self._ab_worker.run)

        def done(results):
            self._ab_results = results
            self._render_compare()

        def fail(msg):
            self._ab_results = []
            self.status.setText(f"AstroBin: {msg}")
            self._render_compare()

        self._ab_worker.finished.connect(done)
        self._ab_worker.failed.connect(fail)
        self._ab_worker.finished.connect(self._ab_thread.quit)
        self._ab_worker.failed.connect(self._ab_thread.quit)

        def cleanup():
            self._ab_worker.deleteLater()
            self._ab_thread.deleteLater()
            self._ab_worker = self._ab_thread = None

        self._ab_thread.finished.connect(cleanup)
        self._ab_thread.start()
        self.status.setText(tr("rate.astrobin_loading"))

    def _gallery(self, results) -> QWidget:
        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        if not results:
            grid.addWidget(_label(tr("rate.astrobin_none"), "muted"), 0, 0)
            return box
        for i, (img, data) in enumerate(results):
            cell = QPushButton()
            cell.setObjectName("thumb")
            cell.setCursor(Qt.CursorShape.PointingHandCursor)
            cell.setToolTip(f"{img.title} — {img.author}")
            v = QVBoxLayout(cell)
            v.setContentsMargins(4, 4, 4, 4)
            pic = QLabel()
            pic.setFixedSize(150, 110)
            pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if data:
                pm = QPixmap()
                pm.loadFromData(data)
                pic.setPixmap(pm.scaled(150, 110, Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation))
            v.addWidget(pic)
            cap = QLabel(f"<b>{img.author}</b>" + (f" · ♥ {img.likes}" if img.likes else ""))
            cap.setObjectName("statLabel")
            v.addWidget(cap)
            cell.setMinimumSize(160, 150)
            cell.clicked.connect(lambda _=False, u=img.url: QDesktopServices.openUrl(QUrl(u)))
            grid.addWidget(cell, i // 3, i % 3)
        return box

    # ---- details ------------------------------------------------------------------
    def _render_details(self) -> None:
        r, lay = self.rating, self.details_lay
        _clear(lay)
        p, m = r.picture, r.measurements

        def fmt(v, spec="", unit=""):
            if v is None or (isinstance(v, float) and not math.isfinite(v)):
                return "–"
            return f"{v:{spec}}{unit}"

        rows = [
            (tr("rate.d.file"), f"{p.path.name} · {p.format.upper()} {p.bit_depth}"),
            (tr("rate.d.size"), f"{p.width} × {p.height} ({p.width * p.height / 1e6:.1f} MP)"
                                + (f", {tr('rate.d.binned', n=m.work_binned)}"
                                   if m.work_binned > 1 else "")),
            (tr("rate.d.colour"), tr("rate.d.mono") if p.mono else "RGB"),
            ("JPEG", fmt(m.jpeg_quality) + (f" · {m.blockiness:.2f}x" if m.jpeg_quality
                                             else "")),
            (tr("rate.d.sky"), fmt(m.sky * 100, ".1f", " %")),
            (tr("rate.d.gradient"), fmt(m.gradient_pct, ".1f", " %") +
             f" ({tr('rate.d.colour')} {m.color_gradient_pct:.1f} %)"),
            (tr("rate.d.noise"), f"{m.noise * 100:.2f} % · {tr('rate.d.mottle')} "
                                 f"{m.noise_mid * 100:.2f} % · {tr('rate.d.chroma')} "
                                 f"{m.chroma_noise * 100:.2f} %"),
            (tr("rate.d.clip"), f"{m.black_clip_pct:.2f} % / {m.white_clip_pct:.2f} %"),
            (tr("rate.d.stars"), f"{m.star_count:,} ({m.star_density:,.0f} / MP)"),
            (tr("rate.d.fwhm"), fmt(m.fwhm, ".2f", " px") + " · " +
             tr("rate.d.bright") + " " + fmt(m.fwhm_bright, ".1f", " px")),
            (tr("rate.d.ecc"), fmt(m.ellipticity, ".2f") + " · " + tr("rate.d.coherence") +
             " " + fmt(m.orientation_coherence, ".2f")),
            (tr("rate.d.corners"), fmt(m.corner_ratio, ".2f") + " · " + tr("rate.d.tilt") + " "
             + fmt(m.tilt_ratio, ".2f")),
            (tr("rate.d.rings"), fmt((m.ring_fraction or 0) * 100 if m.ring_fraction is not None
                                     else None, ".0f", " %")),
            (tr("rate.d.star_colour"), fmt(m.color_spread, ".2f")),
            (tr("rate.d.saturation"), fmt(m.saturation * 100, ".0f", " %")),
            (tr("rate.d.detail"), fmt(m.detail_ratio, ".1f", "x")),
            (tr("rate.d.hot"), str(m.hot_pixels)),
            (tr("rate.d.edges"), ", ".join(m.edges) or "–"),
        ]
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        for i, (a, b) in enumerate(rows):
            grid.addWidget(_label(a, "statLabel"), i, 0, Qt.AlignmentFlag.AlignTop)
            grid.addWidget(_label(b), i, 1)
        grid.setColumnStretch(1, 1)
        lay.addLayout(grid)
        lay.addStretch(1)

    # ---- export --------------------------------------------------------------------
    def export(self, kind: str) -> None:
        if self.rating is None:
            return
        from advastro.rate import report

        ext = {"pdf": "pdf", "md": "md", "json": "json"}[kind]
        default = str(self.rating.picture.path.with_name(
            f"{self.rating.picture.path.stem}_rating.{ext}"))
        path, _ = QFileDialog.getSaveFileName(self, tr("gui.dialog.export"), default,
                                              f"*.{ext}")
        if not path:
            return
        try:
            if kind == "pdf":
                from advastro.rate.pdf import write_pdf

                write_pdf(self.rating, path, self.preview_image.scaled(
                    1400, 1400, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation) if self.preview_image else None)
            else:
                text = report.to_markdown(self.rating) if kind == "md" else \
                    report.to_json(self.rating)
                Path(path).write_text(text, encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, tr("rate.title"), str(exc))
            return
        self.status.setText(tr("gui.status.exported", path=path))

    def closeEvent(self, event) -> None:
        self._blink.stop()
        for th in (self._thread, self._sky_thread, self._ab_thread):
            if th is not None:
                th.quit()
                th.wait(3000)
        super().closeEvent(event)


__all__ = ["RateWindow", "render_overlay"]
