"""One model, every basin: each basin scored and gated on its own
(docs/multi_basin.md).

A single overall error can hide a basin the model is poor in, and an error
over a different mix of basins isn't comparable with the last one. So every
validation run also records each basin's own errors and sample counts and
what persistence scores there; a basin is served as in distribution only
once every champion beats persistence in it; and a candidate is compared
with the incumbent on the reference basin alone.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.sources import Flavor
from anemoi.metrics.basin import (
    basin_key,
    per_basin_scores,
    sample_counts,
    scored_basins,
    trained_basins,
    verified_basins,
)
from anemoi.models.base import DEFAULT_LEADS
from anemoi.tracking.registry import GROUP1_MODELS, ModelRegistry, Stage
from anemoi.training.basin_gates import basin_tags, resolve_basin_inputs, served_columns
from anemoi.training.curriculum import Curriculum, CurriculumRun, StageResult
from anemoi.training.promotion import MetricSet, evaluate_promotion
from anemoi.training.real_run import validation_metrics

PRIMARY = "track_error_48h_nm"


def northward_track(
    storm_id: str, season: int, *, n: int = 30, step_deg: float = 0.5, accel: float = 0.0,
    lon: float = -50.0,
) -> Track:
    """A storm moving due north, ``step_deg`` a fix (plus ``accel`` more each
    fix), strengthening 2 kt a fix. With no acceleration, holding its last
    motion is exactly right."""
    start = datetime(season, 8, 1, tzinfo=UTC)
    lat = 10.0
    fixes = []
    for i in range(n):
        lat += step_deg + accel * i
        fixes.append(
            Fix(
                storm_id=storm_id, valid_time=start + timedelta(hours=6 * i),
                lat=lat, lon=lon, max_wind_kt=40.0 + 2.0 * i, min_pressure_mb=1000.0 - i,
                quality=TrackQuality.FINAL,
            )
        )
    return Track(storm_id=storm_id, fixes=tuple(fixes))


def metric_set(**values: float) -> MetricSet:
    return MetricSet(split="val", flavor=Flavor.GDAS_FINETUNE, values=dict(values))


def by_basin(overall: float, **basins: tuple[float, float]) -> MetricSet:
    """Validation metrics with ``basin=(model error, persistence error)``."""
    values = {PRIMARY: overall}
    for basin, (model, persistence) in basins.items():
        values[basin_key(basin, PRIMARY)] = model
        values[basin_key(basin, "persistence_" + PRIMARY)] = persistence
        values[basin_key(basin, "train_samples")] = 100.0
        values[basin_key(basin, "val_samples")] = 20.0
    return metric_set(**values)


def complete_run() -> CurriculumRun:
    run = CurriculumRun(Curriculum.standard("lstm"))
    for name, flavor in (("A", Flavor.ERA5_PRETRAIN), ("B", Flavor.GDAS_FINETUNE)):
        run.record(StageResult(name, flavor, 10, 0.4, 0.5, f"s3://ckpt/{name}"))
    return run


# ---- per-basin scores ------------------------------------------------------------


def _forecasts() -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Three samples, one lead each verifiable: two Atlantic, one Eastern
    Pacific. Latitude errors of 1, 3 and 2 degrees (60, 180, 120 n mi)."""
    n_leads = len(DEFAULT_LEADS)
    obs = np.zeros((3, n_leads, 3))
    obs[..., 0], obs[..., 1], obs[..., 2] = 20.0, -60.0, 50.0
    pred = obs.copy()
    pred[0, 0, 0] += 1.0
    pred[1, 0, 0] += 3.0
    pred[2, 0, 0] += 2.0
    pred[2, 0, 2] += 10.0  # and 10 kt too strong
    mask = np.zeros((3, n_leads), dtype=bool)
    mask[:, 0] = True
    return pred, obs, mask, ["AL012022", "AL022022", "EP012022"]


