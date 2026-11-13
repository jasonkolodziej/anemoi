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

#: The order the contract fixes: models in registry order
#: (`tracking.registry.GROUP1_MODELS`), then the two non-model uses.
USED_BY_ORDER = ("lstm", "cnn", "transformer", "gnn", "pinn", "labels", "verification")

#: Stage B `input_sources` (`configs/curriculum.yaml`) that no model reads.
#: The list is checked for role only, so it says what a stage may read.
STAGE_INPUTS_NO_MODEL_READS = {"goes", "sst_ohc"}

#: The cycle planner's optional tier (`data.availability.OPTIONAL_SOURCES`)
#: that no model reads. A late one still flags the cycle `missing:{source}`
#: and marks it degraded; `used_by`'s docstring, docs/api.md and
#: wiki/Data-Sources.md name them.
OPTIONAL_CYCLE_INPUTS_NO_MODEL_READS = {"goes", "ndbc", "sst_ohc", "ensemble_perturbations"}


def _model_sources() -> set[str]:
    return {key for inputs in sources.MODEL_INPUTS.values() for key in inputs}


def test_model_inputs_are_the_group1_models_in_registry_order():
    from anemoi.tracking.registry import GROUP1_MODELS

    assert tuple(sources.MODEL_INPUTS) == GROUP1_MODELS


def test_every_source_named_in_the_usage_tables_is_registered():
    named = _model_sources() | set(sources.LABEL_SOURCES) | set(sources.VERIFICATION_SOURCES)
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
    assert not _model_sources() & set(sources.LABEL_SOURCES)
    assert not _model_sources() & set(sources.VERIFICATION_SOURCES)


def test_a_verification_source_not_read_yet_is_verification_and_nothing_else():
    assert set(sources.VERIFICATION_NOT_READ_YET) < set(sources.VERIFICATION_SOURCES)
    for key in sources.VERIFICATION_NOT_READ_YET:
        assert sources.used_by(key) == (sources.VERIFICATION,), key


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


def test_the_optional_cycle_inputs_are_read_by_no_model():
    """The planner's tiers are older than `used_by`. They say what a cycle
    waits for and which absences it flags, not what a model reads, and no
    model reads any optional-tier source today: a cycle can be marked
    degraded for a source it would not have used. (The opportunistic tier
    is never flagged, so it can't mislead the same way.)

    When an optional source gains a model, take it out of the set above and
    out of the sentences that name it. Whether an unread source should
    degrade a cycle at all is `data.availability`'s to decide.
    """
    from anemoi.data.availability import OPTIONAL_SOURCES

    assert set(OPTIONAL_SOURCES) - _model_sources() == OPTIONAL_CYCLE_INPUTS_NO_MODEL_READS


def test_each_curriculum_stage_lists_what_its_models_read():
    """`curriculum.yaml` declares `input_sources` per stage. Every source a
    model reads has to be in the stage that reads it: Stage B is the
    operational fine-tune, and Stage A swaps in the pretrain-only source.
    What a stage lists beyond that is permission, and is named above so it
    can't grow unnoticed."""
    from anemoi.training.curriculum import stage_a, stage_b

    a, b = set(stage_a().input_sources), set(stage_b().input_sources)
    read = _model_sources()
    operational = {key for key in read if sources.get(key).is_operational}
    assert operational <= b
    assert read - operational <= a
    assert (a | b) - read == STAGE_INPUTS_NO_MODEL_READS


def test_the_label_sources_are_what_the_curriculum_trains_on():
    from anemoi.training.curriculum import stage_a, stage_b

    assert {stage_a().label_source, stage_b().label_source} == set(sources.LABEL_SOURCES)


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


# --- `used_by` against the code ----------------------------------------------
#
# The tables in data/sources.py are typed by hand. The tests below read the
# package's source to hold them to it. They see names: imports, attributes,
# string literals, calls and function signatures. They can't see what a
# function does with a value, so a model that stops reading an input while
# keeping its signature, and the verification entries, still rest on review.

PACKAGE = Path(sources.__file__).resolve().parents[1]

