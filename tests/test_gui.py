"""Desktop app smoke tests. Runs headless; skipped when PySide6 is not installed."""

import os

import pytest
from synthetic import star_field, write_fits

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QSettings, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from advastro.gui.main_window import MainWindow, find_session_frames  # noqa: E402
from advastro.gui.models import SubsFilter  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    QSettings("Miklosoft", "AdvAstro Analyzer").clear()
    return QApplication.instance() or QApplication([])


def _pump(ms: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


@pytest.fixture
def session(tmp_path):
    lights = tmp_path / "LIGHT"
    lights.mkdir()
    for i in range(6):
        write_fits(lights / f"l_{i}.fits", star_field(shape=(256, 384), n_stars=60, seed=i))
    write_fits(lights / "l_cloudy.fits", star_field(shape=(256, 384), n_stars=12, seed=9))
    (tmp_path / "FLAT").mkdir()
    return tmp_path


def test_light_subfolder_is_found(session):
    frames, folder = find_session_frames(session)
    assert folder.name == "LIGHT" and len(frames) == 7


def test_open_analyze_keep_export(qapp, session, tmp_path):
    w = MainWindow()
    w.show()
    w.open_folder(session)
    for _ in range(600):
        _pump(50)
        if w._worker is None and w.summary is not None:
            break
    assert w.summary is not None, "analysis did not finish"
    total, kept, flagged = w.model.counts()
    assert total == 7 and flagged >= 1 and kept == total - flagged
    assert "l_cloudy.fits" in w.model.sub_flags

    w.proxy.set_mode(SubsFilter.FLAGGED)
    assert w.proxy.rowCount() == flagged
    w.proxy.set_mode(SubsFilter.ALL)

    w.model.set_all(True)
    assert w.model.counts()[1] == 7
    w.model.apply_suggestion()
    assert w.model.counts()[1] == 7 - flagged
    rejected = w.model.kept_paths(False)
    assert any(p.endswith("l_cloudy.fits") for p in rejected)

    w.apply_theme("night")
    w.apply_theme("dark")
    w.close()


def test_rate_window_rates_a_picture_and_exports(qapp, tmp_path):
    import numpy as np
    import tifffile

    from advastro.config import load_config
    from advastro.gui.rate_window import RateWindow
    from advastro.gui.theme import DARK

    rgb = np.stack([star_field(shape=(400, 600), n_stars=300, background=6000.0, noise=300.0,
                               seed=s, peak_range=(5000.0, 50000.0)) / 65535 for s in (1, 1, 1)])
    path = tmp_path / "m42.tif"
    tifffile.imwrite(path, (np.moveaxis(rgb, 0, -1) * 65535).astype(np.uint16))
    cfg = load_config(use_user_config=False)
    cfg.values["compare"]["auto_sky"] = False
    win = RateWindow(cfg, DARK)
    win.show()
    win.open_picture(path)
    for _ in range(300):
        _pump(50)
        if win.rating is not None and win._worker is None:
            break
    assert win.rating is not None
    assert win.preview_image is not None and not win.preview_image.isNull()
    for key in ("stars", "background", "noise", "cast", "clipping", "problems", "none"):
        win.set_overlay(key)
    win.object_edit.setText("M42")
    win._render_compare()
    out = tmp_path / "r.json"
    from advastro.rate.report import to_json

    out.write_text(to_json(win.rating))
    assert '"kind": "rate-my-pic"' in out.read_text()
    win.close()


def test_main_window_opens_rate_window(qapp):
    w = MainWindow()
    w.open_rate()
    assert w.rate_window.isVisible()
    w.rate_window.close()
    w.close()


def test_help_window_opens_at_topics(qapp):
    from advastro.gui import help_window

    w = help_window.show_help("finding.star_rings")
    assert "rings" in w.crumb.text().lower()
    w.show_topic("settings.selection")
    assert w.tree.currentItem().data(0, 256) == "settings.selection"
    w.search.setText("drizzle")
    assert not w.no_hits.isVisible()
    w.search.setText("")
    mw = MainWindow()
    assert mw.help_topic() == "start.first"
    mw.close()
    w.close()
