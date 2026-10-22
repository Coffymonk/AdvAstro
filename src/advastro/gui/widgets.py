"""Reusable widgets: start page, stat cards, session summary and image preview."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from advastro.gui import icons
from advastro.gui.theme import DARK, Theme
from advastro.i18n import tr


class ElidedLabel(QLabel):
    """A label that shortens long text in the middle and shows it in full as a tooltip."""

    def __init__(self, text: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(40)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._full = ""
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802 - Qt API name
        self._full = text
        self.setToolTip(text)
        self._elide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        shown = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideMiddle,
                                              max(10, self.width()))
        super().setText(shown)


def icon_label(name: str, color: str, size: int) -> QLabel:
    label = QLabel()
    label.setPixmap(icons.icon(name, color).pixmap(QSize(size, size)))
    label.setFixedSize(size, size)
    return label


class StartPage(QWidget):
    """Empty state: one big, obvious target for a folder of subs."""

    openRequested = Signal()
    recentRequested = Signal(str)
    rateRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.theme: Theme = DARK
        self._hover = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 48, 48, 48)
        outer.addStretch(1)

        self.zone = QWidget()
        self.zone.setFixedWidth(560)
        z = QVBoxLayout(self.zone)
        z.setContentsMargins(40, 44, 40, 36)
        z.setSpacing(10)
        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        z.addWidget(self.icon)
        z.addSpacing(6)
        hero = QLabel(tr("gui.start.title"))
        hero.setObjectName("hero")
        hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        z.addWidget(hero)
        sub = QLabel(tr("gui.start.subtitle"))
        sub.setObjectName("muted")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        z.addWidget(sub)
        z.addSpacing(14)
        row = QHBoxLayout()
        row.addStretch(1)
        self.open_btn = QPushButton(tr("gui.start.choose"))
        self.open_btn.setObjectName("primary")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.clicked.connect(self.openRequested)
        row.addWidget(self.open_btn)
        self.rate_btn = QPushButton(tr("gui.start.rate"))
        self.rate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.rate_btn.setToolTip(tr("gui.tip.rate"))
        self.rate_btn.clicked.connect(self.rateRequested)
        row.addWidget(self.rate_btn)
        row.addStretch(1)
        z.addLayout(row)
        z.addSpacing(10)
        formats = QLabel(tr("gui.start.formats"))
        formats.setObjectName("statLabel")
        formats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        z.addWidget(formats)

        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(self.zone)
        h.addStretch(1)
        outer.addLayout(h)

        self.recent_box = QWidget()
        self.recent_box.setFixedWidth(560)
        self.recent_layout = QVBoxLayout(self.recent_box)
        self.recent_layout.setContentsMargins(4, 22, 4, 0)
        self.recent_layout.setSpacing(2)
        h2 = QHBoxLayout()
        h2.addStretch(1)
        h2.addWidget(self.recent_box)
        h2.addStretch(1)
        outer.addLayout(h2)
        outer.addStretch(2)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self.icon.setPixmap(icons.icon("folder", theme.accent).pixmap(QSize(44, 44)))
        self.update()

    def set_recent(self, folders: list[str]) -> None:
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        folders = [f for f in folders if Path(f).is_dir()][:5]
        if not folders:
            return
        title = QLabel(tr("gui.start.recent").upper())
        title.setObjectName("section")
        self.recent_layout.addWidget(title)
        for f in folders:
            p = Path(f)
            metrics = self.fontMetrics()
            parent = metrics.elidedText(str(p.parent), Qt.TextElideMode.ElideMiddle, 380)
            btn = QPushButton(f"{p.name}     {parent}")
            btn.setObjectName("link")
            btn.setToolTip(str(p))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, f=f: self.recentRequested.emit(f))
            self.recent_layout.addWidget(btn)

    def set_drag_hover(self, hover: bool) -> None:
        self._hover = hover
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        t = self.theme
        r = QRectF(self.zone.geometry()).adjusted(0.5, 0.5, -0.5, -0.5)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(r, 16, 16)
        fill = QColor(t.accent if self._hover else t.surface)
        if self._hover:
            fill.setAlpha(28)
        p.fillPath(path, fill)
        pen = QPen(QColor(t.accent if self._hover else t.faint), 1.5)
        pen.setDashPattern([5, 4])
        p.setPen(pen)
        p.drawPath(path)


class StatCard(QFrame):
    def __init__(self, label: str, tooltip: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setToolTip(tooltip)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(1)
        self.value = QLabel("–")
        self.value.setObjectName("statValue")
        self.label = QLabel(label)
        self.label.setObjectName("statLabel")
        self.detail = QLabel("")
        self.detail.setObjectName("statLabel")
        lay.addWidget(self.value)
        lay.addWidget(self.label)
        lay.addWidget(self.detail)
        self.detail.hide()
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    def set(self, value: str, detail: str = "") -> None:
        self.value.setText(value)
        self.detail.setText(detail)
        self.detail.setVisible(bool(detail))


class SummaryPanel(QFrame):
    """Session numbers at a glance plus the list of flagged subs."""

    flagClicked = Signal(str)  # file name

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.theme: Theme = DARK
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(10)

        title = QLabel(tr("gui.summary.title").upper())
        title.setObjectName("section")
        lay.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(8)
        self.cards = {
            "subs": StatCard(tr("gui.summary.kept"), tr("gui.tip.kept")),
            "fwhm": StatCard(tr("gui.summary.fwhm"), tr("gui.tip.fwhm")),
            "ecc": StatCard(tr("gui.summary.ecc"), tr("gui.tip.ecc")),
            "stars": StatCard(tr("gui.summary.stars"), tr("gui.tip.stars")),
            "noise": StatCard(tr("gui.summary.noise"), tr("gui.tip.noise")),
            "sampling": StatCard(tr("gui.summary.sampling"), tr("gui.tip.sampling")),
        }
        for i, card in enumerate(self.cards.values()):
            grid.addWidget(card, i // 3, i % 3)
        lay.addLayout(grid)

        self.flags_title = QLabel(tr("gui.summary.flags").upper())
        self.flags_title.setObjectName("section")
        lay.addSpacing(4)
        lay.addWidget(self.flags_title)
        self.flags = QListWidget()
        self.flags.setWordWrap(True)
        self.flags.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.flags.itemClicked.connect(
            lambda it: self.flagClicked.emit(it.data(Qt.ItemDataRole.UserRole)))
        lay.addWidget(self.flags, 1)
        self.empty = QLabel(tr("gui.summary.none"))
        self.empty.setObjectName("muted")
        lay.addWidget(self.empty)
        self.empty.hide()

    def clear(self) -> None:
        for card in self.cards.values():
            card.set("–")
        self.flags.clear()
        self.empty.hide()

    def set_counts(self, total: int, kept: int) -> None:
        self.cards["subs"].set(f"{kept} / {total}" if total else "–")

    def set_summary(self, summary, scale: float | None, scale_source: str) -> None:
        m = summary.medians

        def fmt(v, spec):
            return "–" if v is None else format(v, spec)

        fwhm_as = m.get("fwhm_arcsec")
        self.cards["fwhm"].set(
            f"{fmt(fwhm_as, '.2f')}″" if fwhm_as else f"{fmt(m.get('fwhm_px'), '.2f')} px",
            f"{fmt(m.get('fwhm_px'), '.2f')} px" if fwhm_as else "")
        self.cards["ecc"].set(fmt(m.get("eccentricity"), ".2f"))
        self.cards["stars"].set(fmt(m.get("star_count"), ",.0f"))
        self.cards["noise"].set(fmt(m.get("noise_adu"), ".1f"), tr("gui.summary.adu"))
        sampling = summary.sampling or ""
        self.cards["sampling"].set(
            tr(f"gui.sampling.{sampling.replace(' ', '_')}") if sampling else "–",
            f"{scale:.2f}″/px" if scale else tr("gui.summary.scale_unknown"))
        self.cards["sampling"].setToolTip(
            tr(f"sampling.{sampling}") + (f"\n{tr('gui.summary.scale_from', source=scale_source)}"
                                          if scale else ""))

        self.flags.clear()
        t = self.theme
        for f in summary.flags:
            item = QListWidgetItem(icons.icon("flag", t.warn), f"{f.file}\n{f.reason}")
            item.setData(Qt.ItemDataRole.UserRole, f.file)
            self.flags.addItem(item)
        for name, err in summary.errors.items():
            item = QListWidgetItem(icons.icon("reject", t.bad), f"{name}\n{err}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.flags.addItem(item)
        has = bool(summary.flags or summary.errors)
        self.flags.setVisible(has)
        self.empty.setVisible(not has)


class PreviewView(QGraphicsView):
    """Zoomable, pannable preview. Wheel zooms, drag pans, double-click toggles fit / 1:1."""

    zoomChanged = Signal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self._item = QGraphicsPixmapItem()
        self._item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.scene().addItem(self._item)
        self._fit = True
        self._night = False
        self._image: QImage | None = None
        self._placeholder = tr("gui.preview.empty")
        self.theme: Theme = DARK
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHints(QPainter.RenderHint.SmoothPixmapTransform)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMinimumHeight(180)

    def set_placeholder(self, text: str) -> None:
        self._placeholder = text
        self.viewport().update()

    def set_night(self, night: bool) -> None:
        """Night mode shows the image in red only, to protect dark adaptation."""
        self._night = night
        if self._image is not None:
            self._item.setPixmap(self._pixmap(self._image))

    def _pixmap(self, image: QImage) -> QPixmap:
        pm = QPixmap.fromImage(image)
        if self._night:
            painter = QPainter(pm)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
            painter.fillRect(pm.rect(), QColor(235, 30, 20))
            painter.end()
        return pm

    def set_image(self, image: QImage | None) -> None:
        self._image = image
        if image is None:
            self._item.setPixmap(QPixmap())
            self.viewport().update()
            return
        self._item.setPixmap(self._pixmap(image))
        self.scene().setSceneRect(QRectF(image.rect()))
        if self._fit:
            self.fit()

    def has_image(self) -> bool:
        return not self._item.pixmap().isNull()

    def fit(self) -> None:
        self._fit = True
        if self.has_image():
            self.fitInView(self._item, Qt.AspectRatioMode.KeepAspectRatio)
        self.zoomChanged.emit(self.transform().m11())

    def actual(self) -> None:
        self._fit = False
        self.resetTransform()
        self.zoomChanged.emit(1.0)

    def wheelEvent(self, event) -> None:
        if not self.has_image():
            return
        factor = 1.0015 ** event.angleDelta().y()
        current = self.transform().m11()
        if 0.05 < current * factor < 16:
            self._fit = False
            self.scale(factor, factor)
            self.zoomChanged.emit(self.transform().m11())

    def mouseDoubleClickEvent(self, event) -> None:
        if self._fit:
            self.actual()
        else:
            self.fit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._fit:
            self.fit()

    def drawForeground(self, painter: QPainter, rect) -> None:
        if self.has_image():
            return
        painter.save()
        painter.resetTransform()
        painter.setPen(QColor(self.theme.muted))
        painter.drawText(self.viewport().rect(), Qt.AlignmentFlag.AlignCenter, self._placeholder)
        painter.restore()


class PreviewPanel(QFrame):
    """Preview with a one-line caption and small zoom buttons."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(16, 10, 10, 8)
        bar.setSpacing(4)
        text = QVBoxLayout()
        text.setSpacing(1)
        self.name = ElidedLabel(tr("gui.preview.title"))
        self.name.setObjectName("title")
        self.info = QLabel(tr("gui.preview.hint"))
        self.info.setObjectName("statLabel")
        text.addWidget(self.name)
        text.addWidget(self.info)
        bar.addLayout(text, 1)
        self.zoom_label = QLabel("")
        self.zoom_label.setObjectName("statLabel")
        bar.addWidget(self.zoom_label)
        self.fit_btn = QToolButton()
        self.fit_btn.setToolTip(tr("gui.preview.fit"))
        self.actual_btn = QToolButton()
        self.actual_btn.setToolTip(tr("gui.preview.actual"))
        bar.addWidget(self.fit_btn)
        bar.addWidget(self.actual_btn)
        lay.addLayout(bar)
        self.view = PreviewView()
        lay.addWidget(self.view, 1)
        self.fit_btn.clicked.connect(self.view.fit)
        self.actual_btn.clicked.connect(self.view.actual)
        self.view.zoomChanged.connect(
            lambda z: self.zoom_label.setText(f"{z * 100:.0f}%" if self.view.has_image() else ""))

    def set_theme(self, theme: Theme) -> None:
        self.view.theme = theme
        self.fit_btn.setIcon(icons.icon("fit", theme.muted))
        self.actual_btn.setIcon(icons.icon("actual", theme.muted))
        self.view.viewport().update()


