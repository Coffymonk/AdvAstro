"""Rate my pic reports: JSON for tools, Markdown for forums, HTML for the PDF."""

from __future__ import annotations

import html
import json
from dataclasses import asdict, fields

import numpy as np

from advastro import APP_NAME, __version__
from advastro.i18n import tr
from advastro.rate.judge import Rating


class _Names:
    """names[key] -> the translation of '<prefix><key>' in the current language."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def __getitem__(self, key: str) -> str:
        return tr(self.prefix + key)


CATEGORY_NAMES = _Names("rate.cat.")
VERDICT_NAMES = _Names("rate.verdict.")
WORD = _Names("rate.word.")
SEVERITY = _Names("rate.sev.")


def _skill(r: Rating) -> str:
    return tr(f"gui.settings.skills.{r.skill}").lower()


def _plain(v):
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    if isinstance(v, np.ndarray):
        return None
    if isinstance(v, tuple):
        return [_plain(x) for x in v]
    if isinstance(v, float) and not np.isfinite(v):
        return None
    return v


def context_text(r: Rating) -> str:
    """'Emission nebula (North America Nebula, from the name), starless'."""
    c = r.context
    src = tr("rate.report.chosen") if c.kind_source == "manual" else \
        tr(f"rate.kind_source.{c.kind_source}")
    extra = ", ".join(x for x in (c.name, src) if x)
    text = tr(f"rate.kind.{c.kind}") + (f" ({extra})" if extra else "")
    if c.starless:
        text += ", " + tr("rate.report.starless")
    return text


def _mask_lines(keys: list[str], tool: str | None) -> list[str]:
    from advastro.rate.judge import load_masks

    recipes = load_masks()
    lines = []
    for k in keys:
        m = recipes.get(k)
        if not m:
            continue
        lines += ["", f"*{tr('rate.mask_how')}: {m['title']}.* {m.get('what', '')}"]
        for t in (["pixinsight", "siril"] if tool is None else [tool.lower()]):
            steps = m.get(t, [])
            if steps:
                lines += ["", f"{'PixInsight' if t == 'pixinsight' else 'Siril'}:", ""]
                lines += [f"{i}. {x}" for i, x in enumerate(steps, 1)]
    return lines


def measurements_dict(r: Rating) -> dict:
    m = r.measurements
    out = {}
    for f in fields(m):
        if f.name in ("overlays", "detections", "star_colors"):
            continue
        v = getattr(m, f.name)
        if isinstance(v, np.ndarray):
            out[f.name] = [[None if not np.isfinite(x) else round(float(x), 3) for x in row]
                           for row in v] if v.ndim == 2 and v.size <= 64 else None
        else:
            out[f.name] = _plain(v)
    return out


def to_json(r: Rating) -> str:
    p = r.picture
    sky = None
    if r.sky is not None:
        s = r.sky
        t = getattr(s.target, "target", None)
        sky = {
            "solved": s.field is not None,
            "ra": s.field.ra if s.field else None, "dec": s.field.dec if s.field else None,
            "scale_arcsec": s.field.scale_arcsec if s.field else None,
            "width_deg": s.field.width_deg if s.field else None,
            "target": t.label if t else None,
            "limit_mag": s.depth.limit_mag if s.depth else None,
            "colour_r": s.colour.r if s.colour else None,
            "survey": s.survey_name, "errors": s.errors,
        }
    return json.dumps({
        "app": "advastro-analyzer", "version": __version__, "kind": "rate-my-pic",
        "file": str(p.path), "format": p.format, "bit_depth": p.bit_depth,
        "width": p.width, "height": p.height, "mono": p.mono,
        "skill": r.skill, "score": r.score, "verdict": r.verdict, "headline": r.headline,
        "context": {"object_type": r.context.kind, "source": r.context.kind_source,
                    "object": r.context.name, "starless": r.context.starless,
                    "fills_frame": r.context.fills_frame},
        "categories": {k: {"score": v.score, "verdict": v.verdict}
                       for k, v in r.categories.items()},
        "findings": [{"id": f.id, "category": f.category, "severity": f.severity,
                      "title": f.title, "text": f.text} for f in r.findings],
        "plan": [{"finding": s.finding.id, "why": s.why, "steps": s.steps,
                  "capture": s.capture} for s in r.plan],
        "capture": r.capture,
        "measurements": measurements_dict(r),
        "sky": sky,
    }, indent=2, ensure_ascii=False, default=_plain)


def to_markdown(r: Rating, tool: str | None = None) -> str:
    p = r.picture
    lines = [f"# {tr('rate.title')}: {p.path.name}", "",
             tr("rate.report.score_line", verdict=VERDICT_NAMES[r.verdict], score=r.score,
                skill=_skill(r), headline=r.headline), "",
             tr("rate.report.picture", context=context_text(r)), "",
             f"| {tr('rate.report.category')} | {tr('rate.report.score')} | "
             f"{tr('rate.report.verdict')} |", "|---|---|---|"]
    for k, c in r.categories.items():
        lines.append(f"| {CATEGORY_NAMES[k]} | {c.score} | {WORD[c.verdict]} |")
    if r.strengths:
        lines += ["", f"## {tr('rate.what_works')}", ""]
        lines += [f"- **{f.title}.** {f.text}" for f in r.strengths]
    if r.issues:
        lines += ["", f"## {tr('rate.tab.findings')}", ""]
        lines += [f"- *{SEVERITY[f.severity]}* — **{f.title}.** {f.text}" for f in r.issues]
    if r.plan:
        lines += ["", f"## {tr('rate.report.improve')}", ""]
        for i, s in enumerate(r.plan, 1):
            lines.append(f"### {i}. {s.finding.title}")
            if s.why:
                lines += ["", s.why]
            for t, steps in s.steps.items():
                if tool and t.lower() != tool.lower():
                    continue
                lines += ["", f"**{t}**", ""] + [f"1. {x}" for x in steps]
            lines += _mask_lines(s.masks, tool)
            lines.append("")
    if r.capture:
        lines += [f"## {tr('rate.capture')}", ""] + [f"- {c}" for c in r.capture]
    lines += ["", f"*{APP_NAME} {__version__}*"]
    return "\n".join(lines) + "\n"


def to_html(r: Rating, images: dict[str, str] | None = None, accent: str = "#2a6fd6") -> str:
    """HTML for the PDF report. images: name -> resource URL (picture, survey)."""
    p, m = r.picture, r.measurements
    e = html.escape
    colour = {"excellent": "#2e9e5b", "ready": "#2e9e5b", "fixable": "#c98a12",
              "needs_work": "#c94040"}[r.verdict]
    sev_col = {"critical": "#c94040", "major": "#c94040", "minor": "#c98a12",
               "info": "#6b7480", "good": "#2e9e5b"}
    out = [f"""<html><head><style>
      body {{ font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif; font-size: 9.5pt;
             color: #1d232b; }}
      h1 {{ font-size: 18pt; margin: 0; }} h2 {{ font-size: 12.5pt; color: {accent};
      margin-top: 18px; border-bottom: 1px solid #d9dee5; }} h3 {{ font-size: 10.5pt;
      margin-bottom: 2px; }}
      .muted {{ color: #6b7480; }} td {{ padding: 3px 8px; }}
      .verdict {{ font-size: 15pt; font-weight: bold; color: {colour}; }}
    </style></head><body>
    <h1>{e(tr("rate.title"))}</h1>
    <p class="muted">{e(p.path.name)} · {p.width} × {p.height} · {e(p.format.upper())}
    {e(p.bit_depth)} · {e(tr("rate.report.judged", skill=_skill(r)))} · {APP_NAME} {__version__}<br>
    {e(tr("rate.report.picture", context=context_text(r)))}</p>"""]
    if images and images.get("picture"):
        out.append(f'<p><img src="{images["picture"]}" width="640"></p>')
    out.append(f'<p><span class="verdict">{e(VERDICT_NAMES[r.verdict])}</span> &nbsp; '
               f'<b>{r.score}</b>/100<br>{e(r.headline)}</p>')
    out.append('<table cellspacing="0">')
    for k, c in r.categories.items():
        bar = "█" * (c.score // 10) + "░" * (10 - c.score // 10)
        out.append(f"<tr><td><b>{CATEGORY_NAMES[k]}</b></td><td>{c.score}</td>"
                   f"<td style='color:{accent}'>{bar}</td><td>{WORD[c.verdict]}</td></tr>")
    out.append("</table>")
    if r.strengths:
        out.append(f"<h2>{e(tr('rate.what_works'))}</h2><ul>")
        out += [f"<li><b>{e(f.title)}.</b> {e(f.text)}</li>" for f in r.strengths]
        out.append("</ul>")
    if r.issues:
        out.append(f"<h2>{e(tr('rate.tab.findings'))}</h2><ul>")
        out += [f"<li><span style='color:{sev_col[f.severity]}'>{SEVERITY[f.severity]}</span>"
                f" — <b>{e(f.title)}.</b> {e(f.text)}</li>" for f in r.issues]
        out.append("</ul>")
    if r.plan:
        out.append(f"<h2>{e(tr('rate.report.improve'))}</h2>")
        for i, s in enumerate(r.plan, 1):
            out.append(f"<h3>{i}. {e(s.finding.title)}</h3><p class='muted'>{e(s.why)}</p>")
            for tool, steps in s.steps.items():
                out.append(f"<p><b>{e(tool)}</b></p><ol>" +
                           "".join(f"<li>{e(x)}</li>" for x in steps) + "</ol>")
    if r.capture:
        out.append(f"<h2>{e(tr('rate.capture'))}</h2><ul>" +
                   "".join(f"<li>{e(c)}</li>" for c in r.capture) + "</ul>")
    if r.sky is not None and (r.sky.field or r.sky.errors):
        s = r.sky
        out.append(f"<h2>{e(tr('rate.sky_section'))}</h2>")
        if s.field:
            t = getattr(s.target, "target", None)
            f = s.field
            out.append("<p>" + e(tr("rate.field", ra=f"{f.ra:.3f}", dec=f"{f.dec:+.3f}",
                                    scale=f"{f.scale_arcsec:.2f}", w=f"{f.width_deg:.2f}",
                                    h=f"{f.height_deg:.2f}", source=f.source))
                       + (f" · {e(t.label)}" if t else "") + "</p>")
        if s.depth and s.depth.limit_mag:
            out.append(f"<p>{e(tr('rate.report.limit', mag=f'{s.depth.limit_mag:.1f}'))}</p>")
        if s.colour:
            out.append(f"<p>{e(tr('rate.colour_text', r=f'{s.colour.r:.2f}', n=s.colour.stars))}"
                       "</p>")
        if images and images.get("survey"):
            from advastro.rate.sky import survey_credit

            credit = tr("rate.credit", source=survey_credit(s.survey_name))
            out.append(f"<p>{e(tr('rate.report.survey', name=s.survey_name or 'Survey'))}<br>"
                       f'<img src="{images["survey"]}" width="640"><br>'
                       f"<span class='muted'>{e(credit)}</span></p>")
        if s.depth or s.colour:
            from advastro.rate.sky import GAIA_CREDIT

            out.append(f"<p class='muted'>{e(tr('rate.report.star_data'))}: "
                       f"{e(GAIA_CREDIT)}.</p>")
        for k, v in s.errors.items():
            out.append(f"<p class='muted'>{e(k)}: {e(v)}</p>")
    out.append(f"<h2>{e(tr('rate.report.measurements'))}</h2><table cellspacing='0'>")
    rows = [(tr("rate.d.sky"), f"{m.sky * 100:.1f} %"),
            (tr("rate.d.gradient"), f"{m.gradient_pct:.1f} %"),
            (f"{tr('rate.d.noise')} / {tr('rate.d.mottle')}",
             f"{m.noise * 100:.2f} % / {m.noise_mid * 100:.2f} %"),
            (tr("rate.d.stars"), f"{m.star_count:,}"),
            (tr("rate.d.fwhm"), f"{m.fwhm:.2f} px" if m.fwhm else "–"),
            (tr("rate.d.ecc"), f"{m.ellipticity:.2f}" if m.ellipticity is not None else "–"),
            (tr("rate.d.corners"), f"{m.corner_ratio:.2f}" if m.corner_ratio else "–"),
            (tr("rate.d.saturation"), f"{m.saturation * 100:.0f} %"),
            (tr("rate.d.clip"), f"{m.black_clip_pct:.2f} % / {m.white_clip_pct:.2f} %"),
            (tr("rate.d.hot"), str(m.hot_pixels))]
    out += [f"<tr><td>{e(a)}</td><td>{e(b)}</td></tr>" for a, b in rows]
    out.append("</table></body></html>")
    return "\n".join(out)


def rating_summary_line(r: Rating) -> str:
    return f"{VERDICT_NAMES[r.verdict]} · {r.score}/100"


__all__ = ["to_json", "to_markdown", "to_html", "measurements_dict", "asdict"]
