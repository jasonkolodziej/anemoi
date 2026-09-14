"""Sub-brand registry tests (Branding Brief v1.1 §2.2, §5.2, §5.3)."""

from __future__ import annotations

import pytest

from anemoi.branding import (
    FUSION_COLOR,
    GODS,
    STRUCTURAL_COLORS,
    Module,
    color_for,
    experiment_name,
    god,
)


def test_six_gods_cover_six_directions():
    assert len(GODS) == 6
    assert [g.direction for g in GODS] == ["N", "S", "E", "W", "NE", "NW"]


def test_slugs_and_architectures_are_unique():
    assert len({g.slug for g in GODS}) == 6
    assert len({g.architecture for g in GODS}) == 6


def test_lookup_by_slug_and_by_architecture_agree():
    assert god("boreas") is god("lstm")
    assert god("skiron") is god("diffusion")


def test_lookup_is_case_insensitive():
    assert god("BOREAS").name == "Boreas"


def test_unknown_name_raises_rather_than_guessing():
    with pytest.raises(KeyError):
        god("fusion")


def test_only_skiron_belongs_to_spread():
    spread = [g for g in GODS if g.module is Module.SPREAD]
    assert [g.slug for g in spread] == ["skiron"]
    assert all(g.module is Module.CORE for g in GODS if g.slug != "skiron")


def test_experiment_names_are_the_god_slugs():
    assert experiment_name("transformer") == "notus"
    assert experiment_name("pinn") == "kaikias"


def test_structural_colors_are_never_model_colors():
    """§5.3: if a colour appears on data it must map to exactly one model."""
    model_colors = {g.color for g in GODS} | {FUSION_COLOR}
    assert not model_colors & set(STRUCTURAL_COLORS.values())


def test_every_god_color_is_distinct():
    assert len({g.color for g in GODS}) == 6
    assert color_for("gnn") == "#EF4444"
