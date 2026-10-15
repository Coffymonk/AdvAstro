"""AdvAstro's own line icons, drawn as SVG and tinted to the active theme.

All icons share one grid (24 x 24, 1.75 stroke, round caps) so they read as a
family. Each is a set of SVG elements; colour is filled in at render time.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_PATHS = {
    # Open a folder of subs
    "folder": '<path d="M3 7.5a2 2 0 0 1 2-2h3.6l2 2H19a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H5'
              'a2 2 0 0 1-2-2z"/>'
              '<path d="M3 10h18"/>',
    # Analyze again
    "analyze": '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/>'
               '<path d="M10.5 7.5v6M7.5 10.5h6"/>',
    # Stop a running analysis
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    # Export (arrow out of a tray)
    "export": '<path d="M12 4v11"/><path d="M7.5 8.5L12 4l4.5 4.5"/>'
              '<path d="M4 14v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>',
    # Keep / reject
    "keep": '<circle cx="12" cy="12" r="8.5"/><path d="M8 12.3l2.7 2.7L16 9.6"/>',
    "reject": '<circle cx="12" cy="12" r="8.5"/><path d="M9 9l6 6M15 9l-6 6"/>',
    # Suggested selection (magic wand)
    "suggest": '<path d="M5 19L15.5 8.5"/><path d="M14 7l3 3"/>'
               '<path d="M18 3v3M16.5 4.5h3M20 10v2M19 11h2M10 3v2M9 4h2"/>',
    # Warning (flagged sub)
    "flag": '<path d="M12 4l9 16H3z"/><path d="M12 10v4"/><path d="M12 17.2v.3"/>',
    # Help (question mark in a circle)
    "help": '<circle cx="12" cy="12" r="8.5"/><path d="M9.6 9.6a2.5 2.5 0 1 1 3.4 2.3'
            'c-.6.3-1 .8-1 1.5v.6"/><path d="M12 16.8v.3"/>',
    # Rate my pic (medal with ribbon)
    "rate": '<circle cx="12" cy="9.5" r="5.5"/><path d="M12 7.2l.8 1.6 1.7.2-1.2 1.2.3 1.7'
            '-1.6-.8-1.6.8.3-1.7-1.2-1.2 1.7-.2z"/><path d="M8.7 14l-1.7 6.5 5-2.5 5 2.5'
            '-1.7-6.5"/>',
    # Star (FWHM, stars)
    "star": '<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8'
            '-4.3-4.1 5.9-.8z"/>',
    # Fit image to window
    "fit": '<path d="M4 9V5a1 1 0 0 1 1-1h4M15 4h4a1 1 0 0 1 1 1v4M20 15v4a1 1 0 0 1-1 1h-4'
           'M9 20H5a1 1 0 0 1-1-1v-4"/>',
    # 1:1 pixels
    "actual": '<rect x="4" y="4" width="16" height="16" rx="2"/>'
              '<path d="M9 9.5l1.5-1v7M14 9.5l1.5-1v7"/>',
    # Night (red) mode
    "night": '<path d="M19.5 14.5A8 8 0 0 1 9.5 4.5a8 8 0 1 0 10 10z"/>',
    # Information / summary
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5"/><path d="M12 7.8v.3"/>',
    # Image / preview
    "image": '<rect x="3.5" y="5" width="17" height="14" rx="2"/>'
             '<path d="M3.5 16l5-4.5 4 3.5 2.5-2 5.5 4.5"/><circle cx="15.5" cy="9.5" r="1.4"/>',
    # Settings
    "settings": '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/>'
                '<circle cx="9" cy="17" r="2"/>',
    # File list (export list)
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><path d="M4.5 6h.5M4.5 12h.5M4.5 18h.5"/>',
    # Table / spreadsheet
    "table": '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/>'
             '<path d="M3.5 9.5h17M3.5 14.5h17M9.5 9.5v10"/>',
    # Code / JSON
    "code": '<path d="M8.5 7L4 12l4.5 5M15.5 7L20 12l-4.5 5"/>',
    # Plate solve (reticle on a star)
    "solve": '<circle cx="12" cy="12" r="7.5"/><path d="M12 2.5v4M12 17.5v4M2.5 12h4M17.5 12h4"/>'
             '<circle cx="12" cy="12" r="1.6"/>',
    # Light bulb (insight)
    "insight": '<path d="M9 17.5h6M10 20.5h4"/><path d="M8.2 14.2A6 6 0 1 1 15.8 14.2'
               'c-.8.8-1.3 1.7-1.3 2.8h-5c0-1.1-.5-2-1.3-2.8z"/>',
    # Copy
    "copy": '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/>'
            '<path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8'
            'A1.5 1.5 0 0 0 6 15.5h2.5"/>',
    # Object families
    "galaxy": '<ellipse cx="12" cy="12" rx="9" ry="4" transform="rotate(-25 12 12)"/>'
              '<path d="M7.5 9.5c2.5-2.5 7-2.6 8.6.2M16.5 14.5c-2.5 2.5-7 2.6-8.6-.2"/>'
              '<circle cx="12" cy="12" r="1.4"/>',
    "nebula": '<path d="M6.5 17.5a4 4 0 0 1-.6-7.9 5.5 5.5 0 0 1 10.6-1.4 4.6 4.6 0 0 1 '
              '1.2 9.3z"/><path d="M9 13.5c1.5-1 3.5-1 5 .5"/>',
    "cluster": '<circle cx="12" cy="12" r="1.3"/><circle cx="7.5" cy="9" r="1"/>'
               '<circle cx="16" cy="8" r="1"/><circle cx="8.5" cy="16" r="1"/>'
               '<circle cx="15.5" cy="15.5" r="1"/><circle cx="12" cy="5" r=".8"/>'
               '<circle cx="19" cy="12.5" r=".8"/><circle cx="4.8" cy="13" r=".8"/>',
    "planetary": '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3.5"/>'
                 '<circle cx="12" cy="12" r=".6"/>',
    "unknown": '<circle cx="12" cy="12" r="8.5"/><path d="M9.6 9.5a2.5 2.5 0 0 1 4.8.8'
               'c0 1.7-2.4 2-2.4 3.7"/><path d="M12 16.8v.3"/>',
}

FAMILY_ICON = {
    "galaxy": "galaxy", "emission": "nebula", "reflection": "nebula",
    "planetary": "planetary", "cluster": "cluster", "globular": "cluster",
    "unknown": "unknown",
}

_ASSETS = Path(__file__).with_name("assets")


def _svg(name: str, color: str) -> bytes:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">'
        f'{_PATHS[name]}</svg>'
    ).encode()


def _render(svg: bytes, size: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pm


@cache
def icon(name: str, color: str, disabled_color: str | None = None) -> QIcon:
    """A crisp icon at common sizes (and high-DPI) in the given colour."""
    ic = QIcon()
    for size in (16, 20, 24, 32, 40, 48):
        ic.addPixmap(_render(_svg(name, color), size), QIcon.Mode.Normal)
        if disabled_color:
            ic.addPixmap(_render(_svg(name, disabled_color), size), QIcon.Mode.Disabled)
    return ic


@cache
def app_icon() -> QIcon:
    """The application icon; small sizes are a simplified drawing that stays crisp."""
    ic = QIcon()
    for path in sorted(_ASSETS.glob("app-*.png")):
        ic.addFile(str(path))
    return ic


def names() -> list[str]:
    return sorted(_PATHS)
