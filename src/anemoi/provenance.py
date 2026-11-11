"""What code and configuration produced something (#214).

A served cycle, a training run's registered model, a skew sample -- each is
only reproducible, or comparable with another, if it says which commit and
which `configs/*.yaml` produced it. Neither image carries `.git`
(`docker/multistage.Dockerfile.dockerignore`), so `git rev-parse` returns
nothing in production; CI writes ``build-info.json`` at the repo root before
every image build, and both images copy it to ``/app/build-info.json``.

Lookup order for the commit: ``ANEMOI_GIT_SHA``, then ``build-info.json``
(next to ``configs/``), then ``git rev-parse HEAD`` (a checkout), else
``None`` -- never a made-up value.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from functools import cache
from pathlib import Path

GIT_SHA_ENV = "ANEMOI_GIT_SHA"
BUILD_INFO_NAME = "build-info.json"


def _build_info_path() -> Path:
    from .config import config_dir

    return config_dir().parent / BUILD_INFO_NAME


@cache
def build_info() -> dict[str, str]:
    """``build-info.json``'s contents, or ``{}`` when there isn't one."""
    try:
        data = json.loads(_build_info_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


@cache
def git_sha() -> str | None:
    if sha := os.environ.get(GIT_SHA_ENV):
        return sha
    if sha := build_info().get("git_sha"):
        return sha
    try:
        out = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            cwd=Path(__file__).parent, capture_output=True, text=True, timeout=5, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    sha = out.stdout.strip()
    return sha or None


@cache
def config_digest() -> str:
    """sha256 over every ``configs/*.yaml`` file (name and bytes, sorted) --
    two runs with the same digest ran on the same settings."""
    from .config import config_dir

    h = hashlib.sha256()
    for path in sorted(config_dir().glob("*.yaml")):
        h.update(path.name.encode())
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def summary() -> dict[str, str | None]:
    """The provenance fields every record carries."""
    return {"git_sha": git_sha(), "config_sha256": config_digest()}
