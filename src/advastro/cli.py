"""Command-line interface for batch analysis.

    advastro analyze <folder> [--format table|json|csv] [--output FILE]
    advastro config [--show]

The CLI uses the same engine and configuration as the GUI.
"""

from __future__ import annotations

import argparse
import io
import multiprocessing
import sys
from pathlib import Path

from advastro import APP_NAME, __version__, report
from advastro.config import (
    ConfigError,
    load_config,
    measure_options,
    session_thresholds,
    to_toml,
    user_config_path,
    worker_count,
)
from advastro.engine.session import (
    SessionSummary,
    analyze_paths,
    resolve_pixel_scale,
    summarize,
)
from advastro.i18n import set_language, tr
from advastro.integrations.miklosoft import find_mksession, load_mksession
from advastro.readers import find_frames


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="advastro", description=f"{APP_NAME} {__version__}")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def config_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--config", action="append", type=Path, default=[],
                        help="extra TOML config file (can be repeated; last wins)")
        sp.add_argument("--set", action="append", default=[], metavar="SECTION.KEY=VALUE",
                        help="override one setting, e.g. --set reject.fwhm_sigma=2.5")
        sp.add_argument("--no-user-config", action="store_true",
                        help=f"ignore {user_config_path()}")
        sp.add_argument("--lang", help="UI language code, e.g. en or sv")

    a = sub.add_parser("analyze", help="analyze a folder of subs")
    a.add_argument("folder", type=Path)
    a.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    a.add_argument("-f", "--format", choices=["table", "json", "csv"], default=None)
    a.add_argument("-o", "--output", type=Path, help="write the report to a file")
    a.add_argument("-j", "--jobs", type=int, help="parallel workers (default: config)")
    a.add_argument("--session", type=Path, help=".mksession file (auto-detected if omitted)")
    a.add_argument("-q", "--quiet", action="store_true", help="no progress output")
    a.add_argument("--advise", action="store_true",
                   help="identify the target and print a processing workflow")
    a.add_argument("--tool", choices=["pixinsight", "siril"], default="pixinsight",
                   help="tool for the workflow (default: pixinsight)")
    solve = a.add_mutually_exclusive_group()
    solve.add_argument("--solve", dest="solve", action="store_true", default=None,
                       help="plate solve with ASTAP if the files carry no solution")
    solve.add_argument("--no-solve", dest="solve", action="store_false",
                       help="never run the plate solver")
    a.add_argument("--workflow", type=Path, help="also save the workflow as Markdown")
    a.add_argument("--no-calibration", action="store_true",
                   help="do not analyze calibration frames found with the lights")
    config_args(a)

    s = sub.add_parser("solve", help="plate solve one image and identify what it shows")
    s.add_argument("file", type=Path)
    config_args(s)

    r = sub.add_parser("rate", help="rate a finished picture (Rate my pic)")
    r.add_argument("file", type=Path, help="FITS, XISF, TIFF, PNG, JPEG or WebP")
    r.add_argument("--object", help="object name, helps plate solving (e.g. M31)")
    r.add_argument("--sky", action="store_true",
                   help="also plate solve, measure depth against Gaia and check star colours")
    r.add_argument("-f", "--format", choices=["table", "markdown", "json"], default="table")
    r.add_argument("-o", "--output", type=Path, help="write the report to a file")
    r.add_argument("--pdf", type=Path, help="also write a PDF report")
    r.add_argument("--tool", choices=["pixinsight", "siril"],
                   help="only show steps for this program")
    r.add_argument("--skill", choices=["beginner", "intermediate", "advanced"],
                   help="judge at this level (default: from your settings)")
    r.add_argument("--type", dest="object_type", default="auto",
                   choices=["auto", "galaxy", "emission", "reflection", "planetary", "dark",
                            "cluster", "globular", "milkyway"],
                   help="object type (default: from the name or the plate solve)")
    r.add_argument("--starless", choices=["auto", "yes", "no"], default="auto",
                   help="is the picture starless? (default: detect)")
    r.add_argument("--workflow", action="store_true",
                   help="print the processing workflow for the object type instead")
    config_args(r)

    d = sub.add_parser("astap", help="show where ASTAP and its star databases were found")
    config_args(d)

    c = sub.add_parser("config", help="show the merged configuration")
    c.add_argument("folder", type=Path, nargs="?", help="session folder (for advastro.toml)")
    config_args(c)
    return p


