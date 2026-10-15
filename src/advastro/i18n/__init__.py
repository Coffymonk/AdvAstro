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
