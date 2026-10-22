"""Main window: drop a folder, watch subs fill in, review, keep or reject, export.

Three modes share the window, chosen with the tabs under the toolbar: Session (the
lights), Calibration (bias, darks, flats, flat darks) and Rate my pic (a finished
picture). Each keeps what it has loaded, and the toolbar shows that mode's tools.
"""

from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt, QThread, QThreadPool, QTimer
from PySide6.QtGui import QAction, QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QTableView,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from advastro import APP_NAME, SETTINGS_KEY, __version__, report
from advastro.config import ConfigError, load_config, session_thresholds
from advastro.engine.session import summarize
from advastro.gui import icons
from advastro.gui.advice_panels import TargetPanel, WorkflowPanel
from advastro.gui.calibration_dialog import CalibrationFrameDialog
from advastro.gui.help_window import add_help_shortcut, set_help_theme, show_about, show_help
from advastro.gui.models import (
    BG,
    ECC,
    FILE,
    FWHM_AS,
    FWHM_PX,
    KEEP,
    NOISE,
    PATH_ROLE,
    SNR,
    STARS,
    STATUS,
    CalModel,
    SubsFilter,
    SubsModel,
)
from advastro.gui.rate_window import RatePage
from advastro.gui.settings_dialog import SettingsDialog
from advastro.gui.theme import THEMES, stylesheet
from advastro.gui.widgets import (
    CalibrationPanel,
    ElidedLabel,
    PreviewPanel,
    StartPage,
    SummaryPanel,
)
from advastro.gui.workers import (
    AnalysisWorker,
    AssessWorker,
    CalibrationWorker,
    PreviewSignals,
    PreviewTask,
)
from advastro.i18n import tr
from advastro.readers import find_frames, supported_extensions
from advastro.session_context import find_calibration, folder_kind, session_root

LIGHT_FOLDER_NAMES = ("light", "lights", "lightframes", "light frames")
MODES = ("session", "calibration", "rate")
PICTURE_ONLY = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}
CAL_KINDS = ("darks", "flats", "darkflats", "bias")
LIGHT_WIDTHS = ((KEEP, 54), (STATUS, 30), (FWHM_PX, 78), (FWHM_AS, 74), (ECC, 60), (STARS, 72),
                (BG, 96), (NOISE, 66), (SNR, 66))
CAL_WIDTHS = {"keep": 54, "status": 30, "exposure": 70, "temp": 74, "level": 74, "noise": 64,
              "hot": 76, "glow": 60, "banding": 72, "level_pct": 70, "vignetting": 92,
              "dust": 56}
PREVIEW_CACHE = 8