def test_each_basin_is_scored_on_its_own_storms():
    pred, obs, mask, storm_ids = _forecasts()
    scores = per_basin_scores(pred, obs, mask, storm_ids, DEFAULT_LEADS)
    assert scores["AL/track_error_12h_nm"] == pytest.approx(120.0, rel=0.01)  # mean of 60, 180
    assert scores["EP/track_error_12h_nm"] == pytest.approx(120.0, rel=0.01)
    assert scores["AL/intensity_error_12h_kt"] == 0.0
    assert scores["EP/intensity_error_12h_kt"] == pytest.approx(10.0)
    assert not any("24h" in key for key in scores)  # no verifiable pair at that lead


def test_a_runs_validation_metrics_carry_the_overall_and_each_basin():
    pred, obs, mask, storm_ids = _forecasts()
    metrics = validation_metrics(
        Flavor.GDAS_FINETUNE, pred, obs, mask,
        val_storm_ids=storm_ids, train_storm_ids=["AL011990"] * 5 + ["EP011990"] * 2,
    )
    values = metrics.values
    assert values["track_error_12h_nm"] == pytest.approx(120.0, rel=0.01)  # all three
    assert scored_basins(values) == ("AL", "EP")
    assert (values["AL/val_samples"], values["EP/val_samples"]) == (2.0, 1.0)
    assert (values["AL/train_samples"], values["EP/train_samples"]) == (5.0, 2.0)


def test_without_storm_ids_only_the_overall_metrics_are_recorded():
    pred, obs, mask, _ = _forecasts()
    values = validation_metrics(Flavor.GDAS_FINETUNE, pred, obs, mask).values
    assert scored_basins(values) == ()
    assert "track_error_12h_nm" in values


def test_nothing_verifiable_is_an_error_naming_the_stage():
    pred, obs, mask, storm_ids = _forecasts()
    with pytest.raises(ValueError, match="stage B: no verifiable"):
        validation_metrics(
            Flavor.GDAS_FINETUNE, pred, obs, np.zeros_like(mask),
            val_storm_ids=storm_ids, stage_name="B",
        )


def test_a_storm_id_per_sample_is_required():
    pred, obs, mask, storm_ids = _forecasts()
    with pytest.raises(ValueError, match="2 storm ids for 3 samples"):
        per_basin_scores(pred, obs, mask, storm_ids[:2], DEFAULT_LEADS)


def test_trained_basins_are_the_ones_with_training_samples():
    """A gridded model skips a window with no cached field: a basin in the
    storm archive whose cache hasn't been fetched was not trained on."""
    values = {
        **sample_counts(["AL012021"] * 3, "train"),
        **sample_counts(["AL012022", "EP012022"], "val"),
    }
    assert trained_basins(values) == ("AL",)
    assert trained_basins({"track_error_48h_nm": 40.0}) is None  # a run from before the counts


# ---- the persistence baseline, on the model's own windows --------------------------


def test_persistence_holds_the_last_motion_and_the_current_wind():
    from anemoi.data.besttrack import WorkingTrackNoise
    from anemoi.training.real_run import LEAD_STEPS, iter_stage_windows

    exact = WorkingTrackNoise(0.0, 0.0, 0.0, quantise=False)
    track = northward_track("AL012022", 2022)
    sw = next(iter_stage_windows([track], np.random.default_rng(0), noise=exact))
    # Exact for a storm that keeps its motion: forecast and target agree
    # wherever the target exists.
    p = sw.persistence
    assert p.shape == (len(LEAD_STEPS), 3)
    np.testing.assert_allclose(p[sw.mask, :2], sw.y[sw.mask, :2], atol=1e-6)
    assert (p[:, 2] == sw.current.max_wind_kt).all()