def _fmt(value, spec: str, unit: str = "") -> str:
    return "-" if value is None else f"{value:{spec}}{unit}"


def _render_table(summary: SessionSummary, scale_note: str) -> str:
    flagged = summary.flagged_files()
    out = io.StringIO()
    col = {k: tr(f"cli.col.{k}") for k in ("file", "ecc", "stars", "bkg", "noise")}
    header = f"{'':2}{col['file']:<34}{'FWHM px':>9}{'FWHM ″':>8}{col['ecc']:>6}{col['stars']:>7}" \
             f"{col['bkg']:>10}{col['noise']:>8}{'SNR':>7}"
    out.write(header + "\n" + "-" * len(header) + "\n")
    for s in summary.subs:
        mark = "! " if s.file in flagged else "  "
        name = s.file if len(s.file) <= 33 else "…" + s.file[-32:]
        out.write(f"{mark}{name:<34}{_fmt(s.fwhm_px, '.2f'):>9}{_fmt(s.fwhm_arcsec, '.2f'):>8}"
                  f"{_fmt(s.eccentricity, '.2f'):>6}{s.star_count:>7}"
                  f"{s.background_adu:>10.1f}{s.noise_adu:>8.2f}"
                  f"{_fmt(s.snr_estimate, '.0f'):>7}\n")

    m = summary.medians
    out.write(f"\n{tr('cli.summary_title')}\n")
    rows = [
        (tr("cli.subs"), str(len(summary.subs))),
        (tr("cli.pixel_scale"), scale_note),
        (tr("cli.median_fwhm"), f"{_fmt(m.get('fwhm_px'), '.2f', ' px')}"
                                f"  ({_fmt(m.get('fwhm_arcsec'), '.2f', '″')})"),
        (tr("cli.median_ecc"), _fmt(m.get("eccentricity"), ".2f")),
        (tr("cli.median_stars"), _fmt(m.get("star_count"), ".0f")),
        (tr("cli.median_bg"), _fmt(m.get("background_adu"), ".1f", " ADU")),
        (tr("cli.median_noise"), _fmt(m.get("noise_adu"), ".2f", " ADU")),
        (tr("cli.sampling"), tr(f"sampling.{summary.sampling}") if summary.sampling else "-"),
    ]
    width = max(len(r[0]) for r in rows) + 2
    for label, value in rows:
        out.write(f"  {label:<{width}}{value}\n")

    out.write(f"\n{tr('cli.flagged')}\n")
    if not summary.flags:
        out.write(f"  {tr('cli.none_flagged')}\n")
    for f in summary.flags:
        out.write(f"  ! {f.file}: {f.reason}\n")
    if summary.errors:
        out.write(f"\n{tr('cli.failed')}\n")
        for name, err in summary.errors.items():
            out.write(f"  x {name}: {err}\n")
    return out.getvalue()


