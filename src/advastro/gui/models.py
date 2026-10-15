"""Table model for the subs list: one row per sub, keep/reject per row."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QBrush, QColor

from advastro.engine.metrics import SubMetrics
from advastro.engine.session import SessionSummary, SubFlag
from advastro.gui import icons
from advastro.gui.theme import DARK, Theme
from advastro.i18n import tr
from advastro.naming import short_names

KEEP, STATUS, FILE, FWHM_PX, FWHM_AS, ECC, STARS, BG, NOISE, SNR = range(10)

# column: (header key, tooltip key, attribute, format)
_COLUMNS = {
    KEEP: ("gui.col.keep", "gui.tip.keep", None, None),
    STATUS: ("", "gui.tip.status", None, None),
    FILE: ("gui.col.file", None, "file", None),
    FWHM_PX: ("gui.col.fwhm_px", "gui.tip.fwhm", "fwhm_px", "{:.2f}"),
    FWHM_AS: ("gui.col.fwhm_as", "gui.tip.fwhm_as", "fwhm_arcsec", "{:.2f}"),
    ECC: ("gui.col.ecc", "gui.tip.ecc", "eccentricity", "{:.2f}"),
    STARS: ("gui.col.stars", "gui.tip.stars", "star_count", "{:,.0f}"),
    BG: ("gui.col.bg", "gui.tip.bg", "background_adu", "{:,.0f}"),
    NOISE: ("gui.col.noise", "gui.tip.noise", "noise_adu", "{:.1f}"),
    SNR: ("gui.col.snr", "gui.tip.snr", "snr_estimate", "{:,.0f}"),
}
_FLAG_COLUMNS = {
    "fwhm_px": (FWHM_PX, FWHM_AS),
    "eccentricity": (ECC,),
    "star_count": (STARS,),
    "background_adu": (BG,),
}
NUMERIC = {FWHM_PX, FWHM_AS, ECC, STARS, BG, NOISE, SNR}
SORT_ROLE = Qt.ItemDataRole.UserRole
PATH_ROLE = Qt.ItemDataRole.UserRole + 1
FLAGGED_ROLE = Qt.ItemDataRole.UserRole + 2
KEEP_ROLE = Qt.ItemDataRole.UserRole + 3


class SubsModel(QAbstractTableModel):
    keepChanged = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.rows: list[SubMetrics] = []
        self.sub_flags: dict[str, list[SubFlag]] = {}
        self.keep: dict[str, bool] = {}
        self._user_set: set[str] = set()
        self.theme: Theme = DARK
        self.short: dict[str, str] = {}

    # ---- data management -------------------------------------------------
    def clear(self) -> None:
        self.beginResetModel()
        self.rows, self.sub_flags, self.keep, self._user_set = [], {}, {}, set()
        self.short = {}
        self.endResetModel()
        self.keepChanged.emit()

    def add(self, metrics: SubMetrics) -> None:
        n = len(self.rows)
        self.beginInsertRows(QModelIndex(), n, n)
        self.rows.append(metrics)
        self.keep.setdefault(metrics.file, True)
        self.endInsertRows()
        self._update_short_names()
        self.keepChanged.emit()

    def apply_summary(self, summary: SessionSummary) -> None:
        """Attach flags and pre-select: flagged subs are suggested for rejection."""
        self.sub_flags = {}
        for f in summary.flags:
            self.sub_flags.setdefault(f.file, []).append(f)
        for s in self.rows:
            if s.file not in self._user_set:
                self.keep[s.file] = s.file not in self.sub_flags
        self._refresh_all()
        self.keepChanged.emit()

    def apply_suggestion(self) -> None:
        self._user_set.clear()
        for s in self.rows:
            self.keep[s.file] = s.file not in self.sub_flags
        self._refresh_all()
        self.keepChanged.emit()

    def set_all(self, keep: bool) -> None:
        for s in self.rows:
            self.keep[s.file] = keep
            self._user_set.add(s.file)
        self._refresh_all()
        self.keepChanged.emit()

    def set_keep(self, rows: list[int], keep: bool | None = None) -> None:
        """Set (or toggle when keep is None) the keep state of source rows."""
        if not rows:
            return
        target = keep if keep is not None else not all(self.keep[self.rows[r].file] for r in rows)
        for r in rows:
            name = self.rows[r].file
            self.keep[name] = target
            self._user_set.add(name)
            self.dataChanged.emit(self.index(r, 0), self.index(r, self.columnCount() - 1))
        self.keepChanged.emit()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._refresh_all()

    def kept_paths(self, keep: bool) -> list[str]:
        return [s.path or s.file for s in self.rows if self.keep.get(s.file, True) == keep]

    def counts(self) -> tuple[int, int, int]:
        total = len(self.rows)
        kept = sum(1 for s in self.rows if self.keep.get(s.file, True))
        flagged = sum(1 for s in self.rows if s.file in self.sub_flags)
        return total, kept, flagged

    def _update_short_names(self) -> None:
        """Show only the parts of the file names that differ between subs.

        'Light_NGC 7000_300.0s_Bin1_gain201_20261014-212101_287deg_-10.0C_0009.fit'
        becomes '20261014-212101_287deg_0009' when the other parts are the same for all.
        """
        old = dict(self.short)
        self.short = short_names([r.file for r in self.rows])
        if old != self.short and self.rows:
            self.dataChanged.emit(self.index(0, FILE), self.index(len(self.rows) - 1, FILE))

    def _refresh_all(self) -> None:
        if self.rows:
            self.dataChanged.emit(self.index(0, 0),
                                  self.index(len(self.rows) - 1, self.columnCount() - 1))

    # ---- Qt model API ----------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: B008
        return len(_COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation != Qt.Orientation.Horizontal or section not in _COLUMNS:
            return None
        header, tip, _, _ = _COLUMNS[section]
        if role == Qt.ItemDataRole.DisplayRole:
            return tr(header) if header else ""
        if role == Qt.ItemDataRole.ToolTipRole and tip:
            return tr(tip)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            align = Qt.AlignmentFlag.AlignRight if section in NUMERIC else \
                Qt.AlignmentFlag.AlignLeft
            return int(align | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):  # noqa: A003 - Qt API name
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == KEEP:
            base |= Qt.ItemFlag.ItemIsUserCheckable
        return base

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        s = self.rows[index.row()]
        col = index.column()
        _, _, attr, fmt = _COLUMNS[col]
        kept = self.keep.get(s.file, True)
        flags = self.sub_flags.get(s.file, [])
        t = self.theme

        if role == Qt.ItemDataRole.CheckStateRole and col == KEEP:
            return Qt.CheckState.Checked if kept else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.DisplayRole:
            if attr is None:
                return None
            if col == FILE:
                return self.short.get(s.file, s.file)
            value = getattr(s, attr)
            if value is None:
                return "–"
            return fmt.format(value) if fmt else str(value)
        if role == SORT_ROLE:
            if col == KEEP:
                return int(kept)
            if col == STATUS:
                return len(flags)
            value = getattr(s, attr) if attr else None
            return value if value is not None else float("inf")
        if role == Qt.ItemDataRole.DecorationRole and col == STATUS and flags:
            return icons.icon("flag", t.warn)
        if role == Qt.ItemDataRole.ToolTipRole:
            if flags:
                return "\n".join(f"• {f.reason}" for f in flags)
            if col == KEEP:
                return tr("gui.tip.keep")
            return s.path or s.file
        if role == SORT_ROLE + 10:  # full file name, used to find a row by name
            return s.file
        if role == Qt.ItemDataRole.TextAlignmentRole:
            align = Qt.AlignmentFlag.AlignRight if col in NUMERIC else Qt.AlignmentFlag.AlignLeft
            return int(align | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            if any(col in _FLAG_COLUMNS.get(f.metric, ()) for f in flags):
                return QBrush(QColor(t.warn))  # the reason stays visible after rejecting
            if not kept or (col in NUMERIC and getattr(s, attr) is None):
                return QBrush(QColor(t.faint))
            return None
        if role == Qt.ItemDataRole.BackgroundRole:
            if kept and any(col in _FLAG_COLUMNS.get(f.metric, ()) for f in flags):
                return QBrush(QColor(t.warn_tint))
            return None
        if role == PATH_ROLE:
            return s.path or s.file
        if role == FLAGGED_ROLE:
            return bool(flags)
        if role == KEEP_ROLE:
            return kept
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role == Qt.ItemDataRole.CheckStateRole and index.column() == KEEP:
            checked = Qt.CheckState(value) == Qt.CheckState.Checked
            self.set_keep([index.row()], checked)
            return True
        return False


class SubsFilter(QSortFilterProxyModel):
    """Sorts by raw values and filters All / Flagged / Rejected."""

    ALL, FLAGGED, REJECTED = range(3)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.mode = self.ALL
        self.setSortRole(SORT_ROLE)

    def set_mode(self, mode: int) -> None:
        if hasattr(self, "beginFilterChange"):  # Qt 6.10+
            self.beginFilterChange()
            self.mode = mode
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
        else:
            self.mode = mode
            self.invalidateRowsFilter()

    def filterAcceptsRow(self, row: int, parent) -> bool:
        if self.mode == self.ALL:
            return True
        idx = self.sourceModel().index(row, 0, parent)
        if self.mode == self.FLAGGED:
            return bool(idx.data(FLAGGED_ROLE))
        return not idx.data(KEEP_ROLE)

    def lessThan(self, left, right) -> bool:
        a, b = left.data(SORT_ROLE), right.data(SORT_ROLE)
        try:
            return a < b
        except TypeError:
            return str(a) < str(b)


# ---------------------------------------------------------------- calibration ----
# column id: (header key, tooltip key, attribute, format)
_CAL_COLUMNS = {
    "keep": ("gui.col.keep", "gui.tip.keep", None, None),
    "status": ("", "gui.tip.status", None, None),
    "file": ("gui.col.file", None, "file", None),
    "exposure": ("gui.col.exposure", "gui.tip.exposure", "exposure_s", "{:g} s"),
    "temp": ("gui.col.temp", "gui.tip.temp", "temperature_c", "{:.1f} °C"),
    "level": ("gui.col.level", "gui.tip.level", "median_adu", "{:,.0f}"),
    "noise": ("gui.col.noise", "gui.tip.cal_noise", "noise_adu", "{:.1f}"),
    "hot": ("gui.col.hot", "gui.tip.hot", "hot_pixels", "{:,.0f}"),
    "glow": ("gui.col.glow", "gui.tip.glow", "glow_adu", "{:.0f}"),
    "banding": ("gui.col.banding", "gui.tip.banding", "banding_adu", "{:.1f}"),
    "level_pct": ("gui.col.level_pct", "gui.tip.level_pct", "level_pct", "{:.0f} %"),
    "vignetting": ("gui.col.vignetting", "gui.tip.vignetting", "vignetting_pct", "{:.0f} %"),
    "dust": ("gui.col.dust", "gui.tip.dust", "dust_spots", "{:.0f}"),
}
CAL_LAYOUT = {
    "flats": ["keep", "status", "file", "exposure", "temp", "level_pct", "vignetting", "dust"],
    "darks": ["keep", "status", "file", "exposure", "temp", "level", "noise", "hot", "glow",
              "banding"],
}
CAL_LAYOUT["bias"] = CAL_LAYOUT["darkflats"] = CAL_LAYOUT["darks"]
CAL_NUMERIC = {"exposure", "temp", "level", "noise", "hot", "glow", "banding", "level_pct",
               "vignetting", "dust"}
_CAL_FLAG_COLUMNS = {"median_adu": ("level",), "noise_adu": ("noise",),
                     "exposure_s": ("exposure",), "temperature_c": ("temp",),
                     "clipped_pct": ("level_pct",), "gain": (), "offset": (), "binning": ()}


class CalModel(QAbstractTableModel):
    """One calibration frame type (bias, darks, flats or flat darks)."""

    keepChanged = Signal()

    def __init__(self, kind: str, parent=None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.columns = CAL_LAYOUT[kind]
        self.rows = []
        self.sub_flags: dict[str, list[SubFlag]] = {}
        self.keep: dict[str, bool] = {}
        self._user_set: set[str] = set()
        self.short: dict[str, str] = {}
        self.theme: Theme = DARK

    def column(self, name: str) -> int:
        return self.columns.index(name)

    def clear(self) -> None:
        self.beginResetModel()
        self.rows, self.sub_flags, self.keep, self._user_set, self.short = [], {}, {}, set(), {}
        self.endResetModel()
        self.keepChanged.emit()

    def add(self, metrics) -> None:
        n = len(self.rows)
        self.beginInsertRows(QModelIndex(), n, n)
        self.rows.append(metrics)
        self.keep.setdefault(metrics.file, True)
        self.endInsertRows()
        self.short = short_names([r.file for r in self.rows])
        self._refresh_all()
        self.keepChanged.emit()

    def apply_group(self, group) -> None:
        self.sub_flags = {}
        for f in group.flags if group else []:
            self.sub_flags.setdefault(f.file, []).append(f)
        for r in self.rows:
            if r.file not in self._user_set:
                self.keep[r.file] = r.file not in self.sub_flags
        self._refresh_all()
        self.keepChanged.emit()

    def apply_suggestion(self) -> None:
        self._user_set.clear()
        for r in self.rows:
            self.keep[r.file] = r.file not in self.sub_flags
        self._refresh_all()
        self.keepChanged.emit()

    def set_all(self, keep: bool) -> None:
        for r in self.rows:
            self.keep[r.file] = keep
            self._user_set.add(r.file)
        self._refresh_all()
        self.keepChanged.emit()

    def set_keep(self, rows: list[int], keep: bool | None = None) -> None:
        if not rows:
            return
        target = keep if keep is not None else not all(self.keep[self.rows[r].file] for r in rows)
        for r in rows:
            self.keep[self.rows[r].file] = target
            self._user_set.add(self.rows[r].file)
        self._refresh_all()
        self.keepChanged.emit()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._refresh_all()

    def kept_paths(self, keep: bool) -> list[str]:
        return [r.path for r in self.rows if self.keep.get(r.file, True) == keep]

    def counts(self) -> tuple[int, int, int]:
        total = len(self.rows)
        return (total, sum(1 for r in self.rows if self.keep.get(r.file, True)),
                sum(1 for r in self.rows if r.file in self.sub_flags))

    def _refresh_all(self) -> None:
        if self.rows:
            self.dataChanged.emit(self.index(0, 0),
                                  self.index(len(self.rows) - 1, len(self.columns) - 1))

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: B008
        return len(self.columns)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation != Qt.Orientation.Horizontal or not 0 <= section < len(self.columns):
            return None
        name = self.columns[section]
        header, tip, _, _ = _CAL_COLUMNS[name]
        if role == Qt.ItemDataRole.DisplayRole:
            return tr(header) if header else ""
        if role == Qt.ItemDataRole.ToolTipRole and tip:
            return tr(tip)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            align = Qt.AlignmentFlag.AlignRight if name in CAL_NUMERIC else \
                Qt.AlignmentFlag.AlignLeft
            return int(align | Qt.AlignmentFlag.AlignVCenter)
        return None

    def flags(self, index):  # noqa: A003 - Qt API name
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if self.columns[index.column()] == "keep":
            base |= Qt.ItemFlag.ItemIsUserCheckable
        return base

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        r = self.rows[index.row()]
        name = self.columns[index.column()]
        _, _, attr, fmt = _CAL_COLUMNS[name]
        kept = self.keep.get(r.file, True)
        flags = self.sub_flags.get(r.file, [])
        t = self.theme
        flagged_here = any(name in _CAL_FLAG_COLUMNS.get(f.metric, ()) for f in flags)
        if role == Qt.ItemDataRole.CheckStateRole and name == "keep":
            return Qt.CheckState.Checked if kept else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.DisplayRole:
            if name == "file":
                label = self.short.get(r.file, r.file)
                return f"★ {label}" if r.is_master else label
            if attr is None:
                return None
            value = getattr(r, attr)
            return "–" if value is None else fmt.format(value)
        if role == SORT_ROLE:
            if name == "keep":
                return int(kept)
            if name == "status":
                return len(flags)
            value = getattr(r, attr) if attr else None
            return value if value is not None else float("inf")
        if role == Qt.ItemDataRole.DecorationRole and name == "status" and flags:
            return icons.icon("flag", t.warn)
        if role == Qt.ItemDataRole.ToolTipRole:
            if flags:
                return "\n".join(f"• {f.reason}" for f in flags)
            if r.is_master:
                return tr("gui.tip.master")
            return r.path
        if role == Qt.ItemDataRole.TextAlignmentRole:
            align = Qt.AlignmentFlag.AlignRight if name in CAL_NUMERIC else \
                Qt.AlignmentFlag.AlignLeft
            return int(align | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            if flagged_here:
                return QBrush(QColor(t.warn))
            if not kept:
                return QBrush(QColor(t.faint))
            return None
        if role == Qt.ItemDataRole.BackgroundRole and kept and flagged_here:
            return QBrush(QColor(t.warn_tint))
        if role == PATH_ROLE:
            return r.path
        if role == FLAGGED_ROLE:
            return bool(flags)
        if role == KEEP_ROLE:
            return kept
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role == Qt.ItemDataRole.CheckStateRole and self.columns[index.column()] == "keep":
            self.set_keep([index.row()], Qt.CheckState(value) == Qt.CheckState.Checked)
            return True
        return False