def test_persistence_is_scored_on_exactly_the_samples_the_model_was():
    """A gridded runner skips windows with no cached field; scoring the
    baseline over every window instead could make a basin look easy to
    beat. So it is scored on the same samples, with the same mask."""
    pred, obs, mask, storm_ids = _forecasts()
    values = validation_metrics(
        Flavor.GDAS_FINETUNE, pred, obs, mask, val_storm_ids=storm_ids,
        persistence_abs=obs.copy(),  # a perfect baseline on these samples
    ).values
    assert values["AL/persistence_track_error_12h_nm"] == 0.0
    assert values["EP/persistence_track_error_12h_nm"] == 0.0
    # Same leads as the model: nothing scored where the model wasn't.
    assert not any("persistence" in k and "24h" in k for k in values)
    assert verified_basins(values, "track_error_12h_nm") == ()


# ---- verified basins, and the tags ---------------------------------------------


def test_a_basin_is_verified_when_the_model_beats_persistence_there():
    metrics = by_basin(60.0, AL=(50.0, 140.0), EP=(150.0, 120.0), CP=(float("nan"), 100.0))
    assert verified_basins(metrics.values, PRIMARY) == ("AL",)


def test_a_basin_with_no_baseline_is_not_verified():
    values = {PRIMARY: 60.0, "AL/track_error_48h_nm": 50.0}
    assert verified_basins(values, PRIMARY) == ()


def test_the_tags_say_what_was_trained_on_and_what_is_verified():
    metrics = by_basin(60.0, AL=(50.0, 140.0), EP=(150.0, 120.0))
    assert basin_tags(metrics) == {"trained_basins": "AL,EP", "verified_basins": "AL"}


def test_a_basin_validated_but_never_trained_on_is_not_verified():
    """Storms in the archive, fields never cached: validation happened to
    find a few, training none. It didn't train there, so it isn't verified
    there, however the few scored."""
    metrics = by_basin(60.0, AL=(50.0, 140.0), EP=(90.0, 120.0))
    values = dict(metrics.values)
    del values["EP/train_samples"]
    tags = basin_tags(metric_set(**values))
    assert tags == {"trained_basins": "AL", "verified_basins": "AL"}
    # The predicate promotion reads agrees with the tag.
    assert verified_basins(values, PRIMARY) == ("AL",)


def test_validating_well_in_an_untrained_basin_earns_no_allowance():
    """Promotion reads the same predicate as the tags: a basin the
    candidate never trained on can't buy it a worse Atlantic score."""
    incumbent = metric_set(**{PRIMARY: 50.0})
    candidate = by_basin(48.0, AL=(52.0, 140.0), EP=(45.0, 120.0))
    values = dict(candidate.values)
    del values["EP/train_samples"]
    decision = evaluate_promotion(
        "lstm", complete_run(), metric_set(**values), incumbent_val_metrics=incumbent,
    )
    assert not decision.promote_to_staging
    assert not any("newly verified" in r for r in decision.reasons)


def test_a_run_from_before_the_counts_sets_no_basin_tags():
    assert basin_tags(metric_set(**{PRIMARY: 60.0})) == {}


# ---- what is served as in distribution ------------------------------------------


def _champions(reg: ModelRegistry, tags_by_model: dict[str, dict[str, str] | None]) -> None:
    for name in GROUP1_MODELS:
        v = reg.register(
            name, run_id=f"run-{name}", input_flavor=Flavor.GDAS_FINETUNE,
            metrics={PRIMARY: 50.0}, tags=tags_by_model.get(name),
        )
        reg.transition(name, v.version, Stage.PRODUCTION)


def test_no_champion_or_champions_from_before_the_tag_are_the_atlantic(tmp_path: Path):
    assert ModelRegistry(tmp_path / "a").verified_basins() == frozenset({"AL"})
    reg = ModelRegistry(tmp_path / "b")
    _champions(reg, {})
    assert reg.verified_basins() == frozenset({"AL"})
    # Trained on more, but from before verification was recorded: still the Atlantic.
    reg = ModelRegistry(tmp_path / "c")
    _champions(reg, {name: {"trained_basins": "AL,EP"} for name in GROUP1_MODELS})
    assert reg.verified_basins() == frozenset({"AL"})


