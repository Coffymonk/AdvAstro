"""Report renderers shared by the command line and the desktop app."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict

from advastro import __version__
from advastro.engine.session import SessionSummary


def to_json(summary: SessionSummary, scale: float | None, scale_source: str,
            keep: dict[str, bool] | None = None) -> str:
    subs = []
    for s in summary.subs:
        d = s.to_dict()
        d.pop("ref_stars", None)
        if keep is not None:
            d["keep"] = keep.get(s.file, True)
        subs.append(d)
    return json.dumps({
        "app": "advastro-analyzer",
        "version": __version__,
        "pixel_scale_arcsec": scale,
        "pixel_scale_source": scale_source,
        "sampling": summary.sampling,
        "dithered": summary.dithered,
        "dither_px": summary.dither_px,
        "drift_px": summary.drift_px,
        "medians": summary.medians,
        "subs": subs,
        "flags": [asdict(f) for f in summary.flags],
        "errors": summary.errors,
    }, indent=2, ensure_ascii=False)


def to_csv(summary: SessionSummary, keep: dict[str, bool] | None = None) -> str:
    out = io.StringIO()
    flagged = summary.flagged_files()
    skip = {"warnings", "path", "ref_stars", "offset_px"}
    fields = [k for k in summary.subs[0].to_dict() if k not in skip] if summary.subs else []
    extra = ["flagged"] + (["keep"] if keep is not None else [])
    writer = csv.writer(out)
    writer.writerow([*fields, *extra])
    for s in summary.subs:
        d = s.to_dict()
        row = [d[k] for k in fields] + [s.file in flagged]
        if keep is not None:
            row.append(keep.get(s.file, True))
        writer.writerow(row)
    return out.getvalue()


def file_list(paths: list[str]) -> str:
    """One full path per line: loads into PixInsight, Siril or a script."""
    return "\n".join(paths) + ("\n" if paths else "")


_CAL_SKIP = {"path", "channel_levels"}


def calibration_csv(rows: list, keep: dict[str, bool] | None = None) -> str:
    """One calibration group (rows of CalMetrics) as CSV."""
    out = io.StringIO()
    writer = csv.writer(out)
    fields = [k for k in rows[0].to_dict() if k not in _CAL_SKIP] if rows else []
    writer.writerow([*fields, *(["keep"] if keep is not None else [])])
    for r in rows:
        d = r.to_dict()
        writer.writerow([d[k] for k in fields] +
                        ([keep.get(r.file, True)] if keep is not None else []))
    return out.getvalue()


def calibration_json(summary, keep: dict[str, bool] | None = None) -> str:
    """The whole calibration check: groups, frames, flags and notes."""
    groups = {}
    for kind, g in (summary.groups.items() if summary else []):
        frames = []
        for r in [*g.frames, *g.masters]:
            d = r.to_dict()
            if keep is not None and r.kind == kind:
                d["keep"] = keep.get(r.file, True)
            frames.append(d)
        groups[kind] = {"medians": g.medians, "frames": frames,
                        "flags": [asdict(f) for f in g.flags]}
    return json.dumps({
        "app": "advastro-analyzer",
        "version": __version__,
        "calibration": groups,
        "notes": [asdict(n) for n in summary.notes] if summary else [],
        "errors": summary.errors if summary else [],
    }, indent=2, ensure_ascii=False, default=str)
