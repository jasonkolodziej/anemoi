"""Forecast-lead steering features (data.steering), offline."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data import steering
from anemoi.data.gridded_cache import FetchTask
from anemoi.data.real_gridded import GRID_NLAT, GRID_NLON

T = datetime(2023, 8, 29, 12, tzinfo=UTC)


def _uniform(u: float, v: float, du: float = 0.0, dv: float = 0.0) -> steering.LeadFlow:
    full = lambda x: np.full((GRID_NLAT, GRID_NLON), x, dtype=np.float32)  # noqa: E731
    return steering.LeadFlow(full(u), full(v), full(du), full(dv))


def test_dlm_weights_are_the_trapezoid_over_850_to_200():
    assert sum(steering.DLM_WEIGHTS) == 850 - 200
    assert len(steering.DLM_WEIGHTS) == len(steering.STEERING_LEVELS_HPA)


def test_lead_flow_weights_levels_and_takes_shear_as_200_minus_850():
    msgs = {}
    for p in steering.STEERING_LEVELS_HPA:
        msgs[("UGRD", p)] = np.full((GRID_NLAT, GRID_NLON), float(p))
        msgs[("VGRD", p)] = np.full((GRID_NLAT, GRID_NLON), 1.0)
    flow = steering.lead_flow(msgs)
    expected = sum(p * w for p, w in zip(steering.STEERING_LEVELS_HPA, steering.DLM_WEIGHTS,
                                         strict=True)) / 650.0
    assert flow.u_dlm[0, 0] == pytest.approx(expected)
    assert flow.v_dlm[0, 0] == pytest.approx(1.0)
    assert flow.u_shear[0, 0] == pytest.approx(200 - 850)
    assert flow.v_shear[0, 0] == pytest.approx(0.0)
    assert flow.u_dlm.dtype == np.float32


def test_lead_flow_refuses_another_grid():
    msgs = {(sn, p): np.zeros((10, 10)) for p in steering.STEERING_LEVELS_HPA
            for sn in ("UGRD", "VGRD")}
    with pytest.raises(ValueError, match="grid"):
        steering.lead_flow(msgs)


def test_disc_mean_of_a_constant_is_the_constant_and_ignores_nan():
    field = np.full((GRID_NLAT, GRID_NLON), 3.0)
    assert steering.disc_mean(field, 25.0, -80.0) == pytest.approx(3.0)
    field[400:, :] = np.nan  # south of -10: outside the disc
    assert steering.disc_mean(field, 25.0, -80.0) == pytest.approx(3.0)
    assert math.isnan(steering.disc_mean(np.full((GRID_NLAT, GRID_NLON), np.nan), 25.0, -80.0))


def test_disc_mean_only_sees_the_disc_and_wraps_at_greenwich():
    field = np.zeros((GRID_NLAT, GRID_NLON))
    lon_idx = np.arange(GRID_NLON) * 0.25
    field[:, (lon_idx > 20) & (lon_idx < 340)] = 100.0  # everything more than 20 deg from 0E
    assert steering.disc_mean(field, 10.0, 0.0) == pytest.approx(0.0)
    assert steering.disc_mean(field, 10.0, 359.0) == pytest.approx(0.0)
    assert steering.disc_mean(field, 10.0, -1.0) == pytest.approx(0.0)
    assert steering.disc_mean(field, 10.0, 180.0) == pytest.approx(100.0)


def test_disc_mean_is_symmetric_for_a_field_linear_in_longitude():
    """A field that rises eastward averages to its centre value over a disc."""
    lon = (np.arange(GRID_NLON) * 0.25)[None, :]
    field = np.broadcast_to(lon, (GRID_NLAT, GRID_NLON)).astype(float)
    assert steering.disc_mean(field, 0.0, 180.0) == pytest.approx(180.0, abs=1e-6)


def test_features_advect_with_the_flow_plus_beta_drift():
    flows = [_uniform(5.0, 0.0, 3.0, -2.0)] * len(steering.STEERING_LEADS_H)
    feats = steering.steering_features(flows, 20.0, -60.0, beta_drift_ms=(0.0, 0.0))
    assert feats.shape == (9, 6)
    assert feats[:, 0] == pytest.approx(5.0)
    assert feats[:, 2] == pytest.approx(3.0)
    assert feats[:, 3] == pytest.approx(-2.0)
    step_nm = 5.0 * 6 * 3600 / 1852.0
    assert feats[:, 4] == pytest.approx(step_nm * np.arange(9), rel=1e-5)
    assert feats[:, 5] == pytest.approx(0.0)
    drifted = steering.steering_features(flows, 20.0, -60.0, beta_drift_ms=(-1.0, 2.0))
    assert drifted[8, 4] == pytest.approx(4.0 * 6 * 3600 / 1852.0 * 8, rel=1e-5)
    assert drifted[8, 5] == pytest.approx(2.0 * 6 * 3600 / 1852.0 * 8, rel=1e-5)


def test_features_sample_each_lead_where_the_track_has_reached():
    """Lead 1's flow is 10 m/s everywhere west of 60.5W and 0 elsewhere: a
    start at 60W moving west gets there by lead 1, so lead 1 reads 10."""
    west = np.zeros((GRID_NLAT, GRID_NLON), dtype=np.float32)
    lon = np.arange(GRID_NLON) * 0.25
    west[:, lon < 360 - 66] = -10.0
    still = _uniform(-10.0, 0.0)
    marker = steering.LeadFlow(west, still.v_dlm * 0, still.u_shear, still.v_shear)
    flows = [still, marker] + [still] * 7
    feats = steering.steering_features(flows, 0.0, -60.0, beta_drift_ms=(0.0, 0.0),
                                       radius_deg=1.0)
    # 10 m/s for 6 h is 216 km, ~1.94 deg of longitude at the equator. From
    # 60W the lead-1 point is near 61.9W, whose 1-deg disc lies east of 66W
    # (reads 0); from 65.5W it is near 67.4W, whose disc lies west (reads -10).
    assert feats[1, 0] == pytest.approx(0.0)
    feats_west = steering.steering_features(flows, 0.0, -65.5, beta_drift_ms=(0.0, 0.0),
                                            radius_deg=1.0)
    assert feats_west[0, 0] == pytest.approx(-10.0)  # lead 0 reads the uniform flow
    assert feats_west[1, 0] == pytest.approx(-10.0)


def test_features_raise_where_there_is_no_flow():
    nan = _uniform(np.nan, np.nan)
    with pytest.raises(ValueError, match="no steering flow"):
        steering.steering_features([nan] * 9, 20.0, -60.0)


def test_cache_round_trip_and_vector(tmp_path):
    task = FetchTask(storm_id="AL102023", valid_time=T, lat=24.5, lon=-84.9)
    feats = np.arange(54, dtype=np.float32).reshape(9, 6)
    path = steering.steering_path(tmp_path, task.storm_id, T)
    steering.save_steering(path, feats, task)
    assert path.name == "2023082912.npz"
    assert np.array_equal(steering.load_steering(path), feats)
    vec = steering.steering_vector(tmp_path, "AL102023", T)
    assert vec.shape == (steering.STEERING_DIM,)
    assert steering.steering_vector(tmp_path, "AL102023", T + timedelta(hours=6)) is None
    bad = feats.copy()
    bad[3, 1] = np.nan
    steering.save_steering(path, bad, task)
    assert steering.steering_vector(tmp_path, "AL102023", T) is None


def test_meta_refuses_a_cache_written_with_other_settings(tmp_path, monkeypatch):
    steering.write_meta(tmp_path)
    steering.write_meta(tmp_path)  # same settings: fine
    monkeypatch.setattr(steering, "DISC_RADIUS_DEG", 4.0)
    with pytest.raises(ValueError, match="other settings"):
        steering.write_meta(tmp_path)


def test_fetch_reads_the_t_minus_6_run_at_each_lead(monkeypatch):
    urls = []
    monkeypatch.setattr(steering, "fetch_grib2_messages",
                        lambda url, targets, session=None: urls.append(url) or {
                            k: np.zeros((GRID_NLAT, GRID_NLON)) for _sn, _lv, k in targets})
    for lead in (0, 48):
        steering.fetch_lead_flow(T, lead)
    assert urls[0].endswith("gfs.20230829/06/atmos/gfs.t06z.pgrb2.0p25.f006")
    assert urls[1].endswith("gfs.20230829/06/atmos/gfs.t06z.pgrb2.0p25.f054")


def test_run_fetches_each_time_once_shares_it_and_skips_what_is_cached(tmp_path):
    t2 = T + timedelta(hours=6)
    tasks = [
        FetchTask("AL102023", T, 24.5, -84.9),
        FetchTask("AL112023", T, 15.0, -45.0),
        FetchTask("AL102023", t2, 25.5, -84.8),
    ]
    calls = []

    def fetch(t, lead):
        calls.append((t, lead))
        return _uniform(1.0, 2.0)

    report = steering.run_steering_cache(tasks, tmp_path, fetch=fetch, max_workers=2,
                                         progress_every=0)
    assert (report.n_times, report.n_written, report.n_failed) == (2, 3, 0)
    assert sorted(calls) == sorted((t, lead) for t in (T, t2) for lead in steering.STEERING_LEADS_H)
    calls.clear()
    again = steering.run_steering_cache(tasks, tmp_path, fetch=fetch, progress_every=0)
    assert (again.n_written, again.n_skipped, calls) == (0, 3, [])


def test_a_failed_time_is_reported_and_the_others_still_written(tmp_path):
    t2 = T + timedelta(hours=6)
    tasks = [FetchTask("AL102023", T, 24.5, -84.9), FetchTask("AL102023", t2, 25.5, -84.8)]

    def fetch(t, lead):
        if t == t2 and lead == 48:
            raise KeyError("UGRD:500 mb not found")
        return _uniform(1.0, 2.0)

    report = steering.run_steering_cache(tasks, tmp_path, fetch=fetch, progress_every=0)
    assert (report.n_written, report.n_failed) == (1, 1)
    assert "KeyError" in report.failures[0][1]


def test_shards_partition_the_times():
    times = [T + timedelta(hours=6 * i) for i in range(10)]
    shards = [steering.shard_times(times, i, 3) for i in range(3)]
    assert sorted(t for s in shards for t in s) == times
    with pytest.raises(ValueError):
        steering.shard_times(times, 3, 3)
