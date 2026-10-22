"""The Swedish texts must cover the English ones and use the same placeholders."""
from __future__ import annotations

import re
import tomllib
from importlib import resources
from pathlib import Path

import pytest

from advastro.i18n import load_data, set_language, tr

SRC = Path(__file__).resolve().parents[1] / "src" / "advastro"
FIELD = re.compile(r"\{(\w+)")


def _flat(d: dict, prefix: str = "") -> dict[str, object]:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flat(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


def _fields(value) -> set[str]:
    if isinstance(value, str):
        return set(FIELD.findall(value))
    if isinstance(value, list):
        return set().union(set(), *(_fields(v) for v in value))
    return set()


def _catalogue(lang: str) -> dict[str, object]:
    path = resources.files("advastro.i18n") / "locales" / f"{lang}.toml"
    return _flat(tomllib.loads(path.read_text(encoding="utf-8")))


def test_every_english_text_has_a_swedish_one():
    en, sv = _catalogue("en"), _catalogue("sv")
    assert sorted(set(en) - set(sv)) == []
    assert sorted(set(sv) - set(en)) == []


def test_catalogue_placeholders_match():
    en, sv = _catalogue("en"), _catalogue("sv")
    wrong = {k: (_fields(en[k]), _fields(sv[k])) for k in en
             if k in sv and _fields(sv[k]) - _fields(en[k])}
    assert wrong == {}


OVERLAYS = sorted(p for p in SRC.rglob("*.sv.toml"))


@pytest.mark.parametrize("overlay", OVERLAYS, ids=lambda p: p.name)
def test_overlay_matches_its_base(overlay: Path):
    base = tomllib.loads(overlay.with_name(overlay.name.replace(".sv.toml", ".toml"))
                        .read_text(encoding="utf-8"))
    over = tomllib.loads(overlay.read_text(encoding="utf-8"))
    problems: list[str] = []

    def check(b, o, where):
        if isinstance(o, dict):
            if not isinstance(b, dict):
                problems.append(f"{where}: not a table in the base")
                return
            for k, v in o.items():
                if k == "id":
                    continue
                if k not in b:
                    problems.append(f"{where}.{k}: not in the base")
                else:
                    check(b[k], v, f"{where}.{k}")
        elif isinstance(o, list) and o and all(isinstance(x, dict) for x in o):
            if all("id" in x for x in o):
                ids = {x.get("id"): x for x in b}
                for x in o:
                    if x["id"] not in ids:
                        problems.append(f"{where}: id {x['id']} not in the base")
                    else:
                        check(ids[x["id"]], x, f"{where}[{x['id']}]")
            else:
                if len(o) != len(b):
                    problems.append(f"{where}: {len(o)} variants, base has {len(b)}")
                for i, (bx, ox) in enumerate(zip(b, o)):
                    check(bx, ox, f"{where}[{i}]")
        else:
            if isinstance(b, list) and isinstance(o, list) and len(b) != len(o):
                problems.append(f"{where}: {len(o)} items, base has {len(b)}")
            extra = _fields(o) - _fields(b)
            if extra and not (isinstance(o, str) and o.startswith("=")):
                problems.append(f"{where}: unknown placeholders {sorted(extra)}")

    check(base, over, overlay.name)
    assert problems == []


def test_overlays_are_used_in_swedish():
    try:
        set_language("sv")
        tips = load_data("advastro.rate", "tips.toml")
        assert tips["noise"]["why"].startswith("Korn syns")
        wf = load_data("advastro.rate", "workflows.toml")
        assert wf["stage"][0]["title"] == "Beskär staplingskanterna"
        assert wf["stage"][0]["kinds"] == "all"          # untranslated fields stay
        assert tr("sky.err.no_astap") == "ASTAP hittades inte"
        set_language("en")
        assert load_data("advastro.rate", "tips.toml")["noise"]["why"].startswith("Grain")
    finally:
        set_language("en")
