"""Background work, so the window never freezes.

AnalysisWorker runs the engine in a QThread (which itself fans out to worker
processes) and streams each sub back as it finishes. PreviewTask builds a
stretched preview on the thread pool.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QImage

from advastro.config import Config, measure_options, session_thresholds, worker_count
from advastro.display import preview_rgb
from advastro.engine.session import analyze_paths, resolve_pixel_scale, summarize
from advastro.frame import FrameMeta
from advastro.integrations.miklosoft import find_mksession
from advastro.readers import read_frame


class AnalysisWorker(QObject):
    progress = Signal(int, int, str)
    result = Signal(object)                      # SubMetrics
    finished = Signal(object, object, str, float)  # summary, scale, scale source, seconds
    failed = Signal(str)

    def __init__(self, folder: Path, paths: list[Path], cfg: Config) -> None:
        super().__init__()
        self.folder, self.paths, self.cfg = folder, paths, cfg
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    @property
    def stopped(self) -> bool:
        return self._stop

    def run(self) -> None:
        started = time.monotonic()
        try:
            subs, errors = analyze_paths(
                self.paths, measure_options(self.cfg), jobs=worker_count(self.cfg),
                progress=self.progress.emit, on_result=self.result.emit,
                should_stop=lambda: self._stop,
            )
            summary = summarize(subs, session_thresholds(self.cfg), errors)
            scale, source = resolve_pixel_scale(
                summary, self.cfg.section("equipment"), find_mksession(self.folder))
            self.finished.emit(summary, scale, source, time.monotonic() - started)
        except Exception as exc:  # report, never crash the window
            self.failed.emit(str(exc))


class PreviewSignals(QObject):
    ready = Signal(str, QImage, object, object)   # path, image, FrameMeta, data shape
    failed = Signal(str, str)


class PreviewTask(QRunnable):
    def __init__(self, path: str, signals: PreviewSignals) -> None:
        super().__init__()
        self.path, self.signals = path, signals
        self.setAutoDelete(True)

    def run(self) -> None:
        try:
            frame = read_frame(self.path)
            rgb = preview_rgb(frame)
            h, w, _ = rgb.shape
            image = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
            meta: FrameMeta = frame.meta
            meta.raw_header = {}  # not needed by the UI; keeps memory low
            shape = tuple(int(x) for x in np.shape(frame.data))
            self.signals.ready.emit(self.path, image, meta, shape)
        except Exception as exc:
            self.signals.failed.emit(self.path, str(exc))


class AssessWorker(QObject):
    """Locate, plate solve (optionally), identify and advise, off the UI thread."""

    done = Signal(object)    # Assessment
    failed = Signal(str)

    def __init__(self, summary, keep: dict, folder: Path, cfg: Config, scale,
                 solve: bool | None, calibration=None) -> None:
        super().__init__()
        self.args = (summary, dict(keep), folder, cfg, scale, solve, calibration)

    def run(self) -> None:
        from advastro.pipeline import assess

        try:
            self.done.emit(assess(*self.args))
        except Exception as exc:
            self.failed.emit(str(exc))


class CalibrationWorker(QObject):
    """Measure calibration frames and check them against each other and the lights."""

    progress = Signal(int, int, str)
    result = Signal(object)                 # CalMetrics
    finished = Signal(object, float)        # CalibrationSummary, seconds
    failed = Signal(str)

    def __init__(self, files: dict, cfg: Config, lights_path: str | None = None) -> None:
        super().__init__()
        self.files, self.cfg, self.lights_path = files, cfg, lights_path
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        from advastro.engine.calibration import analyze_calibration, summarize_calibration

        started = time.monotonic()
        try:
            metrics, errors = analyze_calibration(
                self.files, jobs=worker_count(self.cfg), progress=self.progress.emit,
                on_result=self.result.emit, should_stop=lambda: self._stop)
            meta = when = None
            if self.lights_path:
                from advastro.readers import read_frame

                try:
                    meta = read_frame(self.lights_path).meta
                    when = meta.date_obs.isoformat() if meta.date_obs else None
                except Exception:
                    meta = None
            summary = summarize_calibration(metrics, meta, when, errors)
            self.finished.emit(summary, time.monotonic() - started)
        except Exception as exc:
            self.failed.emit(str(exc))
