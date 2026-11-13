"""Operational guidance on the registry's validation windows
(`training.baseline_backtest`), and the torch-free enumeration it shares
with training (`training.real_latents.joint_stage_windows`).

A constructed HURDAT2 spans 2021-2025, so Stage B's split puts 2024 in
validation, as the real archive does. The a-decks are written from the
best track with a known offset per technique (OFCL 0.1 deg north, AVNI
0.2, ...), so every mean error is known in advance. Nothing here needs
torch or the network.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data.atcf import parse_adeck
from anemoi.data.hurdat2 import parse_hurdat2, parse_hurdat2_statuses
from anemoi.data.nhc_verification import OfficialErrors
from anemoi.data.sources import Flavor
from anemoi.metrics.basin import per_basin_scores
from anemoi.metrics.homogeneous import INTENSITY, TRACK
from anemoi.training import real_latents
from anemoi.training.baseline_backtest import (
    DEFAULT_TECHNIQUES,
    PERSISTENCE,
    BaselineBacktestError,
    RegisteredError,
    TechniqueSpec,
    ValidationForecasts,
    assemble_validation_forecasts,
    format_forecast_check,
    format_report,
    group1_versions_of,
    model_members,
    reconcile_official_errors,
    run_baseline_backtest,
    technique_member,
    techniques_to_read,
    validation_cases,
    validation_tracks,
)
from anemoi.training.real_latents import GROUP1_ORDER, JointLatentSamples, joint_stage_windows
from anemoi.training.real_run import displacements_to_absolute, persistence_of, validation_metrics

#: One degree of latitude, in nm, on the sphere `geo.haversine_nm` uses.
NM_PER_DEG = 6371.0088 / 1.852 * np.pi / 180.0
RADII = ", ".join(["-999"] * 12)
LEADS = (12, 24, 36, 48, 72, 96, 120)


def storm_text(
    storm_id: str, start: datetime, n: int, *, lat0: float = 15.0, lon0: float = -50.0,
    statuses: dict[int, str] | None = None, no_pressure: tuple[int, ...] = (),
) -> str:
    """One HURDAT2 block: ``n`` six-hourly fixes moving north-west, TS
    unless ``statuses`` says otherwise; ``no_pressure`` rows carry -999,
    so the parser drops them and the track has a gap."""
    lines = [f"{storm_id},          TEST, {n:5d},"]
    for i in range(n):
        t = start + timedelta(hours=6 * i)
        lat, lon = lat0 + 0.3 * i, lon0 - 0.5 * i
        status = (statuses or {}).get(i, "TS")
        pressure = -999 if i in no_pressure else 1000 - i
        lines.append(
            f"{t:%Y%m%d}, {t:%H%M},  , {status}, {lat:4.1f}N, {-lon:5.1f}W, "
            f"{40 + 2 * i:3d}, {pressure:4d}, {RADII},"
        )
    return "\n".join(lines) + "\n"


def archive_text() -> str:
    return "".join([
        storm_text("AL012021", datetime(2021, 8, 1, tzinfo=UTC), 12),
        storm_text("AL012022", datetime(2022, 8, 1, tzinfo=UTC), 12),
        storm_text("EP012023", datetime(2023, 7, 1, tzinfo=UTC), 12, lon0=-110.0),
        # Validation (2024): a storm that starts as a low and ends extratropical,
        storm_text(
            "AL012024", datetime(2024, 8, 1, tzinfo=UTC), 18,
            statuses={0: "LO", 1: "LO", 15: "EX", 16: "EX", 17: "EX"},
        ),
        # one too short for any window,
        storm_text("AL022024", datetime(2024, 9, 1, tzinfo=UTC), 5),
        # one whose 9th row has no pressure, so later leads land 6 h late,
        storm_text(
            "EP012024", datetime(2024, 7, 1, tzinfo=UTC), 14, lon0=-110.0, no_pressure=(8,),
        ),
        # and a Central Pacific storm.
        storm_text("CP012024", datetime(2024, 8, 20, tzinfo=UTC), 10, lon0=-150.0),
        storm_text("AL012025", datetime(2025, 8, 1, tzinfo=UTC), 12),
    ])


@pytest.fixture(scope="module")
def archive():
    text = archive_text()
    return parse_hurdat2(text), parse_hurdat2_statuses(text)


@pytest.fixture(scope="module")
def cases(archive):
    tracks, statuses = archive
    return validation_cases(tracks, statuses)


#: technique -> (north offset in degrees, wind offset in kt or None).
OFFSETS = {
    "OFCL": (0.1, 2.0), "AVNI": (0.2, -3.0), "AVNO": (0.15, -6.0), "EMXI": (0.25, -4.0),
    "EMX2": (0.25, -4.0), "OCD5": (1.0, 5.0), "XTRP": (1.5, None),
}
OFCO_TIME = datetime(2024, 8, 3, 0, tzinfo=UTC)


def _row(basin: str, cy: str, t: datetime, tech: str, tau: int, lat: float, lon: float,
         wind: float | None, mslp: int = 0) -> str:
    lat_s = f"{round(lat * 10):d}{'N' if lat >= 0 else 'S'}"
    lon_s = f"{round(abs(lon) * 10):d}{'W' if lon < 0 else 'E'}"
    vmax = 0 if wind is None else round(wind)
    return (
        f"{basin}, {cy}, {t:%Y%m%d%H}, 03, {tech}, {tau:3d}, {lat_s:>5}, {lon_s:>6}, "
        f"{vmax:3d}, {mslp:4d}, XX,  34, NEQ,    0,    0,    0,    0,"
    )


def adeck_text(track, statuses) -> str:
    """Every technique's forecast for every initial time of ``track``,
    off the best track by `OFFSETS`. OFCL and OFCO only while the system
    is tropical, as NHC issues them; OFCO (the regular advisory a special
    one replaced) once, at `OFCO_TIME`, where OFCL is far off."""
    by_time = {f.valid_time: f for f in track.fixes}
    basin, cy = track.storm_id[:2], track.storm_id[2:4]
    rows = []
    for fix in track.fixes:
        t = fix.valid_time
        rows.append(_row(basin, cy, t, "CARQ", 0, fix.lat + 0.1, fix.lon, fix.max_wind_kt, 990))
        if t - timedelta(hours=6) in by_time:
            prev = by_time[t - timedelta(hours=6)]
            rows.append(_row(basin, cy, t, "CARQ", -6, prev.lat, prev.lon, prev.max_wind_kt))
        tropical = statuses[(track.storm_id, t)] in {"TD", "TS", "HU", "SD", "SS"}
        for tau in range(6, 127, 6):
            verif = by_time.get(t + timedelta(hours=tau))
            if verif is None:
                continue
            for tech, (dlat, dwind) in OFFSETS.items():
                if tech in ("OFCL",) and not tropical:
                    continue
                if tech == "EMXI" and t.hour in (0, 12) or tech == "EMX2" and t.hour in (6, 18):
                    continue
                if tech != "AVNO" and tau % 12:
                    continue
                wind = None if dwind is None else verif.max_wind_kt + dwind
                if tech == "OFCL" and t == OFCO_TIME:
                    rows.append(_row(basin, cy, t, "OFCO", tau, verif.lat + 0.05, verif.lon, wind))
                    rows.append(_row(basin, cy, t, "OFCL", tau, verif.lat + 2.0, verif.lon, wind))
                    continue
                rows.append(_row(basin, cy, t, tech, tau, verif.lat + dlat, verif.lon, wind))
    return "\n".join(rows) + "\n"


@pytest.fixture(scope="module")
def adecks(archive):
    tracks, statuses = archive
    return {
        t.storm_id: parse_adeck(adeck_text(t, statuses), t.storm_id)
        for t in validation_tracks(tracks)
    }


# --- the cases ---------------------------------------------------------------


def test_joint_stage_windows_names_the_validation_season_only_and_is_reproducible(archive):
    tracks, _ = archive
    train, val = joint_stage_windows(tracks, seed=7, n_augment=1)
    assert {w.storm_id[-4:] for w in train} == {"2021", "2022", "2023"}
    assert {w.storm_id for w in val} == {"AL012024", "EP012024", "CP012024"}
    _, again = joint_stage_windows(tracks, seed=7, n_augment=1)
    assert [w.current for w in again] == [w.current for w in val]


def test_a_longer_training_pass_keeps_the_cases_and_changes_the_working_fixes(archive):
    tracks, _ = archive
    train1, val1 = joint_stage_windows(tracks, seed=7, n_augment=1)
    train3, val3 = joint_stage_windows(tracks, seed=7, n_augment=3)
    assert len(train3) == 3 * len(train1)
    key = [(w.storm_id, w.current.valid_time) for w in val1]
    assert key == [(w.storm_id, w.current.valid_time) for w in val3]
    assert [w.current.lat for w in val1] != [w.current.lat for w in val3]


def _window_key(window) -> tuple:
    return (
        window.storm_id, window.current, window.window,
        window.y.tobytes(), window.mask.tobytes(),
    )


def test_the_latents_extraction_runs_the_models_on_joint_stage_windows_own_windows(
    archive, monkeypatch, tmp_path,
):
    """What ties the baseline's cases to training's: `extract_joint_latents`
    (and its validation half) hand the models exactly the windows
    `joint_stage_windows` names, in its order, with its working fixes."""
    tracks, _ = archive
    seen: list[list] = []

    def record(windows, trained_artifacts, gdas_cache_dir, device=None):
        seen.append(list(windows))
        return len(seen)

    monkeypatch.setattr(real_latents, "_extract_for_tracks", record)
    artifacts = {name: object() for name in GROUP1_ORDER}
    train, val = joint_stage_windows(tracks, seed=7, n_augment=2)
    assert train and val

    bundle = real_latents.extract_joint_latents(tracks, artifacts, tmp_path, seed=7, n_augment=2)
    assert (bundle.train, bundle.val) == (1, 2)
    assert [_window_key(w) for w in seen[0]] == [_window_key(w) for w in train]
    assert [_window_key(w) for w in seen[1]] == [_window_key(w) for w in val]

    only_val = real_latents.extract_validation_latents(
        tracks, artifacts, tmp_path, seed=7, n_augment=2,
    )
    assert only_val == 3 and len(seen) == 3
    assert [_window_key(w) for w in seen[2]] == [_window_key(w) for w in val]

    with pytest.raises(ValueError, match="missing trained Group 1"):
        real_latents.extract_validation_latents(tracks, {"lstm": object()}, tmp_path)


def test_cases_start_at_each_storms_fifth_fix_and_verify_against_the_best_track(
    archive, cases,
):
    tracks, _ = archive
    finals = {t.storm_id: t for t in tracks}
    assert set(cases.storm_ids) == {"AL012024", "EP012024", "CP012024"}
    assert cases.seasons == (2024, 2024) and cases.n_augment == 1
    first = cases.storm_ids.index("AL012024")
    assert cases.init_times[first] == finals["AL012024"].fixes[4].valid_time
    for i in (first, len(cases) - 1):
        track = finals[cases.storm_ids[i]]
        idx = [f.valid_time for f in track.fixes].index(cases.init_times[i])
        best = track.fixes[idx]
        assert (cases.best_lat[i], cases.best_lon[i]) == (best.lat, best.lon)
        for li, step in enumerate((2, 4, 6, 8, 12, 16, 20)):
            if not cases.mask[i, li]:
                assert idx + step >= len(track.fixes)
                continue
            target = track.fixes[idx + step]
            assert cases.obs_abs[i, li, 0] == pytest.approx(target.lat, abs=1e-9)
            assert cases.obs_abs[i, li, 1] == pytest.approx(target.lon, abs=1e-9)
            assert cases.obs_abs[i, li, 2] == target.max_wind_kt


def test_the_working_fixes_and_persistence_are_the_latents_tasks(archive, cases):
    tracks, _ = archive
    _, windows = joint_stage_windows(tracks, seed=20260806, n_augment=1)
    assert [w.current.lat for w in windows] == list(cases.base_lat)
    expected = displacements_to_absolute(
        persistence_of(windows), cases.base_lat[:, None], cases.base_lon[:, None],
    )
    np.testing.assert_allclose(cases.persistence_abs, expected)
    # and the noise is real: the base is not the best-track fix
    assert np.abs(cases.base_lat - cases.best_lat).max() > 0.0


def test_a_gap_in_the_best_track_is_flagged_not_raised(cases):
    ep = np.array([s == "EP012024" for s in cases.storm_ids])
    al = np.array([s == "AL012024" for s in cases.storm_ids])
    assert (cases.mask & ~cases.time_ok)[ep].any()  # leads across the gap land late
    assert not (cases.mask & ~cases.time_ok)[al].any()


def test_tropical_mask_needs_a_tropical_system_at_both_times(cases):
    tropical = cases.tropical_mask()
    al = [i for i, s in enumerate(cases.storm_ids) if s == "AL012024"]
    # AL012024's fixes 15-17 are EX: a 12 h lead from fix 13 verifies at 15.
    i13 = al[13 - 4]
    assert cases.init_status[i13] == "TS" and cases.verif_status[i13][0] == "EX"
    assert not tropical[i13, 0]
    assert tropical[al[0], 0]  # fix 4 to fix 6: both TS
    assert cases.basins == ("AL", "CP", "EP")


# --- the members -------------------------------------------------------------


def test_technique_specs():
    assert TechniqueSpec.parse("AVNI") == TechniqueSpec("AVNI", ("AVNI",), 0)
    official = TechniqueSpec.parse("OFCL=OFCO/OFCL")
    assert (official.name, official.techniques, official.kind) == (
        "OFCL", ("OFCO", "OFCL"), "official",
    )
    lagged = TechniqueSpec.parse("AVNO-6")
    assert (lagged.name, lagged.lag_hours, lagged.kind) == ("AVNO-6", 6, "lagged")
    assert TechniqueSpec.parse("EMXI=EMXI/EMX2").kind == "early"
    assert TechniqueSpec.parse("HWFI").kind == "guidance"
    for bad in ("avni", "AVNO-5", "OFCL=", "TOOLONG"):
        with pytest.raises(BaselineBacktestError):
            TechniqueSpec.parse(bad)
    assert {"OFCO", "OFCL", "AVNI", "CARQ", "EMX2"} <= techniques_to_read(DEFAULT_TECHNIQUES)


def test_the_official_member_prefers_the_regular_advisory(cases, adecks):
    member, used = technique_member(TechniqueSpec.parse("OFCL=OFCO/OFCL"), cases, adecks)
    i = cases.index()[("AL012024", OFCO_TIME)]
    assert member.pred_abs[i, 0, 0] == pytest.approx(cases.obs_abs[i, 0, 0] + 0.05, abs=0.051)
    assert used["AL"]["OFCO"] == 1
    j = cases.index()[("AL012024", OFCO_TIME + timedelta(hours=6))]
    assert member.pred_abs[j, 0, 0] == pytest.approx(cases.obs_abs[j, 0, 0] + 0.1, abs=0.051)


def test_a_lagged_member_reads_the_earlier_run_at_the_same_valid_time(cases, adecks):
    lagged, _ = technique_member(TechniqueSpec.parse("AVNO-6"), cases, adecks)
    i = cases.index()[("AL012024", OFCO_TIME)]
    adeck = adecks["AL012024"]
    point = adeck.get("AVNO", OFCO_TIME - timedelta(hours=6), 18)
    assert (lagged.pred_abs[i, 0, 0], lagged.pred_abs[i, 0, 1]) == (point.lat, point.lon)


def test_a_case_without_an_adeck_has_no_technique_forecast(cases, adecks):
    without = {k: v for k, v in adecks.items() if k != "CP012024"}
    member, used = technique_member(TechniqueSpec.parse("AVNI"), cases, without)
    cp = np.array([s == "CP012024" for s in cases.storm_ids])
    assert np.isnan(member.pred_abs[cp]).all()
    assert "CP" not in used


# --- the report --------------------------------------------------------------


@pytest.fixture(scope="module")
def report(archive, adecks):
    tracks, statuses = archive
    return run_baseline_backtest(
        tracks, statuses, adecks,
        registered=[RegisteredError.parse("fusion:AL:12=40")],
    )


def _row_of(report, sample, basin, lead, quantity=TRACK):
    return report.row(sample, basin, lead, quantity)


def test_samples_a_b_c_shrink_in_turn_and_errors_are_the_known_offsets(report, cases):
    a, b, c = (_row_of(report, s, "AL", 12) for s in "ABC")
    assert a.n_cases == report.registry_sample["AL"]["n_by_lead"]["12"]
    assert a.n_cases > b.n_cases > c.n_cases > 0
    assert set(a.scores) == {"persistence", "persistence_besttrack"}
    assert {"OFCL", "AVNI", "AVNO-6", "AVNO", "EMXI", "OCD5", "XTRP"} <= set(b.scores)
    assert b.scores["AVNI"].mean_error == pytest.approx(0.2 * NM_PER_DEG, rel=1e-6)
    assert c.scores["OCD5"].mean_error == pytest.approx(1.0 * NM_PER_DEG, rel=1e-6)
    assert _row_of(report, "B", "AL", 12, INTENSITY).scores["OFCL"].bias == pytest.approx(2.0)
    assert "XTRP" not in _row_of(report, "B", "AL", 12, INTENSITY).scores  # track only
    # The registry's own persistence on A is what it registers per basin.
    expected = per_basin_scores(
        cases.persistence_abs, cases.obs_abs, cases.mask, cases.storm_ids, LEADS,
        prefix="persistence_",
    )
    assert report.registry_sample["AL"]["persistence_track_error_nm"]["12"] == pytest.approx(
        expected["AL/persistence_track_error_12h_nm"]
    )
    # B leaves out the EP leads that verify late across the best-track gap.
    assert report.registry_sample["EP"]["n_verifying_fix_not_at_lead"] > 0
    assert report.official_errors == [] and report.reconciliation is None


def test_too_few_storms_is_said_in_every_row_of_a_one_storm_basin(report):
    cp = [r for r in report.results if r.basin == "CP" and r.n_cases]
    assert cp and all(r.too_few_storms and r.n_storms == 1 for r in cp)
    assert all(score.skill_pct is None for r in cp for score in r.scores.values())


def test_the_sample_gap_bounds_a_registered_error_by_hand(report):
    (gap,) = [g for g in report.sample_gap if (g["basin"], g["lead_hours"]) == ("AL", 12)]
    n_a = gap["n_A"]
    sub = gap["subsets"]["B"]
    n_b = sub["n"]
    assert n_a - n_b == sub["n_excluded"] > 0
    assert sum(sub["excluded_initial_status"].values()) == sub["n_excluded"]
    (bound,) = sub["registered_model_bounds"]
    assert bound["max_mean_on_subset"] == pytest.approx(40.0 * n_a / n_b)
    ofcl_on_b = _row_of(report, "B", "AL", 12).scores["OFCL"].mean_error
    assert bound["mean_error_needed_on_excluded_to_tie"]["OFCL"] == pytest.approx(
        (40.0 * n_a - ofcl_on_b * n_b) / (n_a - n_b)
    )
    assert set(gap["subsets"]) == {"B", "C"}
    assert gap["subsets"]["C"]["n"] <= n_b


def test_the_report_serialises_as_strict_json_and_prints_a_table(report):
    body = json.loads(report.to_json())
    assert body["kind"] == "homogeneous_baseline" and body["seed"] == 20260806
    assert body["n_augment"] == 1 and set(body["samples"]) == {"A", "B", "C"}
    assert len(body["results"]) == len(report.results)
    assert "NaN" not in report.to_json()
    text = format_report(report)
    assert "=== AL:" in text and "sample C, track error (nm)" in text
    assert "fewer than 8 storms" in text
    assert "No model forecasts given" in text


# --- NHC's own verification --------------------------------------------------


def test_reconciliation_reproduces_nhcs_errors_and_says_why_cases_differ(archive, adecks):
    tracks, statuses = archive
    val = validation_tracks(tracks)
    published = {}
    for track in (t for t in val if t.storm_id.startswith("AL")):
        by_time = {f.valid_time: f for f in track.fixes}
        for fix in track.fixes:
            verif = by_time.get(fix.valid_time + timedelta(hours=12))
            if verif is None or fix.valid_time == OFCO_TIME:
                continue
            if {statuses[(track.storm_id, f.valid_time)] for f in (fix, verif)} == {"TS"}:
                published[(track.storm_id, fix.valid_time, 12)] = 0.1 * NM_PER_DEG
    # One forecast NHC verified and the a-deck has no tropical case for.
    published[("AL012024", datetime(2024, 8, 1, tzinfo=UTC), 12)] = 50.0
    official = {"AL": OfficialErrors(track_nm=published, intensity_kt={}, domain=None)}
    rec = reconcile_official_errors(val, statuses, adecks, official)
    lead = rec["AL"]["by_lead"]["12"]
    assert lead["n_common"] == len(published) - 1
    assert lead["max_abs_diff_nm"] < 1e-6
    assert lead["n_only_in_nhc"] == 1
    assert lead["ours_not_counted_by_nhc"]["not_tropical_at_both_times"] >= 1
    assert lead["ours_not_counted_by_nhc"]["unexplained"] == 1  # the OFCO time
    assert rec["AL"]["storms_without_adeck"] == []


# --- the project's models: the per-case forecast file ------------------------


def _latents(cases, archive) -> JointLatentSamples:
    tracks, _ = archive
    _, windows = joint_stage_windows(tracks, seed=cases.seed, n_augment=cases.n_augment)
    n = len(cases)
    predictions = np.stack(
        [cases.obs_abs + [0.1 * (k + 1), 0.0, 1.0] for k in range(len(GROUP1_ORDER))], axis=1,
    )
    return JointLatentSamples(
        z=np.zeros((n, 5)), y=np.stack([w.y for w in windows]), mask=cases.mask,
        base_lat=cases.base_lat, base_lon=cases.base_lon, predictions=predictions,
        true_absolute=cases.obs_abs, context=np.zeros((n, 3)), latent_dims=(1,) * 5,
        storm_ids=cases.storm_ids, persistence=persistence_of(windows),
        valid_times=cases.init_times,
    )


def _registered(val: JointLatentSamples, fusion_abs: np.ndarray) -> dict:
    persistence_abs = displacements_to_absolute(
        val.persistence, val.base_lat[:, None], val.base_lon[:, None],
    )
    return {
        "fusion": validation_metrics(
            Flavor.GDAS_FINETUNE, fusion_abs, val.true_absolute, val.mask,
            val_storm_ids=val.storm_ids, persistence_abs=persistence_abs,
        ).values,
    }


def test_assembled_forecasts_check_themselves_against_the_registry(cases, archive):
    val = _latents(cases, archive)
    fusion_abs = cases.obs_abs + [0.05, 0.0, 0.5]
    registered = _registered(val, fusion_abs)
    file = assemble_validation_forecasts(
        val, fusion_abs, cases, versions={"fusion": 12}, latent_signature="sig",
        registered=registered,
    )
    assert file.consistent and file.header["n_without_forecast"] == 0
    assert file.header["same_hurdat2_as_training"] is None
    assert set(file.forecasts) == {*GROUP1_ORDER, "fusion", PERSISTENCE}
    assert any(k.endswith("val_samples") for k in file.header["registered"]["fusion"])
    off = {"fusion": {**registered["fusion"], "AL/track_error_48h_nm": 999.0}}
    bad = assemble_validation_forecasts(
        val, fusion_abs, cases, versions={}, latent_signature=None, registered=off,
        hurdat2={"hurdat2_sha256": "a"}, trained_on_hurdat2_sha256="b",
    )
    assert not bad.consistent and bad.header["same_hurdat2_as_training"] is False
    assert "not the file fusion was trained on" in format_forecast_check(bad)
    assert [c["metric"] for c in bad.header["failed_checks"]] == ["AL/track_error_48h_nm"]
    assert "MISMATCH AL/track_error_48h_nm" in format_forecast_check(bad)
    with pytest.raises(BaselineBacktestError):
        assemble_validation_forecasts(
            replace(val, valid_times=()), fusion_abs, cases, versions={},
            latent_signature=None, registered={},
        )


def test_the_forecast_file_round_trips_and_joins_only_its_own_cases(cases, archive, tmp_path):
    val = _latents(cases, archive)
    fusion_abs = cases.obs_abs + [0.05, 0.0, 0.5]
    file = assemble_validation_forecasts(
        val, fusion_abs, cases, versions={"fusion": 12}, latent_signature="sig",
        registered=_registered(val, fusion_abs),
    )
    path = tmp_path / "nested" / "forecasts.json"
    file.write(path)
    back = ValidationForecasts.read(path)
    assert back.storm_ids == file.storm_ids and back.init_times == file.init_times
    np.testing.assert_allclose(back.forecasts["fusion"], fusion_abs, atol=1e-4)
    members, n_without = model_members(cases, back, ["fusion", "lstm"])
    assert n_without == 0 and [m.name for m in members] == ["fusion", "lstm"]

    shifted = replace(back, base_lat=back.base_lat + 0.1)
    with pytest.raises(BaselineBacktestError, match="working fix"):
        model_members(cases, shifted, ["fusion"])
    moved = (back.init_times[0] - timedelta(days=30), *back.init_times[1:])
    unknown = replace(back, init_times=moved)
    with pytest.raises(BaselineBacktestError, match="not a validation window"):
        model_members(cases, unknown, ["fusion"])
    with pytest.raises(BaselineBacktestError, match="no \\['diffusion'\\]"):
        model_members(cases, back, ["diffusion"])


def test_a_case_without_a_model_forecast_is_excluded_and_counted(report, archive, adecks, cases):
    tracks, statuses = archive
    val = _latents(cases, archive)
    fusion_abs = cases.obs_abs + [0.05, 0.0, 0.5]
    file = assemble_validation_forecasts(
        val, fusion_abs, cases, versions={"fusion": 12}, latent_signature="sig",
        registered=_registered(val, fusion_abs),
    )
    keep = np.arange(1, len(file))  # training skipped the first window
    partial = replace(
        file, storm_ids=file.storm_ids[1:], init_times=file.init_times[1:],
        base_lat=file.base_lat[keep], base_lon=file.base_lon[keep],
        forecasts={k: v[keep] for k, v in file.forecasts.items()},
    )
    with_models = run_baseline_backtest(tracks, statuses, adecks, model_forecasts=partial)
    assert with_models.model_forecasts["n_without_model_forecast"] == 1
    first_storm = cases.storm_ids[0]
    a = with_models.row("A", first_storm[:2], 12, TRACK)
    assert a.scores["fusion"].mean_error == pytest.approx(0.05 * NM_PER_DEG, rel=1e-3)
    assert a.n_cases == _row_of(report, "A", first_storm[:2], 12).n_cases - 1
    b = with_models.row("B", "AL", 48, TRACK)
    assert "fusion" in b.paired and "AVNI" in b.paired["fusion"]
    assert not any("No per-case model forecasts" in note for note in with_models.notes)


def test_group1_versions_come_from_the_latent_signature():
    signature = "lstmv12-cnnv5-transformerv5-gnnv4-pinnv6"
    assert group1_versions_of(signature) == {
        "lstm": 12, "cnn": 5, "transformer": 5, "gnn": 4, "pinn": 6,
    }
    for bad in (None, "", "lstmv12-cnnv5", "lstmv12-cnnv5-transformerv5-gnnv4-pinnv6-x"):
        with pytest.raises(BaselineBacktestError):
            group1_versions_of(bad)


def test_registered_error_spec():
    assert RegisteredError.parse("fusion:AL:48=231") == RegisteredError("fusion", "AL", 48, 231.0)
    with pytest.raises(BaselineBacktestError):
        RegisteredError.parse("fusion AL 48 231")
