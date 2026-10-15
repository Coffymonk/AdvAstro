"""Desktop app entry point: `advastro-gui` (or `python -m advastro.gui`)."""

from __future__ import annotations

import multiprocessing
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()  # bundled executables start worker processes
    argv = list(sys.argv if argv is None else argv)
    smoke_test = "--smoke-test" in argv
    if smoke_test:  # used by the build scripts: open the window off-screen, then quit
        import os

        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from advastro import APP_NAME, __version__
    from advastro.config import ConfigError, load_config
    from advastro.gui.main_window import MainWindow
    from advastro.i18n import set_language

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Miklosoft")
    app.setStyle("Fusion")  # same look on Windows, macOS and Linux; themed by our style sheet
    font = app.font()
    if sys.platform == "win32":
        font = QFont("Segoe UI Variable Text")
        if not font.exactMatch():
            font = QFont("Segoe UI")
    font.setPointSizeF(10)
    app.setFont(font)

    try:
        set_language(str(load_config().get("general", "language", "en")))
    except ConfigError:
        set_language("en")

    window = MainWindow()
    window.show()
    if smoke_test:
        from PySide6.QtCore import QTimer

        from advastro import help as manual
        from advastro.gui.help_window import show_help
        from advastro.rate.judge import _load_tips

        # Bundled data must be readable in the packaged app: the manual and the tips.
        for lang in ("en", "sv"):
            if len(manual.chapters(lang)) < 10:
                print(f"smoke test: manual '{lang}' incomplete", file=sys.stderr)
                return 1
        if not _load_tips():
            print("smoke test: tips.toml missing", file=sys.stderr)
            return 1
        show_help("rate.verdict", window)
        QTimer.singleShot(500, app.quit)
        return app.exec()
    folder = next((Path(a) for a in argv[1:] if Path(a).is_dir()), None)
    if folder:
        window.open_folder(folder)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
