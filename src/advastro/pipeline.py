"""After the subs are measured: locate the field, identify the target, advise.

Shared by the command line and the desktop app so both give identical advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from advastro.advisor.engine import Advice, advise
from advastro.advisor.facts import build_facts
from advastro.config import Config
from advastro.engine.session import SessionSummary
from advastro.frame import FrameMeta
from advastro.readers import read_frame
from advastro.session_context import SessionContext, build_context
from advastro.sky.identify import TargetReport, identify
from advastro.sky.solve import SkyField, SolveError, detect_astap, locate, solve_astap


@dataclass
class Assessment:
    context: SessionContext
    meta: FrameMeta | None
    sky: SkyField | None
    target: TargetReport
    facts: dict
    advice: Advice
    solve_note: str | None = None   # why a solve was skipped or failed


def best_sub_path(summary: SessionSummary, keep: dict[str, bool]) -> str | None:
    kept = [s for s in summary.subs if keep.get(s.file, True) and s.path]
    best = min((s for s in kept if s.fwhm_px), key=lambda s: s.fwhm_px, default=None)
    return (best or (kept[0] if kept else None)).path if (best or kept) else None


def assess(summary: SessionSummary, keep: dict[str, bool], frames_dir: Path, cfg: Config,
           scale: float | None, solve: bool | None = None, calibration=None) -> Assessment:
    """solve: True = run ASTAP if needed, False = never, None = follow the config."""
    path = best_sub_path(summary, keep)
    frame = read_frame(path) if path else None
    meta = frame.meta if frame else None
    context = build_context(frames_dir, meta.object_name if meta else None)

    sky = locate(frame, scale) if frame else None
    note = None
    want_solve = cfg.get("solver", "auto_solve", True) if solve is None else solve
    if frame is not None and (sky is None or sky.level != "solved") and want_solve:
        install = detect_astap(cfg.get("solver", "astap_path", ""),
                               cfg.get("solver", "database_path", ""))
        if install.ready:
            try:
                sky = solve_astap(frame, install, scale_hint=scale,
                                  radius_deg=cfg.get("solver", "search_radius_deg", 30.0),
                                  timeout_s=cfg.get("solver", "timeout_s", 90.0))
            except SolveError as exc:
                note = str(exc)
        elif install.executable is None:
            note = "astap_missing"
        else:
            note = "astap_no_database"
    elif sky is None and frame is not None:
        note = "no_position"

    extra = []
    if context.mksession:
        from advastro.sky.catalog import SkyObject

        for t in context.mksession.targets:
            if t.ra_deg is not None and t.dec_deg is not None:
                extra.append(SkyObject(id=t.id, type="", ra=t.ra_deg, dec=t.dec_deg,
                                       constellation="", major_arcmin=t.size_arcmin,
                                       minor_arcmin=None, position_angle=None, magnitude=None,
                                       aliases=t.aliases, names=[t.name] if t.name else []))
    # Prefer the catalog's richer entry when the user's target is a catalog object.
    target = identify(sky, context.name_hints, extra=None)
    if target.target is None and extra:
        target = identify(sky, context.name_hints, extra=extra)

    profile = cfg.section("profile")
    facts = build_facts(summary, keep, meta, context, target, profile, scale, calibration)
    tools = [t.lower() for t in profile.get("software", []) if t.lower() in ("pixinsight", "siril")]
    return Assessment(context, meta, sky, target, facts, advise(facts, tools or None), note)
