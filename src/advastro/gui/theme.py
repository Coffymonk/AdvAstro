"""Colour themes and the application style sheet.

Two themes: a calm dark theme (default) and a red night mode that keeps
dark adaptation at the telescope. Colours are defined once here; widgets ask
for them by role, so switching theme is a single call.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str          # window background
    surface: str     # panels
    raised: str      # cards, inputs, hover
    border: str
    text: str
    muted: str
    faint: str       # disabled text and icons
    accent: str
    accent_text: str
    good: str
    warn: str
    bad: str
    warn_tint: str   # row/cell tint for flagged values
    selection: str


DARK = Theme(
    name="dark",
    bg="#0f1216", surface="#151a20", raised="#1d232b", border="#262d37",
    text="#e4e8ee", muted="#8a94a3", faint="#4d5663",
    accent="#6aa8ff", accent_text="#0b1018",
    good="#5cc98a", warn="#f2b84b", bad="#ef6b6b",
    warn_tint="#33291a", selection="#1f3350",
)

NIGHT = Theme(
    name="night",
    bg="#0a0000", surface="#120202", raised="#1c0505", border="#2e0a0a",
    text="#e04848", muted="#9c2e2e", faint="#5a1a1a",
    accent="#ff4a4a", accent_text="#140000",
    good="#c84040", warn="#ff6a3a", bad="#ff3030",
    warn_tint="#2a0a06", selection="#3a0c0c",
)

THEMES = {t.name: t for t in (DARK, NIGHT)}


def _check_image(color: str) -> str:
    """Write a small check-mark SVG for the table check boxes; returns a QSS-safe path."""
    folder = Path(tempfile.gettempdir()) / "advastro-ui"
    folder.mkdir(exist_ok=True)
    path = folder / f"check-{color.lstrip('#')}.svg"
    if not path.exists():
        path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" '
            f'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M4 8.4l2.6 2.6L12 5.6"/></svg>', encoding="utf-8")
    return path.as_posix()


def _chevron(color: str, up: bool) -> str:
    folder = Path(tempfile.gettempdir()) / "advastro-ui"
    folder.mkdir(exist_ok=True)
    path = folder / f"chevron-{'up' if up else 'down'}-{color.lstrip('#')}.svg"
    if not path.exists():
        d = "M4 10l4-4 4 4" if up else "M4 6l4 4 4-4"
        path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" '
            f'stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
            f'stroke-linejoin="round"><path d="{d}"/></svg>', encoding="utf-8")
    return path.as_posix()


def stylesheet(t: Theme) -> str:
    check = _check_image(t.accent)
    down, up = _chevron(t.muted, False), _chevron(t.muted, True)
    return f"""
    * {{ outline: 0; }}
    QWidget {{ background: {t.bg}; color: {t.text}; font-size: 10pt; }}
    QMainWindow::separator {{ background: {t.border}; width: 1px; height: 1px; }}
    QToolTip {{ background: {t.raised}; color: {t.text}; border: 1px solid {t.border};
                padding: 5px 8px; border-radius: 6px; }}

    /* Toolbar */
    QToolBar {{ background: {t.surface}; border: 0; border-bottom: 1px solid {t.border};
                padding: 6px 10px; spacing: 2px; }}
    QToolBar QWidget#spacer {{ background: transparent; }}
    QToolBar::separator {{ background: {t.border}; width: 1px; margin: 6px 8px; }}
    QToolButton {{ background: transparent; color: {t.text}; border: 0; border-radius: 7px;
                   padding: 6px 10px; }}
    QToolButton:hover {{ background: {t.raised}; }}
    QToolButton:pressed, QToolButton:checked {{ background: {t.border}; }}
    QToolButton:disabled {{ color: {t.faint}; }}
    QToolButton::menu-indicator {{ image: none; width: 0; }}
    QToolButton#primary {{ background: {t.accent}; color: {t.accent_text}; font-weight: 600; }}
    QToolButton#primary:hover {{ background: {t.text}; }}
    QToolButton#primary:disabled {{ background: {t.raised}; color: {t.faint}; }}

    /* Buttons */
    QPushButton {{ background: {t.raised}; color: {t.text}; border: 1px solid {t.border};
                   border-radius: 8px; padding: 7px 14px; }}
    QPushButton:hover {{ border-color: {t.muted}; }}
    QPushButton#primary {{ background: {t.accent}; color: {t.accent_text}; border: 0;
                           font-weight: 600; padding: 9px 18px; }}
    QPushButton#primary:hover {{ background: {t.text}; }}
    QPushButton#link {{ background: transparent; border: 0; color: {t.muted};
                        padding: 4px 6px; text-align: left; }}
    QPushButton#link:hover {{ color: {t.accent}; }}

    /* Menus */
    QMenu {{ background: {t.raised}; border: 1px solid {t.border}; border-radius: 8px;
             padding: 5px; }}
    QMenu::item {{ padding: 7px 22px 7px 10px; border-radius: 5px; }}
    QMenu::item:selected {{ background: {t.selection}; }}
    QMenu::icon {{ padding-left: 8px; }}
    QMenu::separator {{ height: 1px; background: {t.border}; margin: 4px 6px; }}

    /* Table */
    QTableView {{ background: {t.surface}; alternate-background-color: {t.surface};
                  border: 0; gridline-color: transparent;
                  selection-background-color: {t.selection}; selection-color: {t.text}; }}
    QTableView::item {{ padding: 0 8px; border-bottom: 1px solid {t.bg}; }}
    QHeaderView {{ background: {t.surface}; }}
    QHeaderView::section {{ background: {t.surface}; color: {t.muted}; border: 0;
                            border-bottom: 1px solid {t.border}; padding: 8px 8px;
                            font-size: 9pt; font-weight: 600; }}
    QHeaderView::section:hover {{ color: {t.text}; }}
    QHeaderView::down-arrow, QHeaderView::up-arrow {{ width: 8px; height: 8px;
                                                      subcontrol-position: center right; }}
    QTableView QTableCornerButton::section {{ background: {t.surface}; border: 0; }}
    QTableView::indicator {{ width: 16px; height: 16px; border-radius: 5px;
                             border: 1.5px solid {t.faint}; background: transparent; }}
    QTableView::indicator:hover {{ border-color: {t.muted}; }}
    QTableView::indicator:checked {{ border-color: {t.accent}; image: url("{check}"); }}

    /* Scroll bars */
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
    QScrollBar::handle {{ background: {t.border}; border-radius: 3px; min-height: 24px;
                          min-width: 24px; }}
    QScrollBar::handle:hover {{ background: {t.faint}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    /* Panels and cards */
    QFrame#panel {{ background: {t.surface}; border: 0; }}
    QFrame#card {{ background: {t.raised}; border-radius: 10px; }}
    QLabel {{ background: transparent; }}
    QLabel#title {{ font-size: 11pt; font-weight: 600; }}
    QLabel#section {{ color: {t.muted}; font-size: 8.5pt; font-weight: 600;
                      letter-spacing: 0.6px; }}
    QLabel#muted {{ color: {t.muted}; }}
    QLabel#statValue {{ font-size: 15pt; font-weight: 600; }}
    QLabel#statLabel {{ color: {t.muted}; font-size: 8.5pt; }}
    QLabel#hero {{ font-size: 18pt; font-weight: 600; }}

    /* Flags list */
    QListWidget {{ background: transparent; border: 0; }}
    QListWidget::item {{ padding: 7px 6px; border-radius: 6px; }}
    QListWidget::item:hover {{ background: {t.raised}; }}
    QListWidget::item:selected {{ background: {t.selection}; color: {t.text}; }}

    /* Status bar and progress */
    QStatusBar {{ background: {t.surface}; color: {t.muted}; border-top: 1px solid {t.border}; }}
    QStatusBar::item {{ border: 0; }}
    QProgressBar {{ background: {t.raised}; border: 0; border-radius: 3px; max-height: 6px;
                    min-width: 180px; }}
    QProgressBar::chunk {{ background: {t.accent}; border-radius: 3px; }}

    QSplitter::handle {{ background: {t.border}; }}
    QGraphicsView {{ background: {t.bg}; border: 0; }}

    /* Tabs (Session / Target / Workflow) */
    QTabWidget::pane {{ border: 0; background: {t.surface}; }}
    QTabBar {{ background: {t.surface}; }}
    QTabBar::tab {{ background: transparent; color: {t.muted}; padding: 9px 16px;
                    border: 0; border-bottom: 2px solid transparent; font-weight: 600; }}
    QTabBar::tab:hover {{ color: {t.text}; }}
    QTabBar::tab:selected {{ color: {t.text}; border-bottom: 2px solid {t.accent}; }}
    QScrollArea {{ background: {t.surface}; border: 0; }}
    QScrollArea > QWidget > QWidget {{ background: {t.surface}; }}

    /* Workflow steps */
    QFrame#step {{ background: transparent; border-bottom: 1px solid {t.border}; }}
    QLabel#stepNumber {{ background: {t.raised}; color: {t.text}; border-radius: 12px;
                         font-size: 9pt; font-weight: 600; }}

    /* Form controls */
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {t.raised}; color: {t.text}; border: 1px solid {t.border};
        border-radius: 7px; padding: 6px 8px; min-height: 18px;
        selection-background-color: {t.selection}; }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {t.accent}; }}
    QComboBox::drop-down {{ border: 0; width: 26px; }}
    QComboBox::down-arrow {{ image: url("{down}"); width: 12px; height: 12px; }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{up}"); width: 10px;
                                                    height: 10px; }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{down}"); width: 10px;
                                                        height: 10px; }}
    QComboBox QAbstractItemView {{ background: {t.raised}; border: 1px solid {t.border};
        selection-background-color: {t.selection}; outline: 0; padding: 4px; }}
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 18px; border: 0;
                                                              background: transparent; }}
    QCheckBox {{ spacing: 9px; padding: 3px 0; background: transparent; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 5px;
                            border: 1.5px solid {t.faint}; background: transparent; }}
    QCheckBox::indicator:hover {{ border-color: {t.muted}; }}
    QCheckBox::indicator:checked {{ border-color: {t.accent}; image: url("{check}"); }}

    /* Settings window */
    QDialog {{ background: {t.bg}; }}
    QListWidget#nav {{ background: {t.surface}; border: 0; border-right: 1px solid {t.border};
                       padding: 14px 8px; }}
    QListWidget#nav::item {{ padding: 9px 10px; border-radius: 7px; margin: 1px 0; }}
    QListWidget#nav::item:selected {{ background: {t.raised}; color: {t.text}; }}
    """
