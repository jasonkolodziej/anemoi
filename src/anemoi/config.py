"""Runtime configuration: the three files under ``configs/``.

``curriculum.yaml``, ``inference.yaml`` and ``monitoring.yaml`` are what the
code runs on. Modules read their tunables from here once, at import, into the
same module constants and function defaults they always had -- so every call
site is unchanged, and the file is the one place a value is written down.

Where the files are found, first match wins:

1. ``$ANEMOI_CONFIG_DIR`` -- an operator override, e.g. a mounted volume.
2. ``configs/`` at the repository root, located from this file (``src/anemoi``
   -> two levels up). Both images built from ``docker/multistage.Dockerfile``
   copy it to ``/app/configs`` beside ``/app/src``.

There are deliberately no built-in fallbacks. A fallback would let a missing
or misplaced file run on numbers nobody can see, which is the silent drift
this module exists to remove; a clear error at import is the better failure.

Two kinds of key:

* **Tunable** (:func:`get`) -- read and used as-is, after a type check.
* **Fixed** (:func:`fixed`) -- written in the file so the constraint is
  visible, but changing it would break something the file can't (the
  synoptic hours, the trained models' lead times, the operational flavor).
  A different value is refused with the reason, rather than half-applied.

Every key read is recorded (:func:`accessed`), so ``tests/test_config_sync.py``
can prove each key in the files is actually used by something.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR_ENV = "ANEMOI_CONFIG_DIR"
FILES = ("curriculum", "inference", "monitoring")

_accessed: set[str] = set()


class ConfigError(RuntimeError):
    """A configuration file is missing, malformed, or holds an invalid value."""


def config_dir() -> Path:
    override = os.environ.get(CONFIG_DIR_ENV)
    if override:
        path = Path(override)
        if not path.is_dir():
            raise ConfigError(f"{CONFIG_DIR_ENV}={override!r} is not a directory")
        return path
    path = Path(__file__).resolve().parents[2] / "configs"
    if path.is_dir():
        return path
    raise ConfigError(
        f"no configs/ directory found at {path}. Run from a checkout of the "
        f"repository, or set {CONFIG_DIR_ENV} to a directory holding "
        + ", ".join(f"{f}.yaml" for f in FILES)
    )


@cache
def _load(file: str) -> dict[str, Any]:
    if file not in FILES:
        raise ConfigError(f"unknown config file {file!r}; expected one of {FILES}")
    path = config_dir() / f"{file}.yaml"
    try:
        data = yaml.safe_load(path.read_text())
    except FileNotFoundError as exc:
        raise ConfigError(f"{path} not found") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must be a mapping at the top level")
    return data


def _check_type(where: str, value: Any, kind: type | tuple[type, ...]) -> Any:
    kinds = kind if isinstance(kind, tuple) else (kind,)
    # bool is an int subclass; a `true` where a number belongs is a mistake.
    if isinstance(value, bool) and bool not in kinds:
        raise ConfigError(f"{where} must be {_names(kinds)}, got {value!r}")
    if float in kinds and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    if not isinstance(value, kinds):
        raise ConfigError(f"{where} must be {_names(kinds)}, got {value!r}")
    return value


def _names(kinds: tuple[type, ...]) -> str:
    return " or ".join(k.__name__ for k in kinds)


def get(file: str, path: str, kind: type | tuple[type, ...]) -> Any:
    """The value at dotted ``path`` in ``<file>.yaml``, type-checked."""
    where = f"{file}.yaml: {path}"
    node: Any = _load(file)
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ConfigError(f"{where} is missing")
        node = node[part]
    _accessed.add(f"{file}.yaml:{path}")
    return _check_type(where, node, kind)


def get_list(file: str, path: str, item: type | tuple[type, ...]) -> list[Any]:
    where = f"{file}.yaml: {path}"
    values = get(file, path, list)
    return [_check_type(f"{where}[{i}]", v, item) for i, v in enumerate(values)]


def fixed(file: str, path: str, expected: Any, why: str) -> Any:
    """A key the code cannot honour a different value for. Refuses one."""
    kind = type(expected) if not isinstance(expected, (list, tuple)) else list
    value = get(file, path, kind)
    if isinstance(expected, tuple):
        expected = list(expected)
    if value != expected:
        raise ConfigError(f"{file}.yaml: {path} must be {expected!r}, got {value!r} -- {why}")
    return value


def accessed() -> frozenset[str]:
    """``"<file>.yaml:<dotted.path>"`` for every key read so far."""
    return frozenset(_accessed)
