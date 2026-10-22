"""A processing workflow for the rated picture's object type (Rate my pic's Workflow tab).

The stages come from workflows.toml. They are filtered by object type, the steps are
chosen for the user's program and add-ons, and stages that address a finding in this
picture are marked, so the user sees where their own image needs the most work.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

from advastro.rate.objects import NAMES, WITH_ARTICLE


@dataclass
class Stage:
    id: str
    title: str
    explain: str
    steps: list[str]
    note: str | None = None
    linear: bool = False
    needed_by: list[str] = field(default_factory=list)   # titles of findings it addresses


@dataclass
class TargetWorkflow:
    kind: str
    intro: str
    about: str
    stages: list[Stage]


@cache
def _data() -> dict:
    return tomllib.loads(resources.files("advastro.rate").joinpath("workflows.toml")
                         .read_text(encoding="utf-8"))


def target_workflow(rating, tool: str = "PixInsight", addons: list[str] | None = None
                    ) -> TargetWorkflow:
    """Stages for the rating's object type, written for one program ('PixInsight' or 'Siril')."""
    data = _data()
    ctx = rating.context
    kind = ctx.kind if ctx.kind in NAMES else "unknown"
    key = tool.lower()
    addons = addons or []
    issues = {f.id: f.title for f in rating.findings if f.severity != "good"}
    obj = f"{ctx.name}, {WITH_ARTICLE[kind]}" if ctx.name and kind != "unknown" else \
        WITH_ARTICLE.get(kind, "your target")
    intro = data["intro"]["all"].format(object=obj)
    about = data["intro"].get(kind, data["intro"]["unknown"])
    stages = []
    for st in data["stage"]:
        kinds = st.get("kinds", "all")
        if kinds != "all" and kind not in kinds:
            continue
        if ctx.starless and st["id"] in ("stars_off", "stars_on", "cluster_stars"):
            continue
        steps = st.get(key, [])
        for addon in addons:
            variant = st.get(f"{key}@{addon}")
            if variant:
                steps = variant
                break
        needed = [issues[f] for f in st.get("fixes", []) if f in issues]
        stages.append(Stage(st["id"], st["title"], st["explain"], list(steps),
                            st.get(f"note#{kind}"), bool(st.get("linear", False)), needed))
    return TargetWorkflow(kind, intro, about, stages)


def workflow_markdown(wf: TargetWorkflow, tool: str) -> str:
    lines = [f"# Processing workflow ({tool})", "", wf.intro, "", wf.about, ""]
    for i, st in enumerate(wf.stages, 1):
        lines.append(f"## {i}. {st.title}" + (" (linear)" if st.linear else ""))
        lines += ["", st.explain, ""]
        if st.needed_by:
            lines += [f"**Your image:** {', '.join(st.needed_by)}.", ""]
        if st.note:
            lines += [f"*For this object:* {st.note}", ""]
        lines += [f"{n}. {s}" for n, s in enumerate(st.steps, 1)]
        lines.append("")
    return "\n".join(lines)
