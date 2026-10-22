"""Translations.

All user-facing text lives in TOML catalogs under advastro/i18n/locales/,
one file per language (en.toml, sv.toml, ...). The planned in-app language
editor and Hosted Weblate both edit these same files. Missing keys fall back
to English, then to the key itself, so a partial translation never breaks the UI.
"""

from __future__ import annotations

import tomllib
from functools import cache
from importlib import resources

FALLBACK = "en"
_current = FALLBACK


@cache
def _catalog(lang: str) -> dict[str, str]:
    try:
        text = resources.files("advastro.i18n").joinpath(f"locales/{lang}.toml").read_text("utf-8")
    except (FileNotFoundError, OSError):
        return {}
    flat: dict[str, str] = {}

    def walk(prefix: str, node: dict) -> None:
        for k, v in node.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                walk(key, v)
            else:
                flat[key] = str(v)

    walk("", tomllib.loads(text))
    return flat


def available_languages() -> list[str]:
    folder = resources.files("advastro.i18n").joinpath("locales")
    return sorted(p.name[:-5] for p in folder.iterdir() if p.name.endswith(".toml"))


def set_language(lang: str) -> None:
    global _current
    _current = lang


def current_language() -> str:
    return _current


def tr(key: str, **params) -> str:
    """Translate a key like 'cli.analyzing'; {placeholders} are filled from params."""
    text = _catalog(_current).get(key) or _catalog(FALLBACK).get(key) or key
    return text.format(**params) if params else text


# ---------------------------------------------------------------- data files
def _merge(base, over):
    """Overlay translated text onto English data.

    Tables merge key by key; arrays of tables merge by their "id" when they have one,
    otherwise position by position; anything else (strings, lists of strings) is replaced.
    """
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = _merge(base[k], v) if k in base else v
        return out
    if isinstance(base, list) and isinstance(over, list) and base and \
            all(isinstance(x, dict) for x in base) and all(isinstance(x, dict) for x in over):
        if all("id" in x for x in base) and all("id" in x for x in over):
            by_id = {x["id"]: x for x in over}
            return [_merge(x, by_id[x["id"]]) if x["id"] in by_id else x for x in base]
        return [_merge(b, o) for b, o in zip(base, over, strict=False)] + base[len(over):]
    return over


@cache
def _data(package: str, name: str, lang: str) -> dict:
    root = resources.files(package)
    data = tomllib.loads(root.joinpath(name).read_text("utf-8"))
    if lang != FALLBACK:
        stem, _, ext = name.rpartition(".")
        try:
            over = tomllib.loads(root.joinpath(f"{stem}.{lang}.{ext}").read_text("utf-8"))
        except (FileNotFoundError, OSError):
            over = None
        if over:
            data = _merge(data, over)
    return data


def load_data(package: str, name: str, lang: str | None = None) -> dict:
    """A TOML data file (rules, tips, workflows) in the current language.

    'rules/workflow.toml' is overlaid with 'rules/workflow.sv.toml' when the language is
    Swedish; the overlay holds only translated text, everything else comes from English.
    """
    return _data(package, name, lang or _current)