def test_a_basin_is_served_once_every_champion_is_verified_in_it(tmp_path: Path):
    reg = ModelRegistry(tmp_path)
    tags = {
        name: {"trained_basins": "AL,CP,EP", "verified_basins": "AL,EP"} for name in GROUP1_MODELS
    }
    # One model trained on the Eastern Pacific without beating persistence there.
    tags[GROUP1_MODELS[2]] = {"trained_basins": "AL,CP,EP", "verified_basins": "AL"}
    _champions(reg, tags)
    assert reg.trained_basins() == frozenset({"AL", "CP", "EP"})
    assert reg.verified_basins() == frozenset({"AL"})

    v = reg.register(
        GROUP1_MODELS[2], run_id="rerun", input_flavor=Flavor.GDAS_FINETUNE,
        metrics={PRIMARY: 45.0},
        tags={"trained_basins": "AL,CP,EP", "verified_basins": "AL,EP"},
    )
    assert reg.verified_basins() == frozenset({"AL"})  # registered, not yet serving
    reg.transition(GROUP1_MODELS[2], v.version, Stage.PRODUCTION)
    assert reg.verified_basins() == frozenset({"AL", "EP"})


def test_a_champion_verified_nowhere_serves_no_basin_as_in_distribution(tmp_path: Path):
    """An empty tag is not a missing one: it trained, and beat persistence
    nowhere."""
    reg = ModelRegistry(tmp_path)
    tags = {name: {"trained_basins": "AL", "verified_basins": "AL"} for name in GROUP1_MODELS}
    tags[GROUP1_MODELS[0]] = {"trained_basins": "AL", "verified_basins": ""}
    _champions(reg, tags)
    assert reg.verified_basins() == frozenset()


# ---- promotion: the reference basin ---------------------------------------------


def test_candidates_are_compared_on_the_reference_basin_not_the_mix():
    """The Eastern Pacific's storms pull the overall error down; on the
    Atlantic the candidate is worse than the incumbent."""
    incumbent = by_basin(52.0, AL=(52.0, 140.0), EP=(40.0, 120.0))
    candidate = by_basin(47.0, AL=(55.0, 140.0), EP=(38.0, 120.0))
    decision = evaluate_promotion(
        "lstm", complete_run(), candidate, incumbent_val_metrics=incumbent,
    )
    assert not decision.promote_to_staging
    assert any(
        "(AL): candidate 55.00 vs incumbent 52.00 [not better]" in r for r in decision.reasons
    )

    better = by_basin(60.0, AL=(50.0, 140.0), EP=(75.0, 120.0))  # worse overall, better there
    assert evaluate_promotion(
        "lstm", complete_run(), better, incumbent_val_metrics=incumbent,
    ).promote_to_staging


def test_an_incumbent_from_before_basins_were_scored_is_all_reference_basin():
    """Every such version trained and validated on the Atlantic alone, so
    its overall error is its Atlantic error."""
    incumbent = metric_set(**{PRIMARY: 52.0})
    candidate = by_basin(45.0, AL=(51.0, 140.0))
    decision = evaluate_promotion(
        "lstm", complete_run(), candidate, incumbent_val_metrics=incumbent,
    )
    assert decision.promote_to_staging
    assert any("(AL): candidate 51.00 vs incumbent 52.00 [better]" in r for r in decision.reasons)