KIND_NAMES = ("bias", "darks", "flats", "darkflats")


class CalibrationPanel(QFrame):
    """Numbers for one calibration frame type, and every calibration check."""

    fileClicked = Signal(str)

    LEVEL_ICON = {"good": "keep", "info": "info", "warn": "flag", "bad": "reject"}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        self.theme: Theme = DARK
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 12)
        lay.setSpacing(10)
        self.title = QLabel("")
        self.title.setObjectName("section")
        lay.addWidget(self.title)
        self.grid = QGridLayout()
        self.grid.setSpacing(8)
        self.cards = [StatCard("") for _ in range(6)]
        for i, card in enumerate(self.cards):
            self.grid.addWidget(card, i // 3, i % 3)
        lay.addLayout(self.grid)
        checks = QLabel(tr("gui.cal.checks").upper())
        checks.setObjectName("section")
        lay.addSpacing(4)
        lay.addWidget(checks)
        self.notes = QListWidget()
        self.notes.setWordWrap(True)
        self.notes.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.notes.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.notes.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.notes.itemClicked.connect(
            lambda it: it.data(Qt.ItemDataRole.UserRole)
            and self.fileClicked.emit(it.data(Qt.ItemDataRole.UserRole)))
        lay.addWidget(self.notes, 1)
        self.waiting = QLabel(tr("gui.cal.waiting"))
        self.waiting.setObjectName("muted")
        self.waiting.setWordWrap(True)
        lay.addWidget(self.waiting)

    def show_group(self, kind: str, model, summary) -> None:
        """kind: bias | darks | flats | darkflats; summary may be None while analyzing."""
        self.title.setText(tr(f"gui.frames.{kind}").upper())
        total, kept, _ = model.counts()
        g = summary.group(kind) if summary else None
        m = g.medians if g else {}

        def f(key, spec, unit=""):
            v = m.get(key)
            return "–" if v is None else format(v, spec) + unit

        if kind == "flats":
            values = [
                ("gui.cal.kept", f"{kept} / {total}" if total else "–", ""),
                ("gui.cal.level_pct", f("level_pct", ".0f", " %"), "gui.tip.level_pct"),
                ("gui.cal.vignetting", f("vignetting_pct", ".0f", " %"), "gui.tip.vignetting"),
                ("gui.cal.dust", f("dust_spots", ".0f"), "gui.tip.dust"),
                ("gui.cal.exposure", f"{g.setting('exposure_s'):g} s"
                 if g and g.setting("exposure_s") else "–", ""),
                ("gui.cal.clipped", f("clipped_pct", ".2f", " %"), "gui.tip.clipped"),
            ]
        else:
            values = [
                ("gui.cal.kept", f"{kept} / {total}" if total else "–", ""),
                ("gui.cal.level", f("median_adu", ",.0f"), "gui.tip.level"),
                ("gui.cal.noise", f("noise_adu", ".1f"), "gui.tip.cal_noise"),
                ("gui.cal.hot", f("hot_pixels", ",.0f"), "gui.tip.hot"),
                ("gui.cal.glow", f("glow_adu", ".0f"), "gui.tip.glow"),
                ("gui.cal.exposure", f"{g.setting('exposure_s'):g} s"
                 if g and g.setting("exposure_s") else "–", ""),
            ]
        for card, (label, value, tip) in zip(self.cards, values, strict=True):
            card.label.setText(tr(label))
            card.setToolTip(tr(tip) if tip else "")
            card.set(value)

        self.notes.clear()
        if summary is None:
            self.notes.hide()
            self.waiting.show()
            return
        self.waiting.hide()
        self.notes.show()
        t = self.theme
        color = {"good": t.good, "info": t.muted, "warn": t.warn, "bad": t.bad}
        order = {"bad": 0, "warn": 1, "info": 2, "good": 3}
        notes = sorted(summary.notes, key=lambda n: (n.kind != kind, order[n.level]))
        for n in notes:
            group = tr(f"gui.frames.{n.kind}") if n.kind in KIND_NAMES else ""
            item = QListWidgetItem(icons.icon(self.LEVEL_ICON[n.level], color[n.level]),
                                   f"{group}\n{n.text}" if group else n.text)
            self.notes.addItem(item)
        if g:
            for fl in g.flags:
                item = QListWidgetItem(icons.icon("flag", t.warn), f"{fl.file}\n{fl.reason}")
                item.setData(Qt.ItemDataRole.UserRole, fl.file)
                self.notes.addItem(item)
