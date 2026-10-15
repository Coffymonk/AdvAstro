"""Apply the rule file to a session's facts and translate the result for each tool."""

from __future__ import annotations

import string
import tomllib
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

from advastro.advisor.expr import UNKNOWN, evaluate

STAGES = ("insight", "prepare", "calibrate", "stack", "linear", "stretch", "nonlinear", "finish")
TOOLS = ("pixinsight", "siril")


@dataclass
class ToolStep:
    process: str
    menu: str
    settings: list[str]
    note: str | None = None


@dataclass
class Recommendation:
    id: str
    stage: str
    title: str
    why: str
    confidence: str
    params: dict = field(default_factory=dict)
    tools: dict[str, ToolStep] = field(default_factory=dict)


@dataclass
class Advice:
    family: str
    target_label: str
    level: str                     # "solved" | "pointing" | "name" | "none"
    insights: list[Recommendation]
    steps: list[Recommendation]

    def for_tool(self, tool: str) -> list[Recommendation]:
        return [s for s in self.steps if tool in s.tools or not s.tools]


class _Formatter(string.Formatter):
    """str.format that never fails: unknown names become '?', bad specs fall back to str."""

    def get_value(self, key, args, kwargs):
        value = kwargs.get(key) if isinstance(key, str) else None
        return "?" if value is None or value is UNKNOWN else value

    def format_field(self, value, format_spec):
        try:
            return format(value, format_spec)
        except (ValueError, TypeError):
            return str(value)


_fmt = _Formatter()


def render(template: str, values: dict) -> str:
    return _fmt.vformat(template, (), values)


@cache
def _rules() -> list[dict]:
    text = resources.files("advastro.advisor").joinpath("rules/workflow.toml").read_text("utf-8")
    return tomllib.loads(text)["step"]


@cache
def _translator(tool: str) -> dict:
    path = resources.files("advastro.advisor").joinpath(f"translators/{tool}.toml")
    return tomllib.loads(path.read_text("utf-8"))


def _value(v, facts):
    if isinstance(v, str) and v.startswith("="):
        result = evaluate(v[1:], facts)
        return None if result is UNKNOWN else result
    return v


def advise(facts: dict, tools: list[str] | None = None) -> Advice:
    tools = [t for t in (tools or TOOLS) if t in TOOLS]
    family = facts.get("family", "unknown")
    insights, steps = [], []
    for rule in _rules():
        families = rule.get("families")
        if families and family not in families:
            continue
        when = rule.get("when")
        if when and not evaluate(when, facts):
            continue
        params = {k: _value(v, facts) for k, v in rule.get("params", {}).items()}
        values = {**facts, **params}
        rec = Recommendation(
            id=rule["id"], stage=rule["stage"], title=render(rule["title"], values),
            why=render(rule.get("why", ""), values),
            confidence=str(_value(rule.get("confidence", "medium"), facts) or "medium"),
            params=params)
        if rec.stage != "insight":
            for tool in tools:
                for variant in _translator(tool).get(rec.id, []):
                    if variant.get("when") and not evaluate(variant["when"], values):
                        continue
                    rec.tools[tool] = ToolStep(
                        process=render(variant["process"], values),
                        menu=render(variant.get("menu", ""), values),
                        settings=[render(s, values) for s in variant.get("settings", [])],
                        note=render(variant["note"], values) if variant.get("note") else None)
                    break
        (insights if rec.stage == "insight" else steps).append(rec)
    steps.sort(key=lambda r: STAGES.index(r.stage))
    level = "solved" if facts.get("solved") else ("pointing" if facts.get("located") else (
        "name" if family != "unknown" else "none"))
    return Advice(family, facts.get("target_label", "the target"), level, insights, steps)


def to_markdown(advice: Advice, tool: str) -> str:
    """The workflow as a Markdown checklist, for export and the command line."""
    names = {"pixinsight": "PixInsight", "siril": "Siril"}
    lines = [f"# Processing workflow for {advice.target_label} ({names.get(tool, tool)})", ""]
    if advice.insights:
        lines.append("## Worth knowing first")
        for r in advice.insights:
            lines.append(f"- **{r.title}.** {r.why}")
        lines.append("")
    stage = None
    n = 0
    for r in advice.steps:
        if r.stage != stage:
            stage = r.stage
            lines += ["", f"## {stage.capitalize()}"]
        n += 1
        t = r.tools.get(tool)
        lines.append(f"{n}. **{r.title}** — {r.why}")
        if t:
            lines.append(f"    - *{t.process}* ({t.menu})")
            lines += [f"    - {s}" for s in t.settings]
            if t.note:
                lines.append(f"    - Note: {t.note}")
    return "\n".join(lines).strip() + "\n"
