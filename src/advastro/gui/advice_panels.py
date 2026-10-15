"""Target and Workflow panels: what you imaged, and how to process it."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from advastro.advisor.engine import STAGES, Advice, to_markdown
from advastro.gui import icons
from advastro.gui.theme import DARK, Theme
from advastro.i18n import tr
from advastro.sky.solve import _tangent


def _label(text: str = "", name: str | None = None, wrap: bool = True) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return lab


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            _clear(item.layout())


def _scroll(inner: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setWidget(inner)
    return area


# ------------------------------------------------------------------ framing sketch ----
class FramingSketch(QWidget):
    """The camera field as a rectangle and the target's catalogued outline on top."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(180, 110)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(130)
        self.theme: Theme = DARK
        self.sky = None
        self.target = None

    def set_data(self, sky, target) -> None:
        self.sky, self.target = sky, target
        self.update()

    def paintEvent(self, event) -> None:
        if not self.sky:
            return
        t = self.theme
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fw, fh = self.sky.width_deg, self.sky.height_deg
        tw = th = 0.0
        dx = dy = 0.0
        if self.target and self.target.major_arcmin:
            tw = self.target.major_arcmin / 60
            th = (self.target.minor_arcmin or self.target.major_arcmin) / 60
            ex, ny = _tangent(self.target.ra, self.target.dec, self.sky.ra, self.sky.dec)
            rot = math.radians(self.sky.rotation_deg or 0.0)
            dx = ex * math.cos(rot) + ny * math.sin(rot)
            dy = -ex * math.sin(rot) + ny * math.cos(rot)
        span_w = max(fw, 2 * abs(dx) + tw) * 1.12
        span_h = max(fh, 2 * abs(dy) + th) * 1.12
        k = min((self.width() - 8) / span_w, (self.height() - 8) / span_h)
        c = QPointF(self.width() / 2, self.height() / 2)

        if tw:
            p.save()
            p.translate(c.x() - dx * k, c.y() - dy * k)
            pa = (self.target.position_angle or 0.0) - (self.sky.rotation_deg or 0.0)
            p.rotate(-pa + 90)
            fill = QColor(t.accent)
            fill.setAlpha(46)
            p.setBrush(fill)
            p.setPen(QPen(QColor(t.accent), 1.2))
            p.drawEllipse(QRectF(-tw * k / 2, -th * k / 2, tw * k, th * k))
            p.restore()
        p.setBrush(Qt.BrushStyle.NoBrush)
        pen = QPen(QColor(t.text), 1.4)
        p.setPen(pen)
        p.drawRoundedRect(QRectF(c.x() - fw * k / 2, c.y() - fh * k / 2, fw * k, fh * k), 3, 3)
        p.setPen(QColor(t.muted))
        p.drawText(QRectF(c.x() - fw * k / 2 + 6, c.y() - fh * k / 2 + 2, fw * k, 18),
                   Qt.AlignmentFlag.AlignLeft, tr("gui.target.your_field"))