def cmd_analyze(args, cfg) -> int:
    folder: Path = args.folder
    if not folder.is_dir():
        print(f"Not a folder: {folder}", file=sys.stderr)
        return 2
    paths = find_frames(folder, recursive=args.recursive)
    if not paths:
        print(tr("cli.no_files", folder=folder), file=sys.stderr)
        return 1

    jobs = worker_count(cfg, args.jobs)
    options = measure_options(cfg)
    thresholds = session_thresholds(cfg)

    from advastro.session_context import find_calibration, folder_kind, session_root

    kind = folder_kind(paths)
    if kind != "lights":  # a folder of darks, flats... on its own (e.g. a dark library)
        calibration = _analyze_calibration({kind: paths}, None, None, jobs, args.quiet)
        sys.stdout.write(_render_calibration(calibration))
        return 0

    def progress(done: int, total: int, name: str) -> None:
        if not args.quiet:
            print(tr("cli.progress", done=done, total=total, name=name),
                  file=sys.stderr, end="\r" if done < total else "\n", flush=True)

    if not args.quiet:
        print(tr("cli.analyzing", count=len(paths), jobs=jobs), file=sys.stderr)
    subs, errors = analyze_paths(paths, options, jobs=jobs, progress=progress)
    summary = summarize(subs, thresholds, errors)

    session_file = args.session or find_mksession(folder)
    if session_file:
        for entry in load_mksession(session_file).entries:
            for w in entry.warnings:
                print(f"{session_file.name}: {w}", file=sys.stderr)
    scale, scale_source = resolve_pixel_scale(summary, cfg.section("equipment"), session_file)
    scale_note = (f"{scale:.2f} ″/px  ({tr('cli.pixel_scale_from', source=scale_source)})"
                  if scale else tr("cli.pixel_scale_unknown"))

    fmt = args.format or (cfg.get("report", "formats") or ["table"])[0]
    if fmt == "json":
        text = report.to_json(summary, scale, scale_source)
    elif fmt == "csv":
        text = report.to_csv(summary)
    else:
        text = _render_table(summary, scale_note)

    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)

    calibration = None
    want_cal = cfg.get("calibration", "analyze", True) and not args.no_calibration
    cal_files = find_calibration(session_root(folder)).all_files() if want_cal else {}
    if any(cal_files.values()):
        from advastro.readers import read_frame

        first = read_frame(paths[0]).meta if paths else None
        calibration = _analyze_calibration(cal_files, first, first and first.date_obs and
                                           first.date_obs.isoformat(), jobs, args.quiet)
        if fmt == "table" and not args.output:
            sys.stdout.write(_render_calibration(calibration))

    if (args.advise or args.workflow) and subs:
        from advastro.advisor.engine import to_markdown
        from advastro.pipeline import assess

        keep = {s.file: s.file not in summary.flagged_files() for s in summary.subs}
        result = assess(summary, keep, folder, cfg, scale, solve=args.solve,
                        calibration=calibration)
        print("\n" + describe_target(result.target), file=sys.stderr if args.output else None)
        if result.solve_note:
            print(f"Plate solving: {result.solve_note}", file=sys.stderr)
        md = to_markdown(result.advice, args.tool)
        if args.workflow:
            args.workflow.write_text(md, encoding="utf-8")
        if args.advise:
            sys.stdout.write("\n" + md)
    return 0 if subs else 1


def _analyze_calibration(files, lights_meta, lights_time, jobs, quiet):
    from advastro.engine.calibration import analyze_calibration, summarize_calibration

    total = sum(len(v) for v in files.values())

    def progress(done: int, n: int, name: str) -> None:
        if not quiet:
            print(f"[calibration {done}/{n}] {name}", file=sys.stderr,
                  end="\r" if done < n else "\n", flush=True)

    if not quiet:
        print(f"Analyzing {total} calibration frames...", file=sys.stderr)
    metrics, errors = analyze_calibration(files, jobs=jobs, progress=progress)
    return summarize_calibration(metrics, lights_meta, lights_time, errors)


def _render_calibration(cal) -> str:
    names = {"darks": "Darks", "flats": "Flats", "bias": "Bias", "darkflats": "Flat darks"}
    out = io.StringIO()
    out.write("\nCalibration frames\n")
    for kind, g in cal.groups.items():
        m = g.medians
        if kind == "flats":
            detail = (f"level {_fmt(m.get('level_pct'), '.0f', ' %')} · vignetting "
                      f"{_fmt(m.get('vignetting_pct'), '.0f', ' %')} · dust shadows "
                      f"{_fmt(m.get('dust_spots'), '.0f')}")
        else:
            detail = (f"level {_fmt(m.get('median_adu'), '.0f', ' ADU')} · noise "
                      f"{_fmt(m.get('noise_adu'), '.1f', ' ADU')} · hot pixels "
                      f"{_fmt(m.get('hot_pixels'), '.0f')}")
        extra = f" + {len(g.masters)} master" if g.masters else ""
        out.write(f"  {names[kind]:<11}{len(g.frames):>4}{extra}   {detail}\n")
        for f in g.flags:
            out.write(f"     ! {f.file}: {f.reason}\n")
    symbols = {"good": "✓", "info": "·", "warn": "!", "bad": "✗"}
    for n in cal.notes:
        out.write(f"  {symbols[n.level]} {n.text}\n")
    for name, err in cal.errors.items():
        out.write(f"  x {name}: {err}\n")
    return out.getvalue()


