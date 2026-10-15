"""Render the app icon at every size and pack the Windows .ico and macOS .icns.

    python build/icons/make_icons.py

Sources: src/advastro.svg (64 px and up) and src/advastro-small.svg (16–48 px, a
simplified drawing with thicker lines so it stays crisp). Needs PySide6 and Pillow.
"""

import os
import shutil
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image  # noqa: E402
from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

HERE = Path(__file__).parent
ASSETS = HERE.parents[1] / "src" / "advastro" / "gui" / "assets"
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256, 512, 1024)
SMALL_MAX = 48


def render() -> None:
    big = QSvgRenderer(str(HERE / "src" / "advastro.svg"))
    small = QSvgRenderer(str(HERE / "src" / "advastro-small.svg"))
    out = HERE / "png"
    out.mkdir(exist_ok=True)
    for s in SIZES:
        img = QImage(s, s, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        (small if s <= SMALL_MAX else big).render(p, QRectF(0, 0, s, s))
        p.end()
        img.save(str(out / f"advastro-{s}.png"))


def pack() -> None:
    png = HERE / "png"
    load = lambda s: Image.open(png / f"advastro-{s}.png").convert("RGBA")  # noqa: E731
    ico = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    load(256).save(HERE / "advastro.ico", format="ICO", sizes=[(s, s) for s in ico],
                   append_images=[load(s) for s in ico[:-1]])
    load(1024).save(HERE / "advastro.icns", format="ICNS",
                    append_images=[load(s) for s in (16, 32, 64, 128, 256, 512)])
    shutil.copy(png / "advastro-256.png", HERE / "advastro-256.png")
    shutil.copy(HERE / "src" / "advastro.svg", HERE / "advastro.svg")
    ASSETS.mkdir(exist_ok=True)
    for s in (16, 24, 32, 48, 64, 128, 256, 512):
        shutil.copy(png / f"advastro-{s}.png", ASSETS / f"app-{s}.png")


if __name__ == "__main__":
    app = QGuiApplication([])
    render()
    pack()
    print("Icons written to", HERE)
