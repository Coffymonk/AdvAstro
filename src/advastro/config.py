"""Layered TOML configuration.

Order, last wins:
    built-in defaults -> user config -> session config (advastro.toml in the
    session folder) -> explicit --config files -> command-line overrides.

Every value remembers which file it came from, so the GUI and
`advastro config --show` can explain where a setting was set.
"""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

SESSION_CONFIG_NAME = "advastro.toml"


def user_config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "AdvAstro"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "AdvAstro"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "advastro"


def user_config_path() -> Path:
    return user_config_dir() / "config.toml"


class ConfigError(ValueError):
    pass


@dataclass
class Config:
    values: dict[str, dict[str, Any]] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)  # "section.key" -> source
    warnings: list[str] = field(default_factory=list)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.values.get(section, {}).get(key, default)

    def section(self, name: str) -> dict[str, Any]:
        return dict(self.values.get(name, {}))

    def merge(self, data: dict[str, Any], source: str) -> None:
        """Merge one layer. Unknown sections or keys produce warnings, not errors."""
        for section, entries in data.items():
            if not isinstance(entries, dict):
                self.warnings.append(f"{source}: '{section}' must be a [section]; ignored")
                continue
            if section not in self.values:
                self.warnings.append(f"{source}: unknown section [{section}]; ignored")
                continue
            for key, value in entries.items():
                known = self.values[section]
                if key not in known:
                    self.warnings.append(f"{source}: unknown key '{section}.{key}'; ignored")
                    continue
                if not _same_type(known[key], value):
                    self.warnings.append(
                        f"{source}: '{section}.{key}' should be {type(known[key]).__name__}, "
                        f"got {type(value).__name__}; ignored")
                    continue
                known[key] = float(value) if isinstance(known[key], float) else value
                self.sources[f"{section}.{key}"] = source

    def set_override(self, dotted: str, raw: str) -> None:
        """Apply a command-line override like 'reject.fwhm_sigma=2.5'."""
        try:
            section, key = dotted.split(".", 1)
            value = tomllib.loads(f"v = {raw}")["v"]
        except (ValueError, tomllib.TOMLDecodeError):
            value = raw  # plain strings without quotes
            section, _, key = dotted.partition(".")
        self.merge({section: {key: value}}, "command line")


def _same_type(default: Any, value: Any) -> bool:
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, float):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, type(default))


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from exc


def load_config(
    session_folder: Path | None = None,
    extra_files: list[Path] | None = None,
    overrides: list[str] | None = None,
    use_user_config: bool = True,
) -> Config:
    defaults_text = resources.files("advastro").joinpath("defaults.toml").read_text("utf-8")
    cfg = Config(values=tomllib.loads(defaults_text))
    cfg.sources = {f"{s}.{k}": "defaults" for s, sec in cfg.values.items() for k in sec}

    layers: list[Path] = []
    if use_user_config and user_config_path().is_file():
        layers.append(user_config_path())
    if session_folder and (session_folder / SESSION_CONFIG_NAME).is_file():
        layers.append(session_folder / SESSION_CONFIG_NAME)
    for path in extra_files or []:
        if not path.is_file():
            raise ConfigError(f"Config file not found: {path}")
        layers.append(path)

    for path in layers:
        cfg.merge(_read_toml(path), str(path))
    for item in overrides or []:
        if "=" not in item:
            raise ConfigError(f"Override must look like section.key=value, got '{item}'")
        dotted, raw = item.split("=", 1)
        cfg.set_override(dotted.strip(), raw.strip())
    return cfg


def to_toml(cfg: Config, with_sources: bool = True) -> str:
    """Render the merged configuration as TOML, optionally noting each value's source."""
    lines: list[str] = []
    for section, entries in cfg.values.items():
        lines.append(f"[{section}]")
        for key, value in entries.items():
            rendered = _toml_value(value)
            src = cfg.sources.get(f"{section}.{key}", "")
            lines.append(f"{key} = {rendered}" + (f"    # from {src}" if with_sources else ""))
        lines.append("")
    return "\n".join(lines)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(v) for v in value) + "]"
    return repr(value)


def measure_options(cfg: Config):
    """MeasureOptions from the [measure] section."""
    from advastro.engine.metrics import MeasureOptions

    fields = MeasureOptions.__dataclass_fields__
    return MeasureOptions(**{k: v for k, v in cfg.section("measure").items() if k in fields})


def session_thresholds(cfg: Config):
    """SessionThresholds from the [reject] section."""
    from advastro.engine.session import SessionThresholds

    fields = SessionThresholds.__dataclass_fields__
    return SessionThresholds(**{k: v for k, v in cfg.section("reject").items() if k in fields})


def worker_count(cfg: Config, override: int | None = None) -> int:
    jobs = override if override is not None else cfg.get("general", "jobs")
    return jobs or os.cpu_count() or 1


def save_user_config(updates: dict[str, dict[str, Any]], path: Path | None = None) -> Path:
    """Merge updates into the user config file (creating it if needed) and write it.

    Sections and keys the user added by hand are kept; comments are not.
    """
    path = path or user_config_path()
    current: dict[str, dict[str, Any]] = {}
    if path.is_file():
        try:
            current = _read_toml(path)
        except ConfigError:
            current = {}
    for section, values in updates.items():
        current.setdefault(section, {}).update(values)
    lines = ["# Advanced Astrophoto Analyzer user settings. Edited by the Settings window;",
             "# you can also edit it by hand (see defaults.toml for every option).", ""]
    for section, values in current.items():
        if not isinstance(values, dict):
            continue
        lines.append(f"[{section}]")
        lines += [f"{k} = {_toml_value(v)}" for k, v in values.items()]
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