def describe_target(report) -> str:
    """One paragraph about what was imaged, for the command line."""
    if report.target is None:
        return tr("cli.target.unknown")
    t = report.target
    size = f", {t.major_arcmin:g}′" if t.major_arcmin else ""
    where = tr("cli.target.in", const=report.constellation) if report.constellation else ""
    lines = [tr("cli.target.line", label=t.label, ids=" · ".join(t.designations[:4]),
                type=tr("sky.type." + t.type_key), where=where, size=size),
             tr("cli.target.by", level=tr("gui.target.level." + report.confidence).lower(),
                source=report.source)]
    if report.sky:
        sky = report.sky
        lines.append(tr("cli.target.field", w=f"{sky.width_deg * 60:.0f}", h=f"{sky.height_deg * 60:.0f}",
                        scale=f"{sky.scale_arcsec:.2f}", ra=f"{sky.ra:.4f}", dec=f"{sky.dec:.4f}"))
    if report.others:
        lines.append(tr("cli.target.others", names=", ".join(o.label for o in report.others[:6])))
    return "\n".join(lines)


def cmd_solve(args, cfg) -> int:
    from advastro.readers import read_frame
    from advastro.sky.identify import identify
    from advastro.sky.solve import SolveError, detect_astap, locate, solve_astap

    frame = read_frame(args.file)
    sky = locate(frame)
    if sky is None or sky.level != "solved":
        install = detect_astap(cfg.get("solver", "astap_path", ""),
                               cfg.get("solver", "database_path", ""))
        try:
            sky = solve_astap(frame, install, timeout_s=cfg.get("solver", "timeout_s", 90.0))
        except SolveError as exc:
            print(f"Plate solving: {exc}", file=sys.stderr)
    print(describe_target(identify(sky, [frame.meta.object_name] if frame.meta.object_name
                                   else [])))
    return 0 if sky else 1


def cmd_astap(args, cfg) -> int:
    from advastro.sky.solve import detect_astap

    install = detect_astap(cfg.get("solver", "astap_path", ""),
                           cfg.get("solver", "database_path", ""))
    print(f"ASTAP program:   {install.executable or 'not found'}")
    print(f"Star databases:  {', '.join(install.databases) or 'none found'}"
          + (f"  ({install.database_dir})" if install.databases else ""))
    print("Ready to solve." if install.ready else
          "Not ready: install ASTAP and a star database, or set [solver] paths in your config.")
    return 0 if install.ready else 1


def cmd_rate(args, cfg) -> int:
    from advastro.rate import report
    from advastro.rate.judge import judge
    from advastro.rate.measure import measure
    from advastro.rate.picture import PictureError, load_picture

    try:
        pic = load_picture(args.file)
    except (PictureError, OSError, ValueError) as exc:
        print(f"{args.file}: {exc}", file=sys.stderr)
        return 1
    m = measure(pic)
    profile = dict(cfg.section("profile"))
    if args.skill:
        profile["skill"] = args.skill
    sky = None
    if args.sky:
        from advastro.rate.sky import sky_checks

        sky = sky_checks(pic, m, cfg, args.object, want_survey=bool(args.pdf))
        for k, v in sky.errors.items():
            print(f"{k}: {v}", file=sys.stderr)
    rating = judge(pic, m, profile, sky, object_kind=args.object_type, starless=args.starless,
                   object_name=args.object)
    if args.workflow:
        from advastro.rate.workflow import target_workflow, workflow_markdown

        tool = {"pixinsight": "PixInsight", "siril": "Siril"}[args.tool or "pixinsight"]
        text = workflow_markdown(target_workflow(rating, tool, profile.get("paid_addons", [])),
                                 tool)
    elif args.format == "json":
        text = report.to_json(rating)
    elif args.format == "markdown":
        text = report.to_markdown(rating, args.tool)
    else:
        text = _render_rating(rating, args.tool)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    if args.pdf:
        import os

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        try:
            from PySide6.QtGui import QGuiApplication
        except ImportError:
            print("PDF reports need the desktop app (PySide6); use -f markdown or json here.",
                  file=sys.stderr)
            return 1

        app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841
        from advastro.rate.pdf import write_pdf

        write_pdf(rating, args.pdf)
        print(f"PDF written to {args.pdf}", file=sys.stderr)
    return 0