#: Every fetch adapter (`data/real_*.py`) and the registry sources it fetches.
#: A new adapter has to be added here, which is what puts its source under
#: `test_an_adapter_is_named_by_other_code_only_if_its_source_is_read`.
ADAPTERS = {
    "real_gridded": ("gdas_gfs", "era5"),
    "real_goes": ("goes",),
    "real_microwave": ("microwave",),
    "real_sst": ("sst_ohc",),
    "real_ensemble": ("ensemble_perturbations",),
    "real_dropsonde": ("dropsonde",),
    "real_ndbc": ("ndbc",),
}

#: Modules (paths under `src/anemoi`) that may name the adapter of a source
#: nothing reads, because they only fetch or cache it: what they produce must
#: not reach a model, a label or a verification score. Empty today. Each
#: entry is a claim for a reviewer to check, since the scan can't.
FETCH_ONLY_IMPORTERS: dict[str, set[str]] = {}

#: Modules that import by a computed name, which the scan can't follow. Both
#: load only their own siblings in `anemoi.models`.
COMPUTED_IMPORTS = {"models/__init__.py", "models/architecture.py"}


def _unread_sources() -> set[str]:
    """Sources no code reads: an empty `used_by`, or a `verification` that is
    a designation only."""
    unused = {key for key in sources.REGISTRY if not sources.used_by(key)}
    return unused | set(sources.VERIFICATION_NOT_READ_YET)


def _parse(relative: str) -> ast.Module:
    return ast.parse((PACKAGE / relative).read_text(encoding="utf-8"))


def _modules() -> dict[str, ast.Module]:
    return {
        path.relative_to(PACKAGE).as_posix(): ast.parse(path.read_text(encoding="utf-8"))
        for path in sorted(PACKAGE.rglob("*.py"))
    }


