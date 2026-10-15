"""The user manual: Markdown chapters per language, with section ids for context help.

Chapters live in help/<lang>/NN-name.md. A line ``<!-- id: some.key -->`` right before a
heading names that section, so the app can open the manual at the right place (F1, the
"?" on a finding). Links of the form ``help:some.key`` jump between sections. Languages
without a manual fall back to English.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

FALLBACK = "en"
_ID = re.compile(r"^<!--\s*id:\s*([\w.]+)\s*-->\s*$")
_HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


@dataclass
class Section:
    id: str
    title: str
    level: int
    text: str = ""                      # the section's own text, for searching


@dataclass
class Chapter:
    key: str                            # id of the chapter's first heading
    title: str
    markdown: str                       # without the id comments
    sections: list[Section] = field(default_factory=list)


def languages() -> list[str]:
    root = resources.files("advastro.help")
    return sorted(p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_"))


def _parse(text: str) -> tuple[str, list[Section]]:
    out, sections, pending = [], [], None
    in_code = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        m = _ID.match(line) if not in_code else None
        if m:
            pending = m.group(1)
            continue
        h = _HEADING.match(line) if not in_code else None
        if h:
            sec_id = pending or f"_{len(sections)}"
            sections.append(Section(sec_id, h.group(2), len(h.group(1))))
            pending = None
        elif sections:
            sections[-1].text += line + "\n"
        out.append(line)
    return "\n".join(out) + "\n", sections


@cache
def chapters(lang: str = FALLBACK) -> tuple[Chapter, ...]:
    if lang not in languages():
        lang = FALLBACK
    folder = resources.files("advastro.help").joinpath(lang)
    result = []
    for entry in sorted(folder.iterdir(), key=lambda p: p.name):
        if not entry.name.endswith(".md"):
            continue
        markdown, sections = _parse(entry.read_text(encoding="utf-8"))
        if not sections:
            continue
        result.append(Chapter(sections[0].id, sections[0].title, markdown, sections))
    return tuple(result)


def locate(topic: str, lang: str = FALLBACK) -> tuple[Chapter, Section] | None:
    """The chapter and section for a topic id, trying parent ids ('a.b.c' -> 'a.b' -> 'a')."""
    parts = topic.split(".")
    while parts:
        key = ".".join(parts)
        for ch in chapters(lang):
            for sec in ch.sections:
                if sec.id == key:
                    return ch, sec
        parts.pop()
    return None


def search(query: str, lang: str = FALLBACK) -> list[tuple[Chapter, Section]]:
    """Sections whose title or text contains every word of the query."""
    words = [w for w in query.lower().split() if w]
    if not words:
        return []
    hits = []
    for ch in chapters(lang):
        for sec in ch.sections:
            hay = (sec.title + " " + sec.text).lower()
            if all(w in hay for w in words):
                hits.append((ch, sec))
    return hits


# Positive findings open the entry for the problem they are the opposite of.
FINDING_TOPICS = {
    "sky_level": "dark_background", "highlights_ok": "clipped_highlights",
    "contrast_ok": "low_contrast", "flat_background": "gradient", "neutral_sky": "color_cast",
    "noise_ok": "noise", "round_stars": "trailed_stars", "tight_stars": "stars_soft",
    "flat_field": "corner_stars", "star_color_ok": "star_color",
    "saturation_ok": "oversaturated", "detail_ok": "low_detail", "clean_edges": "edges",
    "color_calibration_ok": "color_calibration",
}


def finding_topic(finding_id: str) -> str:
    return f"finding.{FINDING_TOPICS.get(finding_id, finding_id)}"
