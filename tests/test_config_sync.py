"""`configs/inference.yaml` mirrors values that live in Python, with no
loader between them -- the YAML is documentation of what the code does.

That pairing has no enforcement, so it drifts silently: raising
`DEFAULT_ENSEMBLE_MEMBERS` 20 -> 50 (#188) left the config still declaring
20, and it took a review to catch. These assert the two agree, so the next
such change fails here instead of shipping a config that describes a system
that no longer exists.

Defaults are read off the real function signatures rather than hoisted into
new module constants -- the point is to check what the code actually does,
not to reshape the code so it is easier to assert against.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from anemoi.inference.postprocess import build_cone
from anemoi.inference.scheduler import DEFAULT_ENSEMBLE_MEMBERS, REDUCED_ENSEMBLE_MEMBERS

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "inference.yaml"


def _scalar(key: str) -> float:
    """The value of a `key: <number>` line, without taking a YAML dependency
    for three numbers."""
    m = re.search(
        rf"^\s*{re.escape(key)}:\s*([0-9]+(?:\.[0-9]+)?)\s*$",
        CONFIG.read_text(),
        re.MULTILINE,
    )
    assert m, f"{key} not found in {CONFIG.name}"
    return float(m.group(1))


def _default(name: str):
    return inspect.signature(build_cone).parameters[name].default


def test_configured_ensemble_members_matches_the_scheduler():
    assert _scalar("members") == DEFAULT_ENSEMBLE_MEMBERS


def test_the_load_shed_comment_still_describes_the_real_reduced_count():
    """The reduced count appears only in prose, so this checks the prose --
    a comment that contradicts the code is worse than no comment."""
    text = CONFIG.read_text()
    assert f"~{REDUCED_ENSEMBLE_MEMBERS} ensemble members" in text, (
        "the load-shedding comment in inference.yaml no longer matches "
        f"REDUCED_ENSEMBLE_MEMBERS ({REDUCED_ENSEMBLE_MEMBERS})"
    )
    assert f"instead of {DEFAULT_ENSEMBLE_MEMBERS}" in text


def test_configured_cone_thresholds_match_build_cone():
    assert _scalar("min_members_for_ensemble_cone") == _default("min_members")
    assert _scalar("underdispersion_fraction") == _default("underdispersion_fraction")