def _render_rating(r, tool: str | None) -> str:
    import textwrap

    from advastro.rate.report import CATEGORY_NAMES, SEVERITY, VERDICT_NAMES, WORD, context_text

    p = r.picture
    out = io.StringIO()
    out.write(f"{p.path.name}  ({p.width} x {p.height}, {p.format.upper()} {p.bit_depth})\n\n")
    out.write(f"  {VERDICT_NAMES[r.verdict].upper()}  {r.score}/100  "
              f"({tr('rate.report.judged', skill=tr(f'gui.settings.skills.{r.skill}').lower())})\n")
    out.write(f"  {tr('rate.report.picture', context=context_text(r))}\n")
    out.write(f"  {r.headline}\n\n")
    for k, c in r.categories.items():
        bar = "#" * (c.score // 5) + "." * (20 - c.score // 5)
        out.write(f"  {CATEGORY_NAMES[k]:<13} {bar} {c.score:>3}  {WORD[c.verdict]}\n")
    if r.issues:
        out.write(f"\n{tr('rate.tab.findings')}\n")
        for f in r.issues:
            out.write(f"  [{SEVERITY[f.severity]:<8}] {f.title}: {f.text}\n")
    if r.strengths:
        out.write(f"\n{tr('rate.what_works')}\n")
        for f in r.strengths:
            out.write(f"  + {f.title}\n")
    if r.plan:
        out.write(f"\n{tr('rate.report.improve')}\n")
        for i, s in enumerate(r.plan, 1):
            out.write(f"\n  {i}. {s.finding.title}\n")
            if s.why:
                out.write(textwrap.fill(s.why, 96, initial_indent="     ",
                                        subsequent_indent="     ") + "\n")
            for name, steps in s.steps.items():
                if tool and name.lower() != tool:
                    continue
                out.write(f"     {name}:\n")
                for x in steps:
                    out.write(f"       - {x}\n")
            if s.masks:
                out.write(f"     {tr('rate.report.masks', names=', '.join(s.masks))}\n")
    if r.capture:
        out.write(f"\n{tr('rate.capture')}\n")
        for c in r.capture:
            out.write(f"  - {c}\n")
    if r.sky is not None and r.sky.depth and r.sky.depth.limit_mag:
        out.write("\n" + tr("rate.report.limit", mag=f"{r.sky.depth.limit_mag:.1f}") + "\n")
    return out.getvalue()


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()  # needed by bundled executables on Windows
    args = _build_parser().parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles: allow ″ and å ä ö
    try:
        cfg = load_config(
            session_folder=getattr(args, "folder", None),
            extra_files=args.config, overrides=args.set,
            use_user_config=not args.no_user_config,
        )
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 2
    set_language(args.lang or cfg.get("general", "language", "en"))
    for w in cfg.warnings:
        print(tr("cli.config_warning", message=w), file=sys.stderr)

    if args.command == "config":
        sys.stdout.write(to_toml(cfg))
        return 0
    if args.command == "solve":
        return cmd_solve(args, cfg)
    if args.command == "astap":
        return cmd_astap(args, cfg)
    if args.command == "rate":
        return cmd_rate(args, cfg)
    return cmd_analyze(args, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