def test_a_candidate_verified_in_a_new_basin_may_be_slightly_worse_on_the_reference():
    incumbent = metric_set(**{PRIMARY: 50.0})  # Atlantic only
    within = by_basin(48.0, AL=(52.0, 140.0), EP=(45.0, 120.0))  # 4% worse on the Atlantic
    decision = evaluate_promotion("lstm", complete_run(), within, incumbent_val_metrics=incumbent)
    assert decision.promote_to_staging
    assert any("newly verified in ['EP']" in r for r in decision.reasons)
    assert any("[within the allowance]" in r for r in decision.reasons)

    beyond = by_basin(48.0, AL=(53.0, 140.0), EP=(45.0, 120.0))  # 6% worse
    assert not evaluate_promotion(
        "lstm", complete_run(), beyond, incumbent_val_metrics=incumbent,
    ).promote_to_staging
    # The allowance is the caller's to set.
    assert evaluate_promotion(
        "lstm", complete_run(), beyond, incumbent_val_metrics=incumbent, new_basin_tolerance=0.10,
    ).promote_to_staging


def test_the_allowance_is_only_for_a_basin_the_candidate_is_verified_in():
    """Trained on the Eastern Pacific but no better than persistence there:
    nothing was gained, so the Atlantic must improve outright."""
    incumbent = metric_set(**{PRIMARY: 50.0})
    candidate = by_basin(48.0, AL=(51.0, 140.0), EP=(130.0, 120.0))
    assert not evaluate_promotion(
        "lstm", complete_run(), candidate, incumbent_val_metrics=incumbent,
    ).promote_to_staging


def test_the_allowance_is_not_repeated_once_the_basin_is_covered():
    """Both verified in the same basins: outright better, as before --
    otherwise each retrain could give the Atlantic away a little more."""
    incumbent = by_basin(50.0, AL=(50.0, 140.0), EP=(45.0, 120.0))
    candidate = by_basin(50.0, AL=(51.0, 140.0), EP=(40.0, 120.0))
    assert not evaluate_promotion(
        "lstm", complete_run(), candidate, incumbent_val_metrics=incumbent,
    ).promote_to_staging


def test_a_candidate_that_loses_a_verified_basin_is_refused():
    """Better on the Atlantic, but no longer better than persistence in the
    Eastern Pacific, where the incumbent is: promoting it would quietly
    take that basin out of distribution."""
    incumbent = by_basin(50.0, AL=(50.0, 140.0), EP=(45.0, 120.0))
    candidate = by_basin(45.0, AL=(44.0, 140.0), EP=(125.0, 120.0))
    decision = evaluate_promotion(
        "lstm", complete_run(), candidate, incumbent_val_metrics=incumbent,
    )
    assert not decision.promote_to_staging
    assert any("no longer better than persistence in ['EP']" in r for r in decision.reasons)

    # The same for the reference basin against an older, Atlantic-only incumbent.
    atlantic_lost = by_basin(45.0, AL=(145.0, 140.0), EP=(45.0, 120.0))
    assert not evaluate_promotion(
        "lstm", complete_run(), atlantic_lost, incumbent_val_metrics=metric_set(**{PRIMARY: 150.0}),
    ).promote_to_staging


def test_the_thresholds_are_read_on_the_reference_basin():
    """They are NHC's Atlantic figures; a mix with an easier basin would
    pass a candidate that misses them on the Atlantic."""
    candidate = by_basin(60.0, AL=(80.0, 140.0), EP=(40.0, 120.0))
    decision = evaluate_promotion("lstm", complete_run(), candidate)
    assert any(r.startswith("track_error_48h_nm=80.000 <= 70.000 [FAIL]") for r in decision.reasons)


def test_a_reference_metric_missing_is_missing_not_another_basins_number():
    """No Atlantic storm long enough for 120 h, but Pacific ones: the
    Atlantic 120 h threshold is missing, not read off the Pacific."""
    values = dict(by_basin(60.0, AL=(50.0, 140.0), EP=(40.0, 120.0)).values)
    values["track_error_120h_nm"] = 100.0  # overall: the Pacific's alone
    values["EP/track_error_120h_nm"] = 100.0
    decision = evaluate_promotion("lstm", complete_run(), metric_set(**values))
    assert "track_error_120h_nm: missing [FAIL]" in decision.reasons
    assert not decision.promote_to_production


