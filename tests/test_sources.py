"""Source roles enforce the train/serve policy (Scope v2.1 §4.1, §4.6)."""

import ast
from pathlib import Path

import pytest

from anemoi.data import sources
from anemoi.data.sources import OperationalUseError, Role


def test_era5_is_pretrain_only():
    assert sources.get("era5").role is Role.PRETRAIN_ONLY


def test_final_besttrack_is_labels_only():
    assert sources.get("besttrack_final").role is Role.LABELS_ONLY


def test_working_besttrack_is_operational():
    assert sources.get("besttrack_working").role is Role.OPERATIONAL


def test_reading_era5_in_the_inference_path_is_refused():
    with pytest.raises(OperationalUseError, match="gdas_gfs"):
        sources.assert_not_operational("era5")


def test_reading_final_besttrack_in_the_inference_path_is_refused():
    with pytest.raises(OperationalUseError, match="besttrack_working"):
        sources.assert_not_operational("besttrack_final")


def test_operational_sources_pass_the_guard():
    for src in sources.operational_sources():
        sources.assert_not_operational(src.key)


def test_gdas_latency_exceeds_the_v2_forty_five_minute_assumption():
    """The fact that invalidated v2's schedule, asserted so it cannot regress."""
    latency_hours = sources.get("gdas_gfs").typical_latency.total_seconds() / 3600
    assert latency_hours > 3.0


def test_era5_latency_is_days_not_hours():
    assert sources.get("era5").typical_latency.days >= 5


def test_unknown_source_raises():
    with pytest.raises(KeyError):
        sources.get("nonexistent")


# --- Who uses each source (`used_by`, served by GET /v1/sources) -------------

#: The order the contract fixes: models in catalogue order, then the two
#: non-model uses.
USED_BY_ORDER = ("lstm", "cnn", "transformer", "gnn", "pinn", "labels", "verification")

#: The adapter of every source that no code reads yet. `used_by` says so in
#: two ways: an empty list, or a bare "verification" that is a designation.
UNREAD_ADAPTERS = {
    "goes": "real_goes",
    "microwave": "real_microwave",
    "sst_ohc": "real_sst",
    "ensemble_perturbations": "real_ensemble",
    "dropsonde": "real_dropsonde",
    "ndbc": "real_ndbc",
}


def test_model_inputs_are_the_group1_models_in_catalogue_order():
    from anemoi.tracking.registry import GROUP1_MODELS

    assert tuple(sources.MODEL_INPUTS) == GROUP1_MODELS


def test_every_source_named_in_the_usage_tables_is_registered():
    named = {key for inputs in sources.MODEL_INPUTS.values() for key in inputs}
    named |= set(sources.LABEL_SOURCES) | set(sources.VERIFICATION_SOURCES)
    assert named <= set(sources.REGISTRY)


def test_a_usage_table_names_a_source_once():
    for name, keys in {
        **sources.MODEL_INPUTS,
        "labels": sources.LABEL_SOURCES,
        "verification": sources.VERIFICATION_SOURCES,
    }.items():
        assert len(set(keys)) == len(keys), name


def test_a_model_input_is_never_a_labels_only_source():
    for model, inputs in sources.MODEL_INPUTS.items():
        for key in inputs:
            assert sources.get(key).role is not Role.LABELS_ONLY, (model, key)


def test_a_label_or_verification_source_is_never_a_model_input():
    model_inputs = {key for inputs in sources.MODEL_INPUTS.values() for key in inputs}
    assert not model_inputs & set(sources.LABEL_SOURCES)
    assert not model_inputs & set(sources.VERIFICATION_SOURCES)


def test_every_model_reads_a_source_it_can_be_served_from():
    """A model whose only inputs were pretrain-only could be trained but
    never run in a cycle (`assert_not_operational`)."""
    for model, inputs in sources.MODEL_INPUTS.items():
        assert any(sources.get(key).is_operational for key in inputs), model


def test_every_required_cycle_input_has_a_model_consumer():
    """A source the cycle cannot run without, that no model reads, would be
    blocking cycles for nothing."""
    from anemoi.data.availability import REQUIRED_SOURCES

    for key in REQUIRED_SOURCES:
        assert set(sources.used_by(key)) & set(sources.MODEL_INPUTS), key


def test_used_by_follows_the_contract_order_for_every_source():
    for key in sources.REGISTRY:
        users = sources.used_by(key)
        assert set(users) <= set(USED_BY_ORDER), key
        assert list(users) == sorted(users, key=USED_BY_ORDER.index), key


def test_used_by_per_source():
    assert {key: sources.used_by(key) for key in sources.REGISTRY} == {
        "besttrack_working": ("lstm", "pinn"),
        "besttrack_final": ("labels", "verification"),
        "gdas_gfs": ("cnn", "transformer", "gnn", "pinn"),
        "era5": ("cnn", "transformer", "gnn", "pinn"),
        "goes": (),
        "ndbc": ("verification",),
        "dropsonde": ("verification",),
        "microwave": (),
        "sst_ohc": (),
        "ensemble_perturbations": (),
    }


def test_used_by_refuses_an_unknown_source():
    with pytest.raises(KeyError):
        sources.used_by("nonexistent")


def _imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update((node.module or "").split("."))
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.update(alias.name.split("."))
    return names


def test_a_source_nothing_uses_is_read_by_no_code():
    """Holds `used_by` to the code in the one direction it can drift
    silently: an adapter gets wired into training or a cycle, and the source
    still reads "not used yet" (or, for dropsonde and ndbc, a "verification"
    that `VERIFICATION_SOURCES` documents as not read yet).

    When this fails, the source has a reader: add it to `MODEL_INPUTS` (or
    correct `VERIFICATION_SOURCES`' comment and `SourceOut.used_by`'s
    description), then take it out of `UNREAD_ADAPTERS`.
    """
    for key in sources.REGISTRY:
        if not sources.used_by(key):
            assert key in UNREAD_ADAPTERS, key
    for key in UNREAD_ADAPTERS:
        assert set(sources.used_by(key)) <= {sources.VERIFICATION}, key

    package = Path(sources.__file__).resolve().parents[1]
    readers: dict[str, list[str]] = {}
    for path in sorted(package.rglob("*.py")):
        imported = _imported_names(ast.parse(path.read_text(encoding="utf-8")))
        for key, adapter in UNREAD_ADAPTERS.items():
            if adapter in imported and path.stem != adapter:
                readers.setdefault(key, []).append(str(path.relative_to(package)))
    assert readers == {}