def _imported(tree: ast.AST) -> set[str]:
    """The modules and symbols a piece of code imports, by name."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update((node.module or "").split("."))
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.update(alias.name.split("."))
    return names


def _attributes(tree: ast.AST) -> set[str]:
    """`data.real_ndbc.fetch` reaches `real_ndbc` without importing it by
    name."""
    return {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}


def _names_adapter(tree: ast.AST, adapter: str, *, literals: bool = True) -> bool:
    """Whether a module can reach ``adapter``: an import, an attribute, or a
    string literal (`importlib.import_module("anemoi.data.real_goes")` and
    `runpy` take one). A bare variable of the same name is not a reference:
    it can only hold the module through one of those three."""
    if adapter in _imported(tree) | _attributes(tree):
        return True
    return literals and any(adapter in text for text in _string_literals(tree))


def _called(node: ast.Call) -> str | None:
    """`f(...)` and `module.f(...)` both call `f`."""
    return getattr(node.func, "id", None) or getattr(node.func, "attr", None)


def _calls(tree: ast.AST, function: str) -> bool:
    return any(
        isinstance(node, ast.Call) and _called(node) == function for node in ast.walk(tree)
    )


def _string_literals(tree: ast.AST) -> list[str]:
    """String constants that code can act on. A string that is a statement on
    its own is a docstring: it names a module without loading it."""
    prose = {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
    }
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose
    ]


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"no top-level function {name}")


def _parameters(function: ast.FunctionDef) -> set[str]:
    args = function.args
    return {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)}


def test_every_fetch_adapter_is_classified():
    """The scan below can only look for the adapters it knows. A new
    `data/real_*.py` fails here until it is given its registry source, and a
    source that claims no reader needs an adapter the scan can look for."""
    on_disk = {path.stem for path in (PACKAGE / "data").glob("real_*.py")}
    assert on_disk == set(ADAPTERS)

    fetched = {key for keys in ADAPTERS.values() for key in keys}
    assert fetched <= set(sources.REGISTRY)
    assert _unread_sources() <= fetched


def test_an_adapter_is_named_by_other_code_only_if_its_source_is_read():
    """Holds `used_by` to the code where it drifts most easily: an adapter
    gets wired into training or a cycle and its source still reads "not used
    yet" (or, for dropsonde and ndbc, a `verification` that is documented as
    not read yet). The other way round fails too: a source listed as read
    whose adapter nothing touches.

    What counts as naming an adapter is `_names_adapter`. `data/sources.py`
    is checked for imports and attributes only: its registry text names the
    adapters as prose. Another adapter naming one does count:
    `real_gridded` builds the GDAS fields every gridded model reads, so
    `real_sst` filling their `sst` channel would make OISST a model input.
    Only that "read" direction needs a module outside the adapters, since
    `real_ensemble` borrowing `real_gridded`'s GRIB helpers reads nothing.

    When this fails for a source `used_by` calls unread, the source has a
    reader. If a model, label or verification score now depends on it, add it
    to `MODEL_INPUTS` (or take it out of `VERIFICATION_NOT_READ_YET`) and
    update `SourceOut.used_by`'s description and the docs. If the module only
    fetches or caches it, list the module in `FETCH_ONLY_IMPORTERS`.
    """
    unread = _unread_sources()
    modules = _modules()
    adapter_files = {f"data/{adapter}.py" for adapter in ADAPTERS}
    named_by: dict[str, set[str]] = {key: set() for keys in ADAPTERS.values() for key in keys}
    for adapter, fetched in ADAPTERS.items():
        for relative, tree in modules.items():
            if relative == f"data/{adapter}.py":
                continue
            if relative in FETCH_ONLY_IMPORTERS.get(adapter, ()):
                continue
            if _names_adapter(tree, adapter, literals=relative != "data/sources.py"):
                for key in fetched:
                    named_by[key].add(relative)

    read_while_unread = {key: sorted(by) for key, by in named_by.items() if key in unread and by}
    assert read_while_unread == {}
    # Per source, not per adapter: a second adapter for a read source (the
    # OHC half of `sst_ohc`, say) may land before anything imports it.
    read_by_nothing = sorted(
        key for key, by in named_by.items() if key not in unread and not by - adapter_files
    )
    assert read_by_nothing == []


def test_a_fetch_only_importer_names_the_adapter_it_is_listed_for():
    """A stale entry would excuse a module that no longer exists, or one that
    no longer touches the adapter."""
    for adapter, importers in FETCH_ONLY_IMPORTERS.items():
        assert adapter in ADAPTERS, adapter
        for relative in importers:
            assert _names_adapter(_parse(relative), adapter), (adapter, relative)


def test_no_module_imports_by_a_computed_name():
    """`import_module(f"..data.real_{name}")` would load an adapter without
    naming it, and the scan above would miss it. A literal module name is
    fine: the scan reads string literals."""
    loaders = {"import_module", "__import__", "run_module", "run_path"}
    computed = set()
    for relative, tree in _modules().items():
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _called(node) in loaders):
                continue
            target = node.args[0] if node.args else None
            if not (isinstance(target, ast.Constant) and isinstance(target.value, str)):
                computed.add(relative)
    assert computed == COMPUTED_IMPORTS


def test_model_inputs_match_what_each_runner_and_live_builder_takes():
    """`MODEL_INPUTS` against the two places a model's input is built: its
    curriculum runner (`training/real_run*.py`) and its live builder
    (`real_inference_live.build_live_<model>_x`).

    * The gridded crop: a runner takes `era5_cache_dir` and `gdas_cache_dir`
      (Stage A reads one, Stage B the other) and imports `gridded_cache`;
      a live builder takes the `cache_dir` its GFS fields are kept under.
    * The track: both paths build it with `real_run.track_input`.

    So a track-only model given a field crop, or a gridded model given the
    track, fails here until `MODEL_INPUTS` says so.
    """
    live = _parse("training/real_inference_live.py")
    for model, inputs in sources.MODEL_INPUTS.items():
        runner_file = "real_run.py" if model == "lstm" else f"real_run_{model}.py"
        runner = _parse(f"training/{runner_file}")
        curriculum = _parameters(_function(runner, f"run_{model}_curriculum"))
        builder = _function(live, f"build_live_{model}_x")

        assert ("era5" in inputs) == ("era5_cache_dir" in curriculum), model
        assert ("gdas_gfs" in inputs) == ("gdas_cache_dir" in curriculum), model
        assert ("gdas_gfs" in inputs) == ("cache_dir" in _parameters(builder)), model
        reads_fields = bool({"era5", "gdas_gfs"} & set(inputs))
        assert reads_fields == ("gridded_cache" in _imported(runner)), model

        reads_track = "besttrack_working" in inputs
        assert reads_track == _calls(runner, "track_input"), model
        assert reads_track == _calls(builder, "track_input"), model