def test_a_candidate_with_no_reference_basin_storms_is_not_compared_on_others():
    incumbent = metric_set(**{PRIMARY: 50.0})
    candidate = by_basin(30.0, EP=(30.0, 120.0))
    decision = evaluate_promotion(
        "lstm", complete_run(), candidate, incumbent_val_metrics=incumbent,
    )
    assert not decision.promote_to_staging
    assert any("has no AL validation storms" in r for r in decision.reasons)


def test_a_candidate_that_scored_no_basin_is_judged_as_before():
    incumbent = metric_set(**{PRIMARY: 50.0})
    decision = evaluate_promotion(
        "lstm", complete_run(), metric_set(**{PRIMARY: 49.0}), incumbent_val_metrics=incumbent,
    )
    assert decision.promote_to_staging
    assert any(r == "track_error_48h_nm: candidate 49.00 vs incumbent 50.00 [better]"
               for r in decision.reasons)


# ---- the basin as a model input --------------------------------------------------


def test_columns_never_trained_on_are_blanked_once_for_latents_and_serving():
    """Resolved on the artifacts before anything reads them -- the joint
    latents fusion/diffusion train on and the tag serving builds from --
    so the two can't disagree (docs/multi_basin.md)."""
    from types import SimpleNamespace

    from anemoi.data.basins import TRAINING_BASINS
    from anemoi.tracking.experiment_tracking import basin_input_tags, basin_inputs
    from anemoi.training.real_run import RunArtifacts

    assert served_columns(("AL", "EP", "CP"), ("AL", "EP")) == ("AL", "EP", "")
    artifacts = RunArtifacts(model=None, basins=("AL", "EP", "CP"))
    trained_on_al = metric_set(**{PRIMARY: 50.0, "AL/train_samples": 9.0, "AL/val_samples": 3.0})
    resolved = resolve_basin_inputs(artifacts, trained_on_al)
    assert resolved.basins == ("AL", "", "")
    assert resolve_basin_inputs(artifacts, metric_set(**{PRIMARY: 50.0})) is artifacts
    # Tagged with their order and count, blanks included, and read back as is.
    tags = basin_input_tags(resolved)
    assert tags == {"basin_inputs": "AL,,"}
    assert basin_inputs(tags) == ("AL", "", "")
    assert basin_inputs({}) == ()  # a version from before the basin input
    # One configured basin, never trained on: still one column.
    assert basin_inputs(basin_input_tags(SimpleNamespace(basins=("",)))) == ("",)
    # PINN's candidate keeps its own columns.
    pinn = SimpleNamespace(basins=("AL", "", ""), candidate_basins=("AL", "EP", "CP"))
    pinn_tags = basin_input_tags(pinn)
    assert basin_inputs(pinn_tags, "candidate_basin_inputs") == ("AL", "EP", "CP")
    assert len(TRAINING_BASINS) == 3


def test_the_basin_input_builders_add_one_column_or_channel_per_basin():
    from anemoi.training.basin_input import (
        with_basin_channels,
        with_basin_columns,
        with_basin_vector,
    )

    basins = ("AL", "EP", "CP")
    rows = with_basin_columns(np.zeros((4, 5)), "EP012024", basins)
    assert rows.shape == (4, 8) and (rows[:, 5:] == [0, 1, 0]).all()
    planes = with_basin_channels(np.zeros((10, 9, 9)), "CP012024", basins)
    assert planes.shape == (13, 9, 9) and planes[12].min() == 1.0 and planes[10:12].max() == 0.0
    vec = with_basin_vector(np.zeros(6), "WP012024", basins)  # a basin it has no column for
    assert vec.shape == (9,) and not vec.any()
    # No basins: unchanged, as every version before the basin input was built.
    x = np.ones((4, 5))
    assert with_basin_columns(x, "AL012024", ()) is x