# ---------------------------------------------------------------------- target panel ----
class TargetPanel(QWidget):
    solveRequested = Signal()
    setupRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.theme: Theme = DARK
        inner = QWidget()
        self.lay = QVBoxLayout(inner)
        self.lay.setContentsMargins(16, 14, 16, 14)
        self.lay.setSpacing(8)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll(inner))
        self._assessment = None
        self.show_message(tr("gui.target.waiting"))

    def show_message(self, text: str, busy: bool = False) -> None:
        _clear(self.lay)
        lab = _label(text, "muted")
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lay.addStretch(1)
        self.lay.addWidget(lab)
        self.lay.addStretch(2)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        if self._assessment is not None:
            self.set_assessment(self._assessment)

    def set_assessment(self, a) -> None:
        self._assessment = a
        _clear(self.lay)
        t = self.theme
        report = a.target
        obj = report.target

        # Heading: family icon, name, designations, type and constellation
        head = QHBoxLayout()
        head.setSpacing(12)
        ic = QLabel()
        ic.setPixmap(icons.icon(icons.FAMILY_ICON.get(report.family, "unknown"), t.accent)
                     .pixmap(QSize(40, 40)))
        ic.setFixedSize(44, 44)
        head.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(2)
        if obj:
            text.addWidget(_label(obj.label, "hero"))
            ids = [d for d in obj.designations if d != obj.label][:4]
            if ids:
                text.addWidget(_label(" · ".join(ids), "muted"))
            kind = tr(f"sky.type.{obj.type_key}")
            where = (tr("gui.target.in_constellation", constellation=report.constellation)
                     if report.constellation else "")
            text.addWidget(_label(f"{kind}{where}"))
        else:
            text.addWidget(_label(tr("gui.target.unknown"), "hero"))
            text.addWidget(_label(tr("gui.target.unknown_hint"), "muted"))
        head.addLayout(text, 1)
        self.lay.addLayout(head)

        # How sure we are
        level = report.confidence
        color = {"solved": t.good, "pointing": t.warn, "name": t.warn}.get(level, t.muted)
        chip = _label(f"<span style='color:{color}'>●</span>&nbsp; "
                      f"{tr(f'gui.target.level.{level}')} · {report.source}", "statLabel")
        self.lay.addWidget(chip)

        # Actions when the solution could be better
        if level != "solved":
            row = QHBoxLayout()
            solve = QPushButton(icons.icon("solve", t.text), tr("gui.target.solve_now"))
            solve.clicked.connect(self.solveRequested)
            row.addWidget(solve)
            if a.solve_note in ("astap_missing", "astap_no_database"):
                setup = QPushButton(tr("gui.target.setup_astap"))
                setup.setObjectName("link")
                setup.clicked.connect(self.setupRequested)
                row.addWidget(setup)
            row.addStretch(1)
            self.lay.addLayout(row)
            if a.solve_note:
                note = tr(f"gui.target.note.{a.solve_note}") \
                    if a.solve_note in ("astap_missing", "astap_no_database", "no_position") \
                    else a.solve_note
                self.lay.addWidget(_label(note, "statLabel"))

        # Framing sketch and its sentence
        if report.sky:
            sketch = FramingSketch()
            sketch.theme = t
            sketch.set_data(report.sky, obj)
            self.lay.addSpacing(4)
            self.lay.addWidget(sketch)
            if report.framing:
                self.lay.addWidget(_label(tr(f"gui.target.framing.{report.framing}",
                                             pct=f"{(report.coverage or 0) * 100:.0f}")))

        # Facts grid
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 130)
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        rows = []
        if obj and obj.major_arcmin:
            size = f"{obj.major_arcmin:g}′" + (f" × {obj.minor_arcmin:g}′"
                                              if obj.minor_arcmin else "")
            rows.append((tr("gui.target.size"), size))
        if obj and obj.magnitude is not None:
            rows.append((tr("gui.target.magnitude"), f"{obj.magnitude:.1f}"))
        if report.sky:
            s = report.sky
            rows.append((tr("gui.target.field"),
                         f"{s.width_deg * 60:.0f}′ × {s.height_deg * 60:.0f}′"))
            rows.append((tr("gui.target.scale"), f"{s.scale_arcsec:.2f}″/px"))
            rows.append((tr("gui.target.center"), f"RA {s.ra:.4f}°  Dec {s.dec:+.4f}°"))
            if s.rotation_deg is not None:
                rows.append((tr("gui.target.rotation"), f"{s.rotation_deg:.1f}°"))
        if report.galactic_latitude is not None:
            b = report.galactic_latitude
            rows.append((tr("gui.target.galactic"),
                         f"{b:+.1f}°" + (f"  · {tr('gui.target.milky_way')}"
                                         if report.milky_way else "")))
        for i, (k, v) in enumerate(rows):
            grid.addWidget(_label(k, "statLabel"), i, 0)
            grid.addWidget(_label(v), i, 1)
        if rows:
            self.lay.addSpacing(4)
            self.lay.addLayout(grid)

        if report.others:
            title = _label(tr("gui.target.also").upper(), "section")
            self.lay.addSpacing(6)
            self.lay.addWidget(title)
            names = []
            for o in report.others[:8]:
                kind = tr(f"sky.type.{o.type_key}").lower()
                names.append(f"{o.label} <span style='color:{t.muted}'>({kind})</span>")
            self.lay.addWidget(_label(" · ".join(names)))
        self.lay.addStretch(1)


