"""CLI wiring for era5-cache/gdas-cache (#22): each must select the right
data.splits boundary scheme -- ERA5 keeps the default (Stage A wants the
full 1980-2025 window), GDAS uses STAGE_B_BOUNDARIES (its real archive only
starts 2021, with zero overlap against the default train window). Exercised
directly against the cmd_* functions with monkeypatched fetch/parse so no
real network or HURDAT2 file is needed.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

from anemoi import cli
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.gridded_cache import FetchCacheReport
from anemoi.data.splits import STAGE_B_BOUNDARIES


def make_track(storm_id: str, season: int) -> Track:
    fix = Fix(
        storm_id=storm_id,
        valid_time=datetime(season, 8, 1, tzinfo=UTC),
        lat=20.0,
        lon=-60.0,
        max_wind_kt=60.0,
        min_pressure_mb=990.0,
        quality=TrackQuality.FINAL,
    )
    return Track(storm_id=storm_id, fixes=(fix,))


def make_args(tmp_path, **overrides) -> argparse.Namespace:
    defaults = dict(
        hurdat2="unused.txt",
        cache_dir=str(tmp_path),
        split="train",
        box_deg=10.0,
        max_workers=2,
        force=False,
        progress_every=0,
        sync_archive=False,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def _empty_report() -> FetchCacheReport:
    return FetchCacheReport(n_total=0, n_fetched=0, n_skipped=0)


def _spy_assign_splits(monkeypatch, captured: dict) -> None:
    import anemoi.data.splits as splits_module

    real_assign_splits = splits_module.assign_splits

    def spy(tracks_, boundaries=None):
        captured["boundaries"] = boundaries
        return real_assign_splits(tracks_, boundaries)

    monkeypatch.setattr(splits_module, "assign_splits", spy)


def test_cmd_gdas_cache_selects_stage_b_boundaries(tmp_path, monkeypatch):
    tracks = [make_track("AL01", 2021)]
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: tracks)
    monkeypatch.setattr(
        "anemoi.data.gdas_cache.run_fetch_cache", lambda tracks_, cache_dir, **kw: _empty_report()
    )
    captured: dict = {}
    _spy_assign_splits(monkeypatch, captured)

    assert cli.cmd_gdas_cache(make_args(tmp_path)) == 0
    assert captured["boundaries"] is STAGE_B_BOUNDARIES


def test_cmd_era5_cache_keeps_the_default_boundaries(tmp_path, monkeypatch):
    tracks = [make_track("AL01", 1985)]
    monkeypatch.setattr("anemoi.data.hurdat2.parse_hurdat2_file", lambda path: tracks)
    monkeypatch.setattr(
        "anemoi.data.era5_cache.run_fetch_cache", lambda tracks_, cache_dir, **kw: _empty_report()
    )
    captured: dict = {}
    _spy_assign_splits(monkeypatch, captured)

    assert cli.cmd_era5_cache(make_args(tmp_path)) == 0
    assert captured["boundaries"] is None  # cmd_era5_cache passes no override
