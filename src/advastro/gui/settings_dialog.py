"""Settings window: one page per topic, every option explained in place."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from advastro import APP_NAME
from advastro.config import Config, save_user_config, user_config_path
from advastro.gui import icons
from advastro.gui.help_window import add_help_shortcut, show_help
from advastro.gui.theme import Theme
from advastro.i18n import available_languages, tr
from advastro.sky.solve import detect_astap

ASTAP_URL = "https://www.hnsky.org/astap.htm"
STRICTNESS = {  # fwhm_sigma, eccentricity_max, star_count_fraction, background_sigma
    "lenient": (4.0, 0.7, 0.45, 5.0),
    "normal": (3.0, 0.6, 0.6, 4.0),
    "strict": (2.0, 0.5, 0.75, 3.0),
}
LANGUAGE_NAMES = {"en": "English", "sv": "Svenska"}
PAGES = ("general", "equipment", "selection", "solver", "software", "style", "compare")
PAGE_ICONS = {"general": "settings", "equipment": "star", "selection": "keep",
              "solver": "solve", "software": "list", "style": "image", "compare": "rate"}
ASTROBIN_KEY_URL = "https://www.astrobin.com/api/request-key/"


def _hint(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("statLabel")
    label.setWordWrap(True)
    return label


def _page(title: str, intro: str) -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    lay = QVBoxLayout(page)
    lay.setContentsMargins(28, 22, 28, 22)
    lay.setSpacing(10)
    head = QLabel(title)
    head.setObjectName("hero")
    lay.addWidget(head)
    lay.addWidget(_hint(intro))
    lay.addSpacing(6)
    return page, lay


def _form() -> QFormLayout:
    form = QFormLayout()
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    form.setHorizontalSpacing(18)
    form.setVerticalSpacing(10)
    return form


class SettingsDialog(QDialog):
    saved = Signal(set)  # names of the sections that changed

    def __init__(self, cfg: Config, theme: Theme, page: str = "general", parent=None) -> None:
        super().__init__(parent)
        self.cfg, self.theme = cfg, theme
        self.setWindowTitle(f"{tr('gui.settings.title')} — {APP_NAME}")
        self.setMinimumSize(780, 560)
        self.setModal(True)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFixedWidth(200)
        self.nav.setIconSize(QSize(18, 18))
        self.pages = QStackedWidget()
        outer.addWidget(self.nav)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.addWidget(self.pages, 1)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(28, 10, 20, 18)
        self.where = _hint(tr("gui.settings.saved_in", path=str(user_config_path())))
        help_btn = QPushButton(icons.icon("help", theme.muted), tr("gui.action.help"))
        help_btn.setObjectName("link")
        help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        help_btn.clicked.connect(lambda: show_help(self._help_topic(), self))
        buttons.addWidget(help_btn)
        buttons.addWidget(self.where, 1)
        cancel = QPushButton(tr("gui.settings.cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(tr("gui.settings.save"))
        save.setObjectName("primary")
        save.setDefault(True)
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        right.addLayout(buttons)
        outer.addLayout(right, 1)

        for key in PAGES:
            item = QListWidgetItem(icons.icon(PAGE_ICONS[key], theme.text),
                                   tr(f"gui.settings.page.{key}"))
            self.nav.addItem(item)
            self.pages.addWidget(getattr(self, f"_build_{key}")())
        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.nav.setCurrentRow(PAGES.index(page) if page in PAGES else 0)
        self._original = self._values()
        add_help_shortcut(self, self._help_topic)

    def _help_topic(self) -> str:
        return f"settings.{PAGES[max(0, self.nav.currentRow())]}"

    # ---- pages ---------------------------------------------------------------
    def _build_general(self) -> QWidget:
        page, lay = _page(tr("gui.settings.page.general"), tr("gui.settings.general.intro"))
        form = _form()
        self.language = QComboBox()
        for code in available_languages():
            self.language.addItem(LANGUAGE_NAMES.get(code, code), code)
        self.language.setCurrentIndex(max(0, self.language.findData(
            self.cfg.get("general", "language", "en"))))
        form.addRow(tr("gui.settings.language"), self.language)
        self.jobs = QSpinBox()
        self.jobs.setRange(0, 64)
        self.jobs.setSpecialValueText(tr("gui.settings.auto"))
        self.jobs.setValue(int(self.cfg.get("general", "jobs", 0)))
        form.addRow(tr("gui.settings.workers"), self.jobs)
        lay.addLayout(form)
        lay.addWidget(_hint(tr("gui.settings.general.hint")))
        lay.addStretch(1)
        return page

    def _build_equipment(self) -> QWidget:
        page, lay = _page(tr("gui.settings.page.equipment"), tr("gui.settings.equipment.intro"))
        form = _form()
        self.focal = QDoubleSpinBox()
        self.focal.setRange(0, 20000)
        self.focal.setDecimals(0)
        self.focal.setSuffix(" mm")
        self.focal.setSpecialValueText(tr("gui.settings.from_headers"))
        self.focal.setValue(float(self.cfg.get("equipment", "focal_length_mm", 0.0)))
        self.pixel = QDoubleSpinBox()
        self.pixel.setRange(0, 50)
        self.pixel.setDecimals(2)
        self.pixel.setSuffix(" µm")
        self.pixel.setSpecialValueText(tr("gui.settings.from_headers"))
        self.pixel.setValue(float(self.cfg.get("equipment", "pixel_size_um", 0.0)))
        form.addRow(tr("gui.settings.focal"), self.focal)
        form.addRow(tr("gui.settings.pixel"), self.pixel)
        lay.addLayout(form)
        self.scale_label = QLabel("")
        self.scale_label.setObjectName("title")
        lay.addWidget(self.scale_label)
        self.focal.valueChanged.connect(self._update_scale)
        self.pixel.valueChanged.connect(self._update_scale)
        self._update_scale()
        lay.addStretch(1)
        return page

    def _update_scale(self) -> None:
        if self.focal.value() and self.pixel.value():
            scale = 206.264806 * self.pixel.value() / self.focal.value()
            self.scale_label.setText(tr("gui.settings.scale", scale=f"{scale:.2f}"))
        else:
            self.scale_label.setText("")

    def _build_selection(self) -> QWidget:
        page, lay = _page(tr("gui.settings.page.selection"), tr("gui.settings.selection.intro"))
        form = _form()
        self.strictness = QComboBox()
        for key in ("lenient", "normal", "strict"):
            self.strictness.addItem(tr(f"gui.settings.strict.{key}"), key)
        self.strictness.addItem(tr("gui.settings.strict.custom"), "custom")
        form.addRow(tr("gui.settings.strictness"), self.strictness)
        adv = form
        r = self.cfg.section("reject")
        self.fwhm_sigma = self._spin(1.0, 8.0, 0.5, r.get("fwhm_sigma", 3.0))
        self.ecc_max = self._spin(0.2, 0.95, 0.05, r.get("eccentricity_max", 0.6))
        self.stars_frac = self._spin(0.1, 0.95, 0.05, r.get("star_count_fraction", 0.6))
        self.bg_sigma = self._spin(1.0, 10.0, 0.5, r.get("background_sigma", 4.0))
        adv.addRow(tr("gui.settings.fwhm_sigma"), self.fwhm_sigma)
        adv.addRow(tr("gui.settings.ecc_max"), self.ecc_max)
        adv.addRow(tr("gui.settings.stars_frac"), self.stars_frac)
        adv.addRow(tr("gui.settings.bg_sigma"), self.bg_sigma)
        lay.addLayout(adv)
        lay.addWidget(_hint(tr("gui.settings.selection.hint")))
        self.cal_analyze = QCheckBox(tr("gui.settings.cal_analyze"))
        self.cal_analyze.setChecked(bool(self.cfg.get("calibration", "analyze", True)))
        lay.addSpacing(8)
        lay.addWidget(self.cal_analyze)
        lay.addStretch(1)

        current = (self.fwhm_sigma.value(), self.ecc_max.value(), self.stars_frac.value(),
                   self.bg_sigma.value())
        preset = next((k for k, v in STRICTNESS.items()
                       if all(abs(a - b) < 1e-6 for a, b in zip(v, current, strict=True))),
                      "custom")
        self.strictness.setCurrentIndex(self.strictness.findData(preset))
        self.strictness.currentIndexChanged.connect(self._apply_preset)
        for w in (self.fwhm_sigma, self.ecc_max, self.stars_frac, self.bg_sigma):
            w.valueChanged.connect(self._mark_custom)
        return page

    def _spin(self, lo: float, hi: float, step: float, value: float) -> QDoubleSpinBox:
        s = QDoubleSpinBox()
        s.setRange(lo, hi)
        s.setSingleStep(step)
        s.setDecimals(2)
        s.setValue(float(value))
        return s

    def _apply_preset(self) -> None:
        key = self.strictness.currentData()
        if key in STRICTNESS:
            widgets = (self.fwhm_sigma, self.ecc_max, self.stars_frac, self.bg_sigma)
            for w, v in zip(widgets, STRICTNESS[key], strict=True):
                w.blockSignals(True)
                w.setValue(v)
                w.blockSignals(False)

    def _mark_custom(self) -> None:
        self.strictness.blockSignals(True)
        self.strictness.setCurrentIndex(self.strictness.findData("custom"))
        self.strictness.blockSignals(False)

    def _build_solver(self) -> QWidget:
        page, lay = _page(tr("gui.settings.page.solver"), tr("gui.settings.solver.intro"))
        s = self.cfg.section("solver")
        self.auto_solve = QCheckBox(tr("gui.settings.auto_solve"))
        self.auto_solve.setChecked(bool(s.get("auto_solve", True)))
        lay.addWidget(self.auto_solve)
        form = _form()
        self.astap_path = QLineEdit(s.get("astap_path", ""))
        self.astap_path.setPlaceholderText(tr("gui.settings.detect_auto"))
        self.db_path = QLineEdit(s.get("database_path", ""))
        self.db_path.setPlaceholderText(tr("gui.settings.detect_auto"))
        form.addRow(tr("gui.settings.astap_program"),
                    self._with_browse(self.astap_path, folder=False))
        form.addRow(tr("gui.settings.astap_db"), self._with_browse(self.db_path, folder=True))
        self.radius = self._spin(1, 180, 5, s.get("search_radius_deg", 30.0))
        self.radius.setDecimals(0)
        self.radius.setSuffix(" °")
        self.timeout = self._spin(10, 600, 10, s.get("timeout_s", 90.0))
        self.timeout.setDecimals(0)
        self.timeout.setSuffix(" s")
        form.addRow(tr("gui.settings.radius"), self.radius)
        form.addRow(tr("gui.settings.timeout"), self.timeout)
        lay.addLayout(form)

        status = QFrame()
        status.setObjectName("card")
        sl = QVBoxLayout(status)
        sl.setContentsMargins(14, 12, 14, 12)
        self.astap_status = QLabel("")
        self.astap_status.setWordWrap(True)
        self.astap_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        sl.addWidget(self.astap_status)
        row = QHBoxLayout()
        detect = QPushButton(icons.icon("solve", self.theme.text), tr("gui.settings.detect"))
        detect.clicked.connect(self._detect)
        get = QPushButton(tr("gui.settings.get_astap"))
        get.setObjectName("link")
        get.setCursor(Qt.CursorShape.PointingHandCursor)
        get.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(ASTAP_URL)))
        row.addWidget(detect)
        row.addWidget(get)
        row.addStretch(1)
        sl.addLayout(row)
        lay.addWidget(status)
        lay.addWidget(_hint(tr("gui.settings.solver.hint")))
        lay.addStretch(1)
        self._detect()
        return page

    def _with_browse(self, edit: QLineEdit, folder: bool) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(edit, 1)
        btn = QPushButton(tr("gui.settings.browse"))

        def browse() -> None:
            start = edit.text() or str(Path.home())
            path = (QFileDialog.getExistingDirectory(self, tr("gui.settings.astap_db"), start)
                    if folder else
                    QFileDialog.getOpenFileName(self, tr("gui.settings.astap_program"), start)[0])
            if path:
                edit.setText(path)
                self._detect()

        btn.clicked.connect(browse)
        h.addWidget(btn)
        return w

    def _detect(self) -> None:
        install = detect_astap(self.astap_path.text().strip(), self.db_path.text().strip())
        t = self.theme
        if install.ready:
            color, text = t.good, tr("gui.settings.astap_ready",
                                     program=str(install.executable),
                                     dbs=", ".join(install.databases))
            if not self.astap_path.text():
                self.astap_path.setPlaceholderText(str(install.executable))
        elif install.executable:
            color, text = t.warn, tr("gui.settings.astap_no_db", program=str(install.executable))
        else:
            color, text = t.warn, tr("gui.settings.astap_missing")
        self.astap_status.setText(f"<span style='color:{color}'>●</span>&nbsp; {text}")

    def _build_software(self) -> QWidget:
        page, lay = _page(tr("gui.settings.page.software"), tr("gui.settings.software.intro"))
        owned = {s.lower() for s in self.cfg.get("profile", "software", [])}
        paid = {s.lower() for s in self.cfg.get("profile", "paid_addons", [])}
        self.software_boxes: dict[str, QCheckBox] = {}
        for group, names, chosen in (
                ("gui.settings.programs", ["PixInsight", "Siril", "GraXpert", "StarNet"], owned),
                ("gui.settings.paid", ["BlurXTerminator", "NoiseXTerminator", "StarXTerminator"],
                 paid)):
            title = QLabel(tr(group).upper())
            title.setObjectName("section")
            lay.addWidget(title)
            for name in names:
                box = QCheckBox(name)
                box.setChecked(name.lower() in chosen)
                self.software_boxes[name] = box
                lay.addWidget(box)
            lay.addSpacing(8)
        lay.addWidget(_hint(tr("gui.settings.software.hint")))
        lay.addStretch(1)
        return page

    def _build_style(self) -> QWidget:
        page, lay = _page(tr("gui.settings.page.style"), tr("gui.settings.style.intro"))
        form = _form()
        self.aesthetic = QComboBox()
        for key in ("natural", "HOO", "SHO"):
            self.aesthetic.addItem(tr(f"gui.settings.aesthetics.{key.lower()}"), key)
        self.aesthetic.setCurrentIndex(max(0, self.aesthetic.findData(
            self.cfg.get("profile", "aesthetic", "natural"))))
        self.skill = QComboBox()
        for key in ("beginner", "intermediate", "advanced"):
            self.skill.addItem(tr(f"gui.settings.skills.{key}"), key)
        self.skill.setCurrentIndex(max(0, self.skill.findData(
            self.cfg.get("profile", "skill", "intermediate"))))
        form.addRow(tr("gui.settings.aesthetic"), self.aesthetic)
        form.addRow(tr("gui.settings.skill"), self.skill)
        lay.addLayout(form)
        lay.addWidget(_hint(tr("gui.settings.style.hint")))
        lay.addStretch(1)
        return page

    def _build_compare(self) -> QWidget:
        page, lay = _page(tr("gui.settings.page.compare"), tr("gui.settings.compare.intro"))
        c = self.cfg.section("compare")
        self.auto_sky = QCheckBox(tr("gui.settings.compare.auto_sky"))
        self.auto_sky.setChecked(bool(c.get("auto_sky", True)))
        self.survey = QCheckBox(tr("gui.settings.compare.survey"))
        self.survey.setChecked(bool(c.get("survey", True)))
        lay.addWidget(self.auto_sky)
        lay.addWidget(self.survey)
        lay.addSpacing(10)
        lay.addWidget(_hint(tr("gui.settings.compare.others").upper()))
        form = _form()
        self.ab_key = QLineEdit(str(c.get("astrobin_api_key", "")))
        self.ab_key.setPlaceholderText(tr("gui.settings.compare.optional"))
        self.ab_secret = QLineEdit(str(c.get("astrobin_api_secret", "")))
        self.ab_secret.setPlaceholderText(tr("gui.settings.compare.optional"))
        self.ab_secret.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow(tr("gui.settings.compare.key"), self.ab_key)
        form.addRow(tr("gui.settings.compare.secret"), self.ab_secret)
        lay.addLayout(form)
        get = QPushButton(tr("gui.settings.compare.get_key"))
        get.setObjectName("link")
        get.setCursor(Qt.CursorShape.PointingHandCursor)
        get.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(ASTROBIN_KEY_URL)))
        lay.addWidget(get, 0, Qt.AlignmentFlag.AlignLeft)
        self.browser = QCheckBox(tr("gui.settings.compare.browser"))
        self.browser.setChecked(bool(c.get("browser", True)))
        lay.addWidget(self.browser)
        lay.addWidget(_hint(tr("gui.settings.compare.hint")))
        lay.addStretch(1)
        return page

    # ---- saving ------------------------------------------------------------------
    def _values(self) -> dict[str, dict]:
        programs = [n for n in ("PixInsight", "Siril", "GraXpert", "StarNet")
                    if self.software_boxes[n].isChecked()]
        paid = [n for n in ("BlurXTerminator", "NoiseXTerminator", "StarXTerminator")
                if self.software_boxes[n].isChecked()]
        return {
            "general": {"language": self.language.currentData(), "jobs": self.jobs.value()},
            "equipment": {"focal_length_mm": self.focal.value(),
                          "pixel_size_um": self.pixel.value()},
            "reject": {"fwhm_sigma": self.fwhm_sigma.value(),
                       "eccentricity_max": self.ecc_max.value(),
                       "star_count_fraction": self.stars_frac.value(),
                       "background_sigma": self.bg_sigma.value(),
                       "strictness": (self.strictness.currentData()
                                      if self.strictness.currentData() != "custom"
                                      else "normal")},
            "calibration": {"analyze": self.cal_analyze.isChecked()},
            "solver": {"auto_solve": self.auto_solve.isChecked(),
                       "astap_path": self.astap_path.text().strip(),
                       "database_path": self.db_path.text().strip(),
                       "search_radius_deg": self.radius.value(),
                       "timeout_s": self.timeout.value()},
            "compare": {"auto_sky": self.auto_sky.isChecked(),
                        "survey": self.survey.isChecked(),
                        "browser": self.browser.isChecked(),
                        "astrobin_api_key": self.ab_key.text().strip(),
                        "astrobin_api_secret": self.ab_secret.text().strip()},
            "profile": {"software": programs, "paid_addons": paid,
                        "aesthetic": self.aesthetic.currentData(),
                        "skill": self.skill.currentData()},
        }

    def _save(self) -> None:
        values = self._values()
        changed = {k for k, v in values.items() if v != self._original.get(k)}
        if changed:
            save_user_config({k: values[k] for k in changed})
        self.saved.emit(changed)
        self.accept()