# -------------------------------------------------------------------- workflow panel ----
class WorkflowPanel(QWidget):
    toolChanged = Signal(str)

    TOOL_NAMES = {"pixinsight": "PixInsight", "siril": "Siril"}

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.theme: Theme = DARK
        self.advice: Advice | None = None
        self.tool = "pixinsight"
        self.skill = "intermediate"
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(16, 10, 12, 6)
        bar.setSpacing(6)
        self.tool_group = QButtonGroup(self)
        self.tool_buttons: dict[str, QPushButton] = {}
        for key, name in self.TOOL_NAMES.items():
            btn = QPushButton(name)
            btn.setObjectName("chip")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=key: self.set_tool(k))
            self.tool_group.addButton(btn)
            self.tool_buttons[key] = btn
            bar.addWidget(btn)
        bar.addStretch(1)
        self.copy_btn = QPushButton(tr("gui.workflow.copy"))
        self.copy_btn.setObjectName("link")
        self.copy_btn.setToolTip(tr("gui.workflow.copy_tip"))
        self.copy_btn.clicked.connect(self.copy)
        bar.addWidget(self.copy_btn)
        outer.addLayout(bar)
        inner = QWidget()
        self.lay = QVBoxLayout(inner)
        self.lay.setContentsMargins(16, 6, 16, 16)
        self.lay.setSpacing(8)
        outer.addWidget(_scroll(inner), 1)
        self._message(tr("gui.workflow.waiting"))

    def _message(self, text: str) -> None:
        _clear(self.lay)
        lab = _label(text, "muted")
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lay.addStretch(1)
        self.lay.addWidget(lab)
        self.lay.addStretch(2)

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._render()

    def set_advice(self, advice: Advice | None, tools: list[str], skill: str) -> None:
        self.advice, self.skill = advice, skill
        tools = [t for t in tools if t in self.TOOL_NAMES] or list(self.TOOL_NAMES)
        for key, btn in self.tool_buttons.items():
            btn.setVisible(key in tools)
        if self.tool not in tools:
            self.tool = tools[0]
        self.tool_buttons[self.tool].setChecked(True)
        self._render()

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        self.tool_buttons[tool].setChecked(True)
        self.toolChanged.emit(tool)
        self._render()

    def markdown(self) -> str:
        return to_markdown(self.advice, self.tool) if self.advice else ""

    def copy(self) -> None:
        if self.advice:
            QGuiApplication.clipboard().setText(self.markdown())
            self.copy_btn.setText(tr("gui.workflow.copied"))

    def _render(self) -> None:
        if self.advice is None:
            return
        self.copy_btn.setText(tr("gui.workflow.copy"))
        _clear(self.lay)
        t = self.theme
        for rec in self.advice.insights:
            self.lay.addWidget(self._insight(rec))
        stage = None
        n = 0
        for rec in self.advice.steps:
            if rec.stage != stage:
                stage = rec.stage
                title = _label(tr(f"gui.stage.{stage}").upper(), "section")
                title.setContentsMargins(0, 10, 0, 0)
                self.lay.addWidget(title)
            n += 1
            self.lay.addWidget(self._step(n, rec, t))
        self.lay.addStretch(1)

    def _insight(self, rec) -> QFrame:
        t = self.theme
        card = QFrame()
        card.setObjectName("card")
        h = QHBoxLayout(card)
        h.setContentsMargins(12, 10, 12, 10)
        h.setSpacing(10)
        ic = QLabel()
        ic.setPixmap(icons.icon("insight", t.warn).pixmap(QSize(18, 18)))
        ic.setFixedWidth(20)
        h.addWidget(ic, 0, Qt.AlignmentFlag.AlignTop)
        v = QVBoxLayout()
        v.setSpacing(2)
        v.addWidget(_label(f"<b>{rec.title}</b>"))
        v.addWidget(_label(rec.why, "statLabel"))
        h.addLayout(v, 1)
        return card

    def _step(self, n: int, rec, t: Theme) -> QFrame:
        card = QFrame()
        card.setObjectName("step")
        h = QHBoxLayout(card)
        h.setContentsMargins(4, 6, 4, 6)
        h.setSpacing(12)
        num = QLabel(str(n))
        num.setObjectName("stepNumber")
        num.setFixedSize(24, 24)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(num, 0, Qt.AlignmentFlag.AlignTop)
        v = QVBoxLayout()
        v.setSpacing(3)
        conf = {"high": t.good, "medium": t.warn, "low": t.muted}.get(rec.confidence, t.muted)
        v.addWidget(_label(f"<b>{rec.title}</b>&nbsp;&nbsp;<span style='color:{conf};"
                           f"font-size:8pt'>● {tr(f'gui.conf.{rec.confidence}')}</span>"))
        tool = rec.tools.get(self.tool)
        if tool:
            v.addWidget(_label(f"<span style='color:{t.accent}'>{tool.process}</span>"))
            if self.skill != "advanced" and tool.menu and tool.menu != tool.process:
                v.addWidget(_label(tool.menu, "statLabel"))
            if tool.settings:
                v.addWidget(_label("<br>".join(f"• {s}" for s in tool.settings)))
            if tool.note:
                v.addWidget(_label(tool.note, "statLabel"))
        if rec.why and (self.skill != "advanced" or not tool):
            why = _label(rec.why, "muted")
            v.addWidget(why)
        h.addLayout(v, 1)
        return card


def stage_names() -> list[str]:
    return list(STAGES)