def find_session_frames(folder: Path) -> tuple[list[Path], Path]:
    """Subs in the folder; else in a LIGHT subfolder; else anywhere below it."""
    frames = find_frames(folder)
    if frames:
        return frames, folder
    for child in sorted(p for p in folder.iterdir() if p.is_dir()):
        if child.name.lower() in LIGHT_FOLDER_NAMES:
            found = find_frames(child)
            if found:
                return found, child
    return find_frames(folder, recursive=True), folder


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("Miklosoft", SETTINGS_KEY)
        self.theme = THEMES.get(str(self.settings.value("theme", "dark")), THEMES["dark"])
        self.folder: Path | None = None
        self.summary = None
        self.scale: float | None = None
        self.scale_source = ""
        self.cfg = load_config()
        self.assessment = None
        self.cal_summary = None
        self.cal_only: str | None = None      # a folder with only one calibration type
        self.group = "lights"
        self.mode = "session"
        self._cal_group = "darks"             # the calibration tab last looked at
        self._session_title = ""
        self._cal_thread: QThread | None = None
        self._cal_worker = None
        self._assess_thread: QThread | None = None
        self._assess_worker = None
        self._advice_timer = QTimer(self, singleShot=True, interval=250)
        self._advice_timer.timeout.connect(self._refresh_advice)
        self._thread: QThread | None = None
        self._worker: AnalysisWorker | None = None
        self._preview_path: str | None = None
        self._preview_cache: OrderedDict[str, tuple] = OrderedDict()
        self._pool = QThreadPool.globalInstance()
        self._preview_signals = PreviewSignals()
        self._preview_signals.ready.connect(self._on_preview)
        self._preview_signals.failed.connect(self._on_preview_failed)
        self._preview_timer = QTimer(self, singleShot=True, interval=120)
        self._preview_timer.timeout.connect(self._load_preview)

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.app_icon())
        self.setAcceptDrops(True)
        self.resize(1360, 840)
        self.setMinimumSize(980, 620)

        self._build_actions()
        self.rate_page = RatePage(self.cfg, self.theme, self)
        self.rate_page.statusChanged.connect(self._update_actions)
        self.rate_page.status.hide()          # its messages go to the window's status bar
        self.rate_page.message.connect(
            lambda text: self.status_text.setText(text) if self.mode == "rate" else None)
        self._session_status = ""
        self._build_toolbar()
        self._build_pages()
        self._build_statusbar()
        self._build_shortcuts()
        self.apply_theme(self.theme.name)
        self._update_actions()
        self.start.set_recent(self._recent())

        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    # ---- construction ----------------------------------------------------
    def _build_actions(self) -> None:
        self.act_open = QAction(tr("gui.action.open"), self)
        self.act_open.setToolTip(tr("gui.tip.open"))
        self.act_open.setShortcut(QKeySequence.StandardKey.Open)
        self.act_open.triggered.connect(self.choose_folder)

        self.act_analyze = QAction(tr("gui.action.analyze"), self)
        self.act_analyze.setToolTip(tr("gui.tip.analyze"))
        self.act_analyze.setShortcut(QKeySequence("F5"))
        self.act_analyze.triggered.connect(self.analyze)

        self.act_stop = QAction(tr("gui.action.stop"), self)
        self.act_stop.setToolTip(tr("gui.tip.stop"))
        self.act_stop.setShortcut(QKeySequence("Esc"))
        self.act_stop.triggered.connect(self.stop)

        self.act_solve = QAction(tr("gui.action.solve"), self)
        self.act_solve.setToolTip(tr("gui.tip.solve"))
        self.act_solve.triggered.connect(lambda: self.assess(solve=True))

        self.act_settings = QAction(tr("gui.action.settings"), self)
        self.act_settings.setToolTip(tr("gui.tip.settings"))
        self.act_settings.setShortcut(QKeySequence("Ctrl+,"))
        self.act_settings.triggered.connect(lambda: self.open_settings())

        self.act_export_workflow = QAction(tr("gui.export.workflow"), self)
        self.act_export_workflow.triggered.connect(lambda: self.export("workflow"))

        self.act_suggest = QAction(tr("gui.action.suggest"), self)
        self.act_suggest.setToolTip(tr("gui.tip.suggest"))
        self.act_suggest.triggered.connect(lambda: self.cur_model.apply_suggestion())

        self.act_keep_all = QAction(tr("gui.action.keep_all"), self)
        self.act_keep_all.triggered.connect(lambda: self.cur_model.set_all(True))

        self.act_export_rejected = QAction(tr("gui.export.rejected"), self)
        self.act_export_rejected.triggered.connect(lambda: self.export("rejected"))
        self.act_export_kept = QAction(tr("gui.export.kept"), self)
        self.act_export_kept.triggered.connect(lambda: self.export("kept"))
        self.act_export_csv = QAction(tr("gui.export.csv"), self)
        self.act_export_csv.triggered.connect(lambda: self.export("csv"))
        self.act_export_json = QAction(tr("gui.export.json"), self)
        self.act_export_json.triggered.connect(lambda: self.export("json"))

        self.act_rate = QAction(tr("gui.action.rate"), self)
        self.act_rate.setToolTip(tr("gui.tip.rate"))
        self.act_rate.setShortcut(QKeySequence("Ctrl+R"))
        self.act_rate.triggered.connect(lambda: self.open_rate())
        self.addAction(self.act_rate)
        self.mode_shortcuts = []
        for i, mode in enumerate(MODES, 1):
            act = QAction(self)
            act.setShortcut(QKeySequence(f"Ctrl+{i}"))
            act.triggered.connect(lambda _=False, m=mode: self.set_mode(m))
            self.addAction(act)

        self.act_night = QAction(tr("gui.action.night"), self)
        self.act_night.setToolTip(tr("gui.tip.night"))
        self.act_night.setCheckable(True)
        self.act_night.setShortcut(QKeySequence("Ctrl+N"))
        self.act_night.toggled.connect(lambda on: self.apply_theme("night" if on else "dark"))

    def _build_toolbar(self) -> None:
        tb = QToolBar()
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        tb.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.addToolBar(tb)
        self.toolbar = tb

        # Tools for Session and Calibration (shown or hidden per mode by set_mode).
        for a in (self.act_open, self.act_analyze, self.act_stop, self.act_solve):
            tb.addAction(a)
        self.tb_solve = self.act_solve
        self.tb_session = [self.act_open, self.act_analyze, self.act_stop, self.act_solve,
                           tb.addSeparator()]
        tb.addAction(self.act_suggest)
        self.tb_session.append(self.act_suggest)

        self.export_menu = QMenu(self)
        for a in (self.act_export_rejected, self.act_export_kept):
            self.export_menu.addAction(a)
        self.export_menu.addSeparator()
        for a in (self.act_export_csv, self.act_export_json):
            self.export_menu.addAction(a)
        self.export_menu.addSeparator()
        self.export_menu.addAction(self.act_export_workflow)
        self.export_btn = QToolButton()
        self.export_btn.setText(tr("gui.action.export"))
        self.export_btn.setToolTip(tr("gui.tip.export"))
        self.export_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.export_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.export_btn.setMenu(self.export_menu)
        self.tb_session.append(tb.addWidget(self.export_btn))
        # Tools for Rate my pic.
        self.tb_rate = []
        for item in self.rate_page.toolbar_items():
            if item is None:
                self.tb_rate.append(tb.addSeparator())
            elif isinstance(item, QAction):
                tb.addAction(item)
                self.tb_rate.append(item)
            else:
                self.tb_rate.append(tb.addWidget(item))

        spacer = QWidget()
        spacer.setObjectName("spacer")
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)
        tb.addAction(self.act_settings)
        tb.addAction(self.act_night)
        self.help_menu = QMenu(self)
        for key, topic in (("manual", None), ("start", "start"), ("rate", "rate"),
                           ("shortcuts", "reference.shortcuts"), ("faq", "reference.faq"),
                           ("credits", "credits")):
            act = self.help_menu.addAction(tr(f"gui.help.{key}"))
            act.triggered.connect(lambda _=False, tp=topic: self.show_help(tp))
            if key == "manual":
                act.setShortcut(QKeySequence(QKeySequence.StandardKey.HelpContents))
                act.setShortcutVisibleInContextMenu(True)
        self.help_menu.addSeparator()
        about = self.help_menu.addAction(tr("gui.help.about"))
        about.triggered.connect(lambda: show_about(self))
        self.help_btn = QToolButton()
        self.help_btn.setText(tr("gui.action.help"))
        self.help_btn.setToolTip(tr("gui.tip.help"))
        self.help_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.help_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.help_btn.setMenu(self.help_menu)
        tb.addWidget(self.help_btn)
        add_help_shortcut(self, self.help_topic)

    def _build_pages(self) -> None:
        central = QWidget()
        cv = QVBoxLayout(central)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)
        bar = QWidget()
        bar.setObjectName("modeBar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(10, 2, 10, 0)
        self.mode_tabs = QTabBar()
        self.mode_tabs.setObjectName("modes")
        self.mode_tabs.setDrawBase(False)
        self.mode_tabs.setExpanding(False)
        for mode in MODES:
            i = self.mode_tabs.addTab(tr(f"gui.mode.{mode}"))
            self.mode_tabs.setTabToolTip(i, tr(f"gui.mode_tip.{mode}"))
        self.mode_tabs.currentChanged.connect(lambda i: self.set_mode(MODES[i]))
        bl.addWidget(self.mode_tabs)
        bl.addStretch(1)
        cv.addWidget(bar)
        self.stack = QStackedWidget()
        cv.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.start = StartPage()
        self.start.openRequested.connect(self.choose_folder)
        self.start.recentRequested.connect(lambda f: self.open_folder(Path(f)))
        self.start.rateRequested.connect(lambda: (self.set_mode("rate"), self.rate_page.choose()))
        self.stack.addWidget(self.start)

        # Session page: subs on the left, preview and summary on the right.
        self.model = SubsModel(self)
        self.model.keepChanged.connect(self._on_keep_changed)
        self.proxy = SubsFilter(self)
        self.proxy.setSourceModel(self.model)

        left = QFrame()
        left.setObjectName("panel")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        head = QHBoxLayout()
        head.setContentsMargins(16, 12, 12, 10)
        head.setSpacing(6)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        self.session_title = QLabel("")
        self.session_title.setObjectName("title")
        self.session_path = ElidedLabel("")
        self.session_path.setObjectName("statLabel")
        titles.addWidget(self.session_title)
        titles.addWidget(self.session_path)
        head.addLayout(titles, 1)
        self.filter_group = QButtonGroup(self)
        self.filter_buttons = []
        for mode, key in ((SubsFilter.ALL, "gui.filter.all"),
                          (SubsFilter.FLAGGED, "gui.filter.flagged"),
                          (SubsFilter.REJECTED, "gui.filter.rejected")):
            btn = QPushButton(tr(key))
            btn.setObjectName("chip")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(mode == SubsFilter.ALL)
            self.filter_group.addButton(btn, mode)
            self.filter_buttons.append(btn)
            head.addWidget(btn)
        self.filter_group.idClicked.connect(lambda mode: self.cur_proxy.set_mode(mode))
        lv.addLayout(head)

        self.groups = {"lights": (self.model, self.proxy)}
        for kind in CAL_KINDS:
            model = CalModel(kind, self)
            model.keepChanged.connect(self._on_keep_changed)
            proxy = SubsFilter(self)
            proxy.setSourceModel(model)
            self.groups[kind] = (model, proxy)
        self.frame_tabs = QTabBar()
        self.frame_tabs.setObjectName("frames")
        self.frame_tabs.setDocumentMode(True)
        self.frame_tabs.setExpanding(False)
        self.frame_tabs.setDrawBase(False)
        self.frame_tabs.currentChanged.connect(self._on_frame_tab)
        frame_row = QHBoxLayout()
        frame_row.setContentsMargins(8, 0, 12, 0)
        frame_row.addWidget(self.frame_tabs)
        frame_row.addStretch(1)
        self.cal_hint = QLabel(tr("gui.cal.double_click"))
        self.cal_hint.setObjectName("statLabel")
        self.cal_hint.hide()
        frame_row.addWidget(self.cal_hint)
        lv.addLayout(frame_row)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(FILE, Qt.SortOrder.AscendingOrder)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(32)
        hh = self.table.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(FILE, QHeaderView.ResizeMode.Stretch)
        hh.setMinimumSectionSize(28)
        for col, width in ((KEEP, 54), (STATUS, 30), (FWHM_PX, 78), (FWHM_AS, 74), (ECC, 60),
                           (STARS, 72), (BG, 96), (NOISE, 66), (SNR, 66)):
            self.table.setColumnWidth(col, width)
        self.table.selectionModel().currentRowChanged.connect(self._on_current_changed)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._table_menu)
        self.table.doubleClicked.connect(self._open_frame_details)
        lv.addWidget(self.table, 1)

        self.preview = PreviewPanel()
        self.summary_panel = SummaryPanel()
        self.summary_panel.flagClicked.connect(self._select_file)
        right = QSplitter(Qt.Orientation.Vertical)
        self.target_panel = TargetPanel()
        self.target_panel.solveRequested.connect(lambda: self.assess(solve=True))
        self.target_panel.setupRequested.connect(lambda: self.open_settings("solver"))
        self.workflow_panel = WorkflowPanel()
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.cal_panel = CalibrationPanel()
        self.cal_panel.fileClicked.connect(self._select_file)
        self.session_stack = QStackedWidget()
        self.session_stack.addWidget(self.summary_panel)
        self.session_stack.addWidget(self.cal_panel)
        self.tabs.addTab(self.session_stack, tr("gui.tab.session"))
        self.tabs.addTab(self.target_panel, tr("gui.tab.target"))
        self.tabs.addTab(self.workflow_panel, tr("gui.tab.workflow"))
        right.addWidget(self.preview)
        right.addWidget(self.tabs)
        right.setStretchFactor(0, 3)
        right.setStretchFactor(1, 2)
        right.setHandleWidth(1)
        right.setChildrenCollapsible(False)
        self.right_split = right

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        split.setHandleWidth(1)
        split.setChildrenCollapsible(False)
        self.main_split = split
        self.stack.addWidget(split)
        self.stack.addWidget(self.rate_page)
        # Calibration mode without calibration frames.
        self.cal_empty = QWidget()
        ce = QVBoxLayout(self.cal_empty)
        ce.addStretch(1)
        self.cal_empty_text = QLabel(tr("gui.cal.none_found"))
        self.cal_empty_text.setObjectName("muted")
        self.cal_empty_text.setWordWrap(True)
        self.cal_empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ce.addWidget(self.cal_empty_text)
        ce.addStretch(2)
        self.stack.addWidget(self.cal_empty)
        for key, sp in (("split_main", split), ("split_right", right)):
            state = self.settings.value(key)
            if state is not None:
                sp.restoreState(state)
            else:
                sp.setSizes([800, 560] if sp is split else [470, 330])

    def _build_statusbar(self) -> None:
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        self.status_text = QLabel(tr("gui.status.ready"))
        self.status_text.setContentsMargins(8, 0, 0, 0)
        sb.addWidget(self.status_text, 1)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(200)
        self.progress.hide()
        sb.addPermanentWidget(self.progress)
        self.progress_text = QLabel("")
        self.progress_text.setContentsMargins(6, 0, 10, 0)
        sb.addPermanentWidget(self.progress_text)
        version = QLabel(f"v{__version__}")
        version.setObjectName("statLabel")
        version.setContentsMargins(0, 0, 10, 0)
        sb.addPermanentWidget(version)

    def _build_shortcuts(self) -> None:
        QShortcut(QKeySequence("Space"), self.table, activated=lambda: self._keep_selected(None))
        QShortcut(QKeySequence("K"), self.table, activated=lambda: self._keep_selected(True))
        QShortcut(QKeySequence("R"), self.table, activated=lambda: self._keep_selected(False))

    # ---- theme -------------------------------------------------------------
    def apply_theme(self, name: str) -> None:
        self.theme = t = THEMES[name]
        self.settings.setValue("theme", name)
        app = QApplication.instance()
        app.setStyleSheet(stylesheet(t) + f"""
            QPushButton#chip {{ background: transparent; color: {t.muted}; border: 1px solid
                {t.border}; border-radius: 13px; padding: 4px 12px; font-size: 9pt; }}
            QPushButton#chip:hover {{ color: {t.text}; }}
            QPushButton#chip:checked {{ background: {t.raised}; color: {t.text};
                border-color: {t.muted}; }}
        """)
        ic = {
            self.act_open: "folder", self.act_analyze: "analyze", self.act_stop: "stop",
            self.act_suggest: "suggest", self.act_keep_all: "keep", self.act_night: "night",
            self.act_export_rejected: "reject", self.act_export_kept: "keep",
            self.act_export_csv: "table", self.act_export_json: "code",
            self.act_solve: "solve", self.act_settings: "settings",
            self.act_export_workflow: "list", self.act_rate: "rate",
        }
        for action, icon_name in ic.items():
            action.setIcon(icons.icon(icon_name, t.text, t.faint))
        self.export_btn.setIcon(icons.icon("export", t.text, t.faint))
        self.help_btn.setIcon(icons.icon("help", t.text, t.faint))
        set_help_theme(t)
        self.act_night.blockSignals(True)
        self.act_night.setChecked(name == "night")
        self.act_night.blockSignals(False)
        self.start.set_theme(t)
        self.preview.set_theme(t)
        self.preview.view.set_night(name == "night")
        self.summary_panel.theme = t
        if self.summary is not None:
            self.summary_panel.set_summary(self.summary, self.scale, self.scale_source)
        for model, _ in self.groups.values():
            model.set_theme(t)
        self.target_panel.set_theme(t)
        self.workflow_panel.set_theme(t)
        self.rate_page.set_theme(t)

    # ---- folders -----------------------------------------------------------
    def choose_folder(self) -> None:
        recent = self._recent()
        if self.folder is not None:
            start = str(self.folder.parent)
        elif recent:
            start = str(Path(recent[0]).parent)
        else:
            start = str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, tr("gui.dialog.choose"), start)
        if folder:
            self.open_folder(Path(folder))

    def open_folder(self, folder: Path) -> None:
        if self._worker is not None:
            self.stop()
        if not folder.is_dir():
            return
        frames, frames_dir = find_session_frames(folder)
        if not frames:
            QMessageBox.information(
                self, APP_NAME,
                tr("gui.msg.no_files", folder=str(folder),
                   formats=", ".join(sorted(supported_extensions()))))
            return
        self.folder = frames_dir
        self._frames = frames
        kind = folder_kind(frames)
        self.cal_only = kind if kind != "lights" else None
        self._remember(folder)
        self._session_title = (frames_dir.name if frames_dir == folder
                               else f"{folder.name}  ›  {frames_dir.name}")
        self.session_title.setText(self._session_title)
        self.session_path.setText(str(frames_dir.parent))
        self.setWindowTitle(f"{frames_dir.name} — {APP_NAME}")
        if self.cal_only:
            self.mode = "calibration"          # a folder of only darks, flats or bias
        elif self.mode == "rate":
            self.mode = "session"
        self.analyze()
        self.set_mode(self.mode)

    def _recent(self) -> list[str]:
        value = self.settings.value("recent", [])
        return [value] if isinstance(value, str) else list(value or [])

    def _remember(self, folder: Path) -> None:
        recent = [str(folder)] + [f for f in self._recent() if f != str(folder)]
        self.settings.setValue("recent", recent[:8])
        self.start.set_recent(recent)

    # ---- analysis ----------------------------------------------------------
    def analyze(self) -> None:
        if self.folder is None or self._worker is not None:
            return
        try:
            cfg = self.cfg = load_config(session_folder=self.folder)
        except ConfigError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self.assessment = None
        self.target_panel.show_message(tr("gui.target.waiting"))
        self.workflow_panel.set_advice(None, [], "intermediate")
        self.workflow_panel._message(tr("gui.workflow.waiting"))
        self._frames = find_session_frames(self.folder)[0] or self._frames
        self.summary = None
        self.cal_summary = None
        for model, _ in self.groups.values():
            model.clear()
        self.cal_panel.show_group("darks", self.groups["darks"][0], None)
        cal_files = self._calibration_files()
        self._setup_frame_tabs(cal_files)
        self.tabs.setTabEnabled(1, not self.cal_only)
        self.tabs.setTabEnabled(2, not self.cal_only)
        if self.cal_only:
            self.status_text.setText(tr("gui.status.calibrating", count=len(self._frames)))
            self.start_calibration(cal_files)
            return
        self.model.clear()
        self.summary_panel.clear()
        self._preview_cache.clear()
        self.preview.view.set_image(None)
        self.progress.setRange(0, len(self._frames))
        self.progress.setValue(0)
        self.progress.show()
        self.progress_text.setText(f"0 / {len(self._frames)}")
        self.status_text.setText(tr("gui.status.analyzing", count=len(self._frames)))

        self._thread = QThread(self)
        self._worker = AnalysisWorker(self.folder, self._frames, cfg)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.result.connect(self._on_result)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)
        self._thread.start()
        self._update_actions()

    def stop(self) -> None:
        for worker in (self._worker, self._cal_worker):
            if worker is not None:
                worker.stop()
                self.status_text.setText(tr("gui.status.stopping"))

    def _on_result(self, metrics) -> None:
        self.model.add(metrics)
        if self.model.rowCount() == 1:
            self.table.selectRow(0)

    def _on_progress(self, done: int, total: int, name: str) -> None:
        self.progress.setValue(done)
        self.progress_text.setText(f"{done} / {total}")

    def _on_finished(self, summary, scale, source, seconds: float) -> None:
        stopped = self._worker is not None and self._worker.stopped
        self.summary, self.scale, self.scale_source = summary, scale, source
        self.model.apply_summary(summary)
        self.summary_panel.set_summary(summary, scale, source)
        self._on_keep_changed()
        total, _, flagged = self.model.counts()
        key = "gui.status.stopped" if stopped else "gui.status.done"
        self.status_text.setText(tr(key, count=total, seconds=f"{seconds:.0f}",
                                    flagged=flagged))
        self.progress.hide()
        self.progress_text.setText("")
        if total:
            self.assess(solve=None)
            self.start_calibration(self._calibration_files())

    def _on_failed(self, message: str) -> None:
        self.progress.hide()
        self.status_text.setText(tr("gui.status.failed"))
        QMessageBox.critical(self, APP_NAME, message)

    def _cleanup_thread(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        if self._thread is not None:
            self._thread.deleteLater()
        self._worker = self._thread = None
        self._update_actions()

    # ---- keep / reject -----------------------------------------------------
    @property
    def cur_model(self):
        return self.groups[self.group][0]

    @property
    def cur_proxy(self):
        return self.groups[self.group][1]

    def _keep_selected(self, keep: bool | None) -> None:
        rows = sorted({self.cur_proxy.mapToSource(i).row()
                       for i in self.table.selectionModel().selectedRows()})
        self.cur_model.set_keep(rows, keep)

    def _table_menu(self, pos) -> None:
        if not self.table.selectionModel().selectedRows():
            return
        t = self.theme
        menu = QMenu(self)
        menu.addAction(icons.icon("keep", t.good), f"{tr('gui.action.keep')}\tK",
                       lambda: self._keep_selected(True))
        menu.addAction(icons.icon("reject", t.bad), f"{tr('gui.action.reject')}\tR",
                       lambda: self._keep_selected(False))
        menu.addSeparator()
        menu.addAction(self.act_keep_all)
        menu.addAction(self.act_suggest)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _on_keep_changed(self) -> None:
        total, kept, _ = self.model.counts()
        self.summary_panel.set_counts(total, kept)
        if self.group != "lights":
            self.cal_panel.show_group(self.group, self.cur_model, self.cal_summary)
        self._update_frame_tabs()
        self._update_actions()
        if self.assessment is not None and self.sender() is self.model:
            self._advice_timer.start()

    def _select_file(self, name: str) -> None:
        proxy = self.cur_proxy
        col = FILE if self.group == "lights" else self.cur_model.column("file")
        for r in range(proxy.rowCount()):
            idx = proxy.index(r, col)
            if idx.data(PATH_ROLE) and Path(idx.data(PATH_ROLE)).name == name:
                self.table.selectRow(r)
                self.table.scrollTo(idx, QAbstractItemView.ScrollHint.PositionAtCenter)
                return

    def _update_actions(self) -> None:
        running = self._worker is not None or self._cal_worker is not None
        has_session = self.folder is not None
        has_rows = self.cur_model.rowCount() > 0
        self.act_analyze.setEnabled(has_session and not running)
        self.act_stop.setEnabled(running)
        judged = self.summary is not None if self.group == "lights" else \
            self.cal_summary is not None
        self.act_suggest.setEnabled(has_rows and not running and judged)
        self.export_btn.setEnabled(has_rows and not running)
        self.act_stop.setVisible(running)
        self.act_analyze.setVisible(not running)
        assessing = self._assess_worker is not None
        self.act_solve.setEnabled(self.summary is not None and self._worker is None
                                  and not assessing and not self.cal_only)
        self.act_export_workflow.setEnabled(self.assessment is not None)
        rate = self.mode == "rate"
        for a in self.tb_session:
            a.setVisible(not rate)
        self.tb_solve.setVisible(self.mode == "session")
        self.act_export_workflow.setVisible(self.mode == "session")
        for a in self.tb_rate:
            a.setVisible(rate)
        self.act_stop.setVisible(running and not rate)
        self.act_analyze.setVisible(not running and not rate)
        self.mode_tabs.setTabEnabled(0, not self.cal_only)

    # ---- preview -------------------------------------------------------------
    def _on_current_changed(self, current, _previous) -> None:
        if not current.isValid():
            return
        self._preview_path = current.siblingAtColumn(0).data(PATH_ROLE)
        self.preview.name.setText(Path(self._preview_path).name)
        if self._preview_path in self._preview_cache:
            self._show_preview(self._preview_path, *self._preview_cache[self._preview_path])
        else:
            self.preview.info.setText(tr("gui.preview.loading"))
            self._preview_timer.start()

    def _load_preview(self) -> None:
        if self._preview_path:
            self._pool.start(PreviewTask(self._preview_path, self._preview_signals))

    def _on_preview(self, path: str, image: QImage, meta, shape) -> None:
        self._preview_cache[path] = (image, meta, shape)
        while len(self._preview_cache) > PREVIEW_CACHE:
            self._preview_cache.popitem(last=False)
        if path == self._preview_path:
            self._show_preview(path, image, meta, shape)

    def _show_preview(self, path: str, image: QImage, meta, shape) -> None:
        self._preview_cache.move_to_end(path)
        self.preview.view.set_image(image)
        parts = []
        if meta.exposure_s:
            parts.append(f"{meta.exposure_s:g} s")
        if meta.filter_name:
            parts.append(meta.filter_name)
        if meta.gain is not None:
            parts.append(f"{tr('gui.preview.gain')} {meta.gain:g}")
        if meta.temperature_c is not None:
            parts.append(f"{meta.temperature_c:.0f} °C")
        parts.append(f"{shape[-1]} × {shape[-2]}")
        parts.append(meta.bayer_pattern or tr("gui.preview.mono"))
        self.preview.info.setText("  ·  ".join(parts))

    def _on_preview_failed(self, path: str, message: str) -> None:
        if path == self._preview_path:
            self.preview.view.set_image(None)
            self.preview.info.setText(tr("gui.preview.failed", error=message))

    # ---- calibration frames ---------------------------------------------------
    def _calibration_files(self) -> dict:
        if self.folder is None:
            return {}
        if self.cal_only:
            return {self.cal_only: list(self._frames)}
        if not self.cfg.get("calibration", "analyze", True):
            return {}
        return {k: v for k, v in find_calibration(session_root(self.folder)).all_files().items()
                if v}

    def _setup_frame_tabs(self, cal_files: dict) -> None:
        self.frame_tabs.blockSignals(True)
        while self.frame_tabs.count():
            self.frame_tabs.removeTab(0)
        keys = [k for k in CAL_KINDS if k in cal_files]
        for key in keys:
            index = self.frame_tabs.addTab(tr(f"gui.frames.{key}"))
            self.frame_tabs.setTabData(index, key)
        self.frame_tabs.blockSignals(False)
        self._planned = {k: len(v) for k, v in cal_files.items()}
        if keys and self._cal_group not in keys:
            self._cal_group = keys[0]
        self._switch_group(self._cal_group if self.mode == "calibration" and keys else "lights")
        self._update_frame_tabs()
        if self.mode != "rate":
            self.set_mode(self.mode)

    def _update_frame_tabs(self) -> None:
        any_flag, frames = False, 0
        for i in range(self.frame_tabs.count()):
            key = self.frame_tabs.tabData(i)
            model = self.groups[key][0]
            total, _, flagged = model.counts()
            planned = getattr(self, "_planned", {}).get(key, total)
            count = f"{total}" if total >= planned else f"{total}/{planned}"
            label = f"{tr(f'gui.frames.{key}')}  {count}"
            self.frame_tabs.setTabText(i, label + ("  ⚠" if flagged else ""))
            any_flag |= bool(flagged)
            frames += total
        issues = self.cal_summary is not None and any(
            n.level in ("warn", "bad") for n in self.cal_summary.notes)
        label = tr("gui.mode.calibration") + (f"  {frames}" if frames else "")
        self.mode_tabs.setTabText(1, label + ("  ⚠" if any_flag or issues else ""))
        lights = self.model.rowCount()
        self.mode_tabs.setTabText(0, tr("gui.mode.session") + (f"  {lights}" if lights else ""))

    def _on_frame_tab(self, index: int) -> None:
        if index >= 0 and self.mode == "calibration":
            self._cal_group = self.frame_tabs.tabData(index)
            self._switch_group(self._cal_group)

    def _switch_group(self, key: str) -> None:
        self.group = key
        model, proxy = self.groups[key]
        proxy.set_mode(self.filter_group.checkedId() if self.filter_group.checkedId() >= 0
                       else SubsFilter.ALL)
        self.table.setModel(proxy)
        self.table.selectionModel().currentRowChanged.connect(self._on_current_changed)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        if key == "lights":
            hh.setSectionResizeMode(FILE, QHeaderView.ResizeMode.Stretch)
            for col, width in LIGHT_WIDTHS:
                self.table.setColumnWidth(col, width)
            self.table.sortByColumn(FILE, Qt.SortOrder.AscendingOrder)
            self.session_stack.setCurrentWidget(self.summary_panel)
        else:
            hh.setSectionResizeMode(model.column("file"), QHeaderView.ResizeMode.Stretch)
            for name in model.columns:
                if name in CAL_WIDTHS:
                    self.table.setColumnWidth(model.column(name), CAL_WIDTHS[name])
            self.table.sortByColumn(model.column("file"), Qt.SortOrder.AscendingOrder)
            self.cal_panel.show_group(key, model, self.cal_summary)
            self.session_stack.setCurrentWidget(self.cal_panel)
            self.tabs.setCurrentIndex(0)
            for i in range(self.frame_tabs.count()):
                if self.frame_tabs.tabData(i) == key:
                    self.frame_tabs.blockSignals(True)
                    self.frame_tabs.setCurrentIndex(i)
                    self.frame_tabs.blockSignals(False)
        if model.rowCount():
            self.table.selectRow(0)
        self._update_actions()

    def start_calibration(self, files: dict) -> None:
        if not files or self._cal_worker is not None:
            return
        total = sum(len(v) for v in files.values())
        lights = self.summary.subs[0].path if self.summary and self.summary.subs else None
        self._cal_thread = QThread(self)
        self._cal_worker = CalibrationWorker(files, self.cfg, lights)
        self._cal_worker.moveToThread(self._cal_thread)
        self._cal_thread.started.connect(self._cal_worker.run)
        self._cal_worker.result.connect(self._on_cal_result)
        self._cal_worker.progress.connect(self._on_cal_progress)
        self._cal_worker.finished.connect(self._on_cal_finished)
        self._cal_worker.failed.connect(self._on_failed)
        self._cal_worker.finished.connect(self._cal_thread.quit)
        self._cal_worker.failed.connect(self._cal_thread.quit)
        self._cal_thread.finished.connect(self._cleanup_cal_thread)
        self.progress.setRange(0, total)
        self.progress.setValue(0)
        self.progress.show()
        self._cal_thread.start()
        self._update_actions()

    def _on_cal_result(self, metrics) -> None:
        model = self.groups[metrics.kind][0]
        model.add(metrics)
        if self.group == metrics.kind and model.rowCount() == 1:
            self.table.selectRow(0)

    def _on_cal_progress(self, done: int, total: int, name: str) -> None:
        self.progress.setValue(done)
        self.progress_text.setText(tr("gui.status.cal_progress", done=done, total=total))

    def _on_cal_finished(self, summary, seconds: float) -> None:
        self.cal_summary = summary
        for kind in CAL_KINDS:
            self.groups[kind][0].apply_group(summary.group(kind))
        if self.group != "lights":
            self.cal_panel.show_group(self.group, self.cur_model, summary)
        self.progress.hide()
        self.progress_text.setText("")
        issues = sum(1 for n in summary.notes if n.level in ("warn", "bad"))
        frames = sum(len(g.frames) + len(g.masters) for g in summary.groups.values())
        self.status_text.setText(tr("gui.status.cal_done", count=frames,
                                    seconds=f"{seconds:.0f}", issues=issues))
        self._update_frame_tabs()
        if self.assessment is not None:
            self._refresh_advice()

    def _cleanup_cal_thread(self) -> None:
        if self._cal_worker is not None:
            self._cal_worker.deleteLater()
        if self._cal_thread is not None:
            self._cal_thread.deleteLater()
        self._cal_worker = self._cal_thread = None
        self._update_actions()

    # ---- target and workflow --------------------------------------------------
    def assess(self, solve: bool | None = None) -> None:
        """Locate, (optionally) plate solve, identify and advise in the background."""
        if self.summary is None or self.folder is None or self._assess_worker is not None:
            return
        busy = tr("gui.status.solving") if solve else tr("gui.status.identifying")
        self.status_text.setText(busy)
        if self.assessment is None:
            self.target_panel.show_message(busy)
        self._assess_thread = QThread(self)
        self._assess_worker = AssessWorker(self.summary, self.model.keep, self.folder,
                                           self.cfg, self.scale, solve, self.cal_summary)
        self._assess_worker.moveToThread(self._assess_thread)
        self._assess_thread.started.connect(self._assess_worker.run)
        self._assess_worker.done.connect(self._on_assessed)
        self._assess_worker.failed.connect(self._on_assess_failed)
        self._assess_worker.done.connect(self._assess_thread.quit)
        self._assess_worker.failed.connect(self._assess_thread.quit)
        self._assess_thread.finished.connect(self._cleanup_assess)
        self._assess_thread.start()
        self._update_actions()

    def _on_assessed(self, assessment) -> None:
        self.assessment = assessment
        self.target_panel.set_assessment(assessment)
        self._show_advice()
        t = assessment.target
        name = t.target.label if t.target else tr("gui.target.unknown")
        self.status_text.setText(tr("gui.status.identified", target=name,
                                    level=tr(f"gui.target.level.{t.confidence}").lower()))
        self.setWindowTitle(f"{name} · {self.folder.name} — {APP_NAME}")

    def _on_assess_failed(self, message: str) -> None:
        self.target_panel.show_message(tr("gui.target.failed", error=message))
        self.status_text.setText(tr("gui.target.failed", error=message))

    def _cleanup_assess(self) -> None:
        if self._assess_worker is not None:
            self._assess_worker.deleteLater()
        if self._assess_thread is not None:
            self._assess_thread.deleteLater()
        self._assess_worker = self._assess_thread = None
        self._update_actions()

    def _show_advice(self) -> None:
        profile = self.cfg.section("profile")
        tools = [s.lower() for s in profile.get("software", [])]
        self.workflow_panel.set_advice(self.assessment.advice, tools,
                                       profile.get("skill", "intermediate"))
        self._update_actions()

    def _refresh_advice(self) -> None:
        """Keep/reject changed: rebuild the advice from what we already know (no file I/O)."""
        from advastro.advisor.engine import advise
        from advastro.advisor.facts import build_facts

        a = self.assessment
        if a is None or self.summary is None:
            return
        profile = self.cfg.section("profile")
        a.facts = build_facts(self.summary, self.model.keep, a.meta, a.context, a.target,
                              profile, self.scale, self.cal_summary)
        tools = [s.lower() for s in profile.get("software", [])
                 if s.lower() in ("pixinsight", "siril")]
        a.advice = advise(a.facts, tools or None)
        self._show_advice()

    def open_settings(self, page: str = "general") -> None:
        dialog = SettingsDialog(self.cfg, self.theme, page, self)
        dialog.saved.connect(self._on_settings_saved)
        dialog.exec()

    def help_topic(self) -> str:
        """The manual section for what the main window shows right now."""
        if self.mode == "rate":
            return self.rate_page.help_topic()
        if self.folder is None:
            return "start.first"
        if self.mode == "calibration":
            return "calibration"
        return ("session.summary", "target", "workflow")[max(0, self.tabs.currentIndex())]

    def show_help(self, topic: str | None = None) -> None:
        show_help(topic or self.help_topic(), self)

    def open_rate(self, path: Path | None = None) -> None:
        """Switch to Rate my pic; the loaded session and calibration frames stay as they are."""
        self.set_mode("rate")
        if path is not None:
            self.rate_page.open_picture(Path(path))

    # ---- modes -------------------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        """Session, Calibration or Rate my pic: show that mode's page and tools."""
        if mode == "rate" and self.mode != "rate":
            self._session_status = self.status_text.text()
            self.status_text.setText(self.rate_page.last_message or tr("rate.waiting"))
        elif mode != "rate" and self.mode == "rate":
            self.status_text.setText(self._session_status)
        self.mode = mode
        self.mode_tabs.blockSignals(True)
        self.mode_tabs.setCurrentIndex(MODES.index(mode))
        self.mode_tabs.blockSignals(False)
        if mode == "rate":
            self.stack.setCurrentWidget(self.rate_page)
            name = self.rate_page.path.name if self.rate_page.path else None
            self.setWindowTitle(f"{name} · {tr('rate.title')} — {APP_NAME}" if name
                                else f"{tr('rate.title')} — {APP_NAME}")
        elif self.folder is None:
            self.stack.setCurrentWidget(self.start)
            self.setWindowTitle(APP_NAME)
        elif mode == "calibration":
            has_cal = self.frame_tabs.count() > 0
            self.stack.setCurrentWidget(self.main_split if has_cal else self.cal_empty)
            self.frame_tabs.setVisible(has_cal)
            if has_cal:
                self._switch_group(self._cal_group)
            self._show_side_tabs(False)
            self.session_title.setText(f"{session_root(self.folder).name}  ›  "
                                       f"{tr('gui.mode.calibration')}")
            self.cal_hint.setVisible(has_cal)
            self.setWindowTitle(f"{session_root(self.folder).name} · "
                                f"{tr('gui.mode.calibration')} — {APP_NAME}")
        else:
            self.stack.setCurrentWidget(self.main_split)
            self.frame_tabs.setVisible(False)
            self.cal_hint.setVisible(False)
            if self.group != "lights":
                self._switch_group("lights")
            self._show_side_tabs(True)
            self.session_title.setText(self._session_title)
            name = self.assessment.target.target.label if self.assessment is not None and \
                self.assessment.target.target else None
            self.setWindowTitle(f"{name + ' · ' if name else ''}{self.folder.name} — {APP_NAME}")
        self._update_actions()

    def _show_side_tabs(self, session: bool) -> None:
        """Target and Workflow belong to the session; Calibration shows only its checks."""
        self.tabs.setTabVisible(1, session)
        self.tabs.setTabVisible(2, session)
        self.tabs.setTabText(0, tr("gui.tab.session") if session else tr("gui.tab.checks"))
        if not session:
            self.tabs.setCurrentIndex(0)

    # ---- calibration frame details ---------------------------------------------
    def _open_frame_details(self, index) -> None:
        if self.group == "lights" or not index.isValid():
            return
        row = self.cur_proxy.mapToSource(index).row()
        model = self.cur_model
        if row < 0 or row >= len(model.rows):
            return
        group = self.cal_summary.group(self.group) if self.cal_summary else None
        dlg = CalibrationFrameDialog(model.rows[row], group, self.theme, self)
        dlg.exec()

    def _on_settings_saved(self, changed: set) -> None:
        try:
            self.cfg = load_config(session_folder=self.folder)
        except ConfigError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self.rate_page.cfg = self.cfg
        if self.rate_page.rating is not None and changed & {"profile", "compare"}:
            self.rate_page.rejudge()
        if "general" in changed:
            self.status_text.setText(tr("gui.status.restart_language"))
        if self.summary is None:
            return
        if "reject" in changed:  # thresholds only: re-judge the subs without re-measuring
            self.summary = summarize(self.summary.subs, session_thresholds(self.cfg),
                                     self.summary.errors)
            self.model.apply_summary(self.summary)
            self.summary_panel.set_summary(self.summary, self.scale, self.scale_source)
        if changed & {"profile", "solver", "equipment", "reject"}:
            if "equipment" in changed or ("solver" in changed and self.assessment is not None
                                          and self.assessment.target.confidence != "solved"):
                self.assess(solve=None)
            elif self.assessment is not None:
                self._refresh_advice()

    # ---- export --------------------------------------------------------------
    def export(self, kind: str) -> None:
        if self.folder is None:
            return
        base = self.folder.name if self.group == "lights" else \
            f"{session_root(self.folder).name}_{self.group}"
        spec = {
            "rejected": (f"{base}_rejected.txt", "gui.filter.text"),
            "kept": (f"{base}_kept.txt", "gui.filter.text"),
            "csv": (f"{base}_advastro.csv", "gui.filter.csv"),
            "json": (f"{base}_advastro.json", "gui.filter.json"),
            "workflow": (f"{base}_workflow_{self.workflow_panel.tool}.md", "gui.filter.markdown"),
        }[kind]
        target, _ = QFileDialog.getSaveFileName(
            self, tr("gui.dialog.export"), str(self.folder / spec[0]), tr(spec[1]))
        if not target:
            return
        if kind in ("rejected", "kept"):
            text = report.file_list(self.cur_model.kept_paths(kind == "kept"))
        elif self.group != "lights" and kind in ("csv", "json"):
            text = report.calibration_csv(self.cur_model.rows, self.cur_model.keep) \
                if kind == "csv" else report.calibration_json(self.cal_summary,
                                                              self.cur_model.keep)
        elif kind == "workflow":
            text = self.workflow_panel.markdown()
        elif self.summary is None:
            return
        elif kind == "csv":
            text = report.to_csv(self.summary, self.model.keep)
        else:
            text = report.to_json(self.summary, self.scale, self.scale_source, self.model.keep)
        try:
            Path(target).write_text(text, encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, APP_NAME, str(exc))
            return
        self.status_text.setText(tr("gui.status.exported", path=target))

    # ---- drag and drop -------------------------------------------------------
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.start.set_drag_hover(True)

    def dragLeaveEvent(self, event) -> None:
        self.start.set_drag_hover(False)

    def dropEvent(self, event) -> None:
        from advastro.rate.picture import SUPPORTED

        self.start.set_drag_hover(False)
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            # A finished picture goes to Rate my pic: always in that mode, and for picture
            # formats (JPEG, PNG, TIFF) that are never subs.
            if path.is_file() and path.suffix.lower() in SUPPORTED and \
                    (self.mode == "rate" or path.suffix.lower() in PICTURE_ONLY):
                self.open_rate(path)
                return
            if path.is_file():
                path = path.parent
            if path.is_dir():
                self.open_folder(path)
                return

    # ---- lifecycle -------------------------------------------------------------
    def closeEvent(self, event) -> None:
        if self._worker is not None:
            self._worker.stop()
        if self._cal_worker is not None:
            self._cal_worker.stop()
        for thread in (self._thread, self._assess_thread, self._cal_thread):
            if thread is not None:
                thread.quit()
                thread.wait(3000)
        self.rate_page.shutdown()
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("split_main", self.main_split.saveState())
        self.settings.setValue("split_right", self.right_split.saveState())
        super().closeEvent(event)
