"""Retraining sees new seasons (#216).

Both images pinned the 1851-2023 HURDAT2, so no retrain ever saw a newer
season; the data-volume trigger counted a file that never changed; the
fixed split tables left Stage B's test seasons empty and made Stage A's test
season Stage B's validation season; training runs in the image logged no
commit; the noise emulator stayed on placeholders; and nothing ran the
skew audit.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.hurdat2_source import (
    INDEX_URL,
    PINNED_NAME,
    describe,
    fetch_latest_hurdat2,
    latest_name,
)
from anemoi.data.noise_calibration import as_issued, calibrate_season
from anemoi.data.sources import Flavor
from anemoi.data.splits import Split, assign_splits, season_boundaries

ROOT = Path(__file__).parents[1]

LISTING = """
<a href="hurdat2-1851-2022-050423.txt">x</a>
<a href="hurdat2-atl-1851-2023-042624.txt">x</a>
<a href="hurdat2-1851-2024-040425.txt">x</a>
<a href="hurdat2-1851-2024-052025.txt">x</a>
<a href="hurdat2-nepac-1949-2024-031725.txt">x</a>
"""


def test_the_newest_atlantic_release_is_picked():
    assert latest_name(LISTING) == "hurdat2-1851-2024-052025.txt"  # latest season, latest release
    assert latest_name("<a href='hurdat2-nepac-1949-2025-010126.txt'>") is None


def test_fetch_writes_the_file_and_a_manifest(tmp_path):
    files = {
        INDEX_URL: LISTING.encode(),
        INDEX_URL + "hurdat2-1851-2024-052025.txt": b"AL012024, X, 1,\n",
    }
    manifest = fetch_latest_hurdat2(tmp_path / "h.txt", fetch=files.__getitem__)
    assert (tmp_path / "h.txt").read_bytes() == b"AL012024, X, 1,\n"
    assert manifest["last_season"] == 2024 and manifest["fallback"] is False
    assert json.loads((tmp_path / "h.json").read_text())["file"] == "hurdat2-1851-2024-052025.txt"
    tags = describe(tmp_path / "h.txt")
    assert tags["hurdat2_file"] == "hurdat2-1851-2024-052025.txt"
    assert len(tags["hurdat2_sha256"]) == 64


def test_an_unreadable_listing_falls_back_to_the_pinned_file_and_says_so(tmp_path):
    def fetch(url):
        if url == INDEX_URL:
            raise OSError("403")
        return b"pinned"

    manifest = fetch_latest_hurdat2(tmp_path / "h.txt", fetch=fetch)
    assert manifest["file"] == PINNED_NAME
    assert manifest["fallback"] is True and "403" in manifest["fallback_reason"]


def test_no_file_at_all_raises(tmp_path):
    def fetch(url):
        raise OSError("offline")

    with pytest.raises(OSError):
        fetch_latest_hurdat2(tmp_path / "h.txt", fetch=fetch)


# ---- splits -----------------------------------------------------------------


def test_boundaries_move_with_the_archive():
    stage_a, stage_b = season_boundaries(2024)
    assert stage_b[Split.TRAIN] == (2021, 2022)
    assert stage_b[Split.VAL] == (2023, 2023)
    assert stage_b[Split.TEST] == (2024, 2024)
    assert stage_a[Split.TEST] == stage_b[Split.TEST]
    assert stage_a[Split.OPERATIONAL][0] == 2025
    # A new season becomes the test season; last year's moves to validation.
    _, next_b = season_boundaries(2025)
    assert next_b[Split.VAL] == (2024, 2024) and next_b[Split.TEST] == (2025, 2025)


@pytest.mark.parametrize("latest", [2023, 2024, 2025, 2030])
def test_stage_bs_validation_season_is_never_seen_by_stage_a(latest):
    """Promotion is decided on Stage B val; Stage A's test season used to be
    that same season (2023)."""
    stage_a, stage_b = season_boundaries(latest)
    b_val = stage_b[Split.VAL][0]
    for split, (lo, hi) in stage_a.items():
        assert not lo <= b_val <= hi, f"Stage A {split.value} contains Stage B's val season"
    # And nothing evaluated as test is trained or validated on in either stage.
    test = stage_b[Split.TEST][0]
    for bounds in (stage_a, stage_b):
        for split in (Split.TRAIN, Split.VAL):
            lo, hi = bounds[split]
            assert not lo <= test <= hi


def test_too_short_an_archive_is_refused():
    from anemoi.data.splits import MIN_LATEST_SEASON
    from anemoi.training.real_run import boundaries_for_tracks

    with pytest.raises(ValueError, match="through at least 2023"):
        season_boundaries(MIN_LATEST_SEASON - 1)
    # boundaries_for_tracks uses the same threshold: an archive just short of
    # it gets the fixed tables instead of season_boundaries' ValueError.
    short = [_track("AL012022", MIN_LATEST_SEASON - 1)]
    assert boundaries_for_tracks(Flavor.GDAS_FINETUNE, short)


def _track(storm_id, season, n=4, quality=TrackQuality.FINAL, start_hour=0):
    return Track(storm_id=storm_id, fixes=tuple(
        Fix(storm_id=storm_id,
            valid_time=datetime(season, 8, 1, start_hour, tzinfo=UTC) + timedelta(hours=6 * i),
            lat=20.0 + i, lon=-60.0 - i, max_wind_kt=50.0 + i, min_pressure_mb=1000.0 - i,
            quality=quality)
        for i in range(n)
    ))


def test_training_cuts_the_archive_it_is_given():
    from anemoi.training.real_run import boundaries_for_tracks

    tracks = [_track(f"AL01{s}", s) for s in (1990, 2020, 2021, 2022, 2023, 2024)]
    b = assign_splits(tracks, boundaries_for_tracks(Flavor.GDAS_FINETUNE, tracks))
    assert b.ids(Split.TRAIN) == ("AL012021", "AL012022")
    assert b.ids(Split.VAL) == ("AL012023",)
    # Was empty: the fixed table wanted 2024-25 from a 2023 file.
    assert b.ids(Split.TEST) == ("AL012024",)
    a = assign_splits(tracks, boundaries_for_tracks(Flavor.ERA5_PRETRAIN, tracks))
    assert a.ids(Split.TEST) == ("AL012024",)
    assert "AL012023" not in a.storms  # Stage B's val season: not Stage A's anything


# ---- noise calibration --------------------------------------------------------


def test_the_as_issued_bulletin_is_paired_with_the_final_fix():
    final = _track("AL092024", 2024, n=2)
    w0 = Fix(storm_id="AL092024", valid_time=final.fixes[0].valid_time, lat=20.1, lon=-60.0,
             max_wind_kt=55.0, min_pressure_mb=1000.0, quality=TrackQuality.WORKING)
    first_06 = Fix(storm_id="AL092024", valid_time=final.fixes[1].valid_time, lat=21.3, lon=-61.0,
                   max_wind_kt=51.0, min_pressure_mb=999.0, quality=TrackQuality.WORKING)
    corrected_06 = Fix(storm_id="AL092024", valid_time=final.fixes[1].valid_time, lat=21.0,
                       lon=-61.0, max_wind_kt=51.0, min_pressure_mb=999.0,
                       quality=TrackQuality.WORKING)
    assert as_issued([w0, first_06, corrected_06]) == [w0, first_06]

    result = calibrate_season({"AL092024": [w0, first_06, corrected_06]}, [final])
    assert result["n_pairs"] == 2 and result["storms"] == ["AL092024"]
    assert result["intensity_rms_kt"] == pytest.approx(((5.0**2 + 0.0**2) / 2) ** 0.5)
    assert result["position_rms_nm"] > 10  # the as-issued 0.3 deg error, not the corrected 0
    assert calibrate_season({}, [final]) is None


# ---- run tags -------------------------------------------------------------------


def test_run_tags_record_the_commit_split_and_trigger(monkeypatch):
    from anemoi import provenance
    from anemoi.tracking.experiment_tracking import build_run_tags, training_data_tags
    from anemoi.tracking.tags import Trigger
    from anemoi.training.curriculum import Curriculum

    provenance.git_sha.cache_clear()
    monkeypatch.setenv("ANEMOI_GIT_SHA", "abc1234")
    try:
        stage_b = Curriculum.standard("lstm").stages[-1]
        tags = build_run_tags("lstm", stage_b, latest_season=2024, trigger=Trigger.DATA_VOLUME)
    finally:
        provenance.git_sha.cache_clear()
    assert tags is not None  # was None in the image (no .git): no MLflow run was logged
    assert tags.git_commit == "abc1234"
    assert tags.trigger is Trigger.DATA_VOLUME
    assert tags.storm_split == "train-2021-2022_val-2023-2023"

    data = training_data_tags(None, [_track("AL012024", 2024)])
    assert data["hurdat2_last_season"] == "2024" and len(data["config_sha256"]) == 64


# ---- wiring -----------------------------------------------------------------------


def test_the_images_and_jobs_fetch_the_newest_hurdat2():
    dockerfile = (ROOT / "docker" / "multistage.Dockerfile").read_text()
    assert "hurdat2-atl-1851-2023-042624.txt" not in dockerfile
    assert dockerfile.count("anemoi hurdat2-fetch --out /app/data/") == 2
    entrypoint = (ROOT / "docker" / "cloud-run-training" / "entrypoint.sh").read_text()
    assert 'anemoi hurdat2-fetch --out "${HURDAT2_PATH}"' in entrypoint
    assert '--trigger "${TRIGGER}"' in entrypoint


def test_the_skew_audit_runs_after_every_cycle_in_the_api_container():
    """It existed as `anemoi skew-audit`, but nothing scheduled it. It runs
    as a bounded step of the cycle Workflow, in the image that served the
    cycles it replays (#216)."""
    workflow = (ROOT / "docker" / "api" / "src" / "cycleWorkflow.ts").read_text()
    assert "'skew audit'" in workflow
    assert "/v1/internal/skew-audit?max_records=" in workflow
    from anemoi.api.routers import internal

    assert any(r.path == "/internal/skew-audit" for r in internal.router.routes)


def test_the_internal_route_runs_a_bounded_pass(tmp_path, monkeypatch):
    import warnings

    pytest.importorskip("fastapi")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from fastapi.testclient import TestClient

    from anemoi.api import real_state

    radii = ", ".join(["-999"] * 12)
    hurdat2 = tmp_path / "h.txt"
    fix = f"20260901, 0000,  , TS, 20.0N,  60.0W,  40, 1005, {radii},"
    hurdat2.write_text(f"AL012026, T, 1,\n{fix}\n")
    monkeypatch.setenv("ANEMOI_API_REAL_STATE", "1")
    monkeypatch.setattr("anemoi.data.live_atcf.fetch_live_tracks", lambda: [])
    state = real_state.RealState(
        hurdat2_path=str(hurdat2), registry_root=str(tmp_path / "r"),
        checkpoint_store=object(), cache_dir=str(tmp_path / "g"),
    )
    calls = []

    def fake_audit_run(registry, store, cache_dir, root, *, max_records=None):
        calls.append(max_records)
        return {"n_audited": 2, "n_samples_added": 3, "n_remaining": 0}

    monkeypatch.setattr("anemoi.monitoring.skew_audit.audit_run", fake_audit_run)
    monkeypatch.setattr(real_state, "_REAL_STATE", state)
    from anemoi.api.main import app

    r = TestClient(app).post("/v1/internal/skew-audit?max_records=4")
    assert r.status_code == 200 and r.json()["n_samples_added"] == 3
    assert calls == [4]
