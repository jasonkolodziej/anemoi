"""The GFS vortex tracker (data.gfs_track), on synthetic vortices."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from anemoi.data import gfs_track as gt
from anemoi.data.besttrack import Fix, Track, TrackQuality
from anemoi.data.real_gridded import GRID_NLAT, GRID_NLON

T0 = datetime(2022, 9, 1, 12, tzinfo=UTC)
N = len(gt.TRACK_LEADS_H)


def field_with(*vortices: tuple[float, float], vmax: float = 25.0, depth_pa: float = 3000.0):
    """A resting atmosphere with a cyclonic vortex at each (lat, lon)."""
    u = np.zeros((GRID_NLAT, GRID_NLON), dtype=np.float32)
    v = np.zeros((GRID_NLAT, GRID_NLON), dtype=np.float32)
    p = np.full((GRID_NLAT, GRID_NLON), 101300.0, dtype=np.float32)
    half, rm = 40, 1.0  # cells either side; radius of maximum wind, degrees
    for lat, lon in vortices:
        i0, j0 = int(round((90 - lat) / 0.25)), int(round((lon % 360) / 0.25))
        rows = np.arange(i0 - half, i0 + half + 1)
        cols = np.arange(j0 - half, j0 + half + 1)
        dy = (90 - rows * 0.25)[:, None] - lat
        dx = ((cols * 0.25)[None, :] - (lon % 360)) * np.cos(np.radians(lat))
        r = np.hypot(dx, dy)
        speed = vmax * (r / rm) * np.exp(0.5 * (1 - (r / rm) ** 2))
        sign = 1.0 if lat >= 0 else -1.0
        safe = np.maximum(r, 1e-9)
        take = np.ix_(rows, cols % GRID_NLON)
        u[take] += (-sign * speed * dy / safe).astype(np.float32)
        v[take] += (sign * speed * dx / safe).astype(np.float32)
        p[take] -= (depth_pa * np.exp(-((r / 2.0) ** 2))).astype(np.float32)
    return gt.LeadField(u850=u, v850=v, mslp=p)


@pytest.mark.parametrize("lat, lon", [
    (20.1, -60.3),     # Atlantic
    (15.0, -179.9),    # across the dateline
    (12.4, 0.1),       # across Greenwich
    (-18.2, 120.0),    # southern hemisphere: cyclonic is the other sign
])
def test_locate_finds_the_centre_between_grid_points(lat, lon):
    fix = gt.locate(field_with((lat, lon)), lat + 0.8, lon - 0.9)
    assert fix is not None
    assert abs(fix[0] - lat) < 0.1
    assert abs(((fix[1] - lon + 180) % 360) - 180) < 0.1


def test_locate_searches_the_whole_disc_at_high_latitude():
    # At 60N a centre 6 deg of longitude east is 3 deg away on the ground:
    # inside the search radius, though further in degrees than it is wide.
    fix = gt.locate(field_with((60.0, -34.0)), 60.0, -40.0)
    assert fix is not None
    assert abs(fix[0] - 60.0) < 0.15 and abs(fix[1] + 34.0) < 0.3


def test_locate_is_none_in_a_resting_field_and_outside_the_radius():
    assert gt.locate(field_with(), 20.0, -60.0) is None
    far = field_with((20.0, -60.0))
    assert gt.locate(far, 20.0, -60.0 + gt.SEARCH_RADIUS_DEG + 3.0) is None


def test_locate_takes_the_vortex_nearer_the_guess_when_two_fixes_disagree():
    # A strong wind vortex with no pressure signal, and a pressure low
    # elsewhere: the two parameters point at different places.
    wind_only = field_with((20.0, -60.0), depth_pa=0.0)
    low_only = field_with((22.9, -60.0), vmax=0.0)
    both = gt.LeadField(
        u850=wind_only.u850, v850=wind_only.v850, mslp=low_only.mslp,
    )
    near_wind = gt.locate(both, 20.2, -60.0)
    near_low = gt.locate(both, 22.7, -60.0)
    assert abs(near_wind[0] - 20.0) < 0.15
    assert abs(near_low[0] - 22.9) < 0.15


def _moving(lat0, lon0, dlat, dlon, n=N, lost_from=None):
    for k in range(n):
        if lost_from is not None and k >= lost_from:
            yield field_with()
        else:
            yield field_with((lat0 + k * dlat, lon0 + k * dlon))


def test_a_moving_vortex_is_followed_through_every_lead():
    # 1.2 deg north and 2.4 deg west every 6 h: a fast, recurving storm.
    pos = gt.track_vortex(_moving(20.0, -60.0, 1.2, -2.4), 20.3, -59.7, 1.2, -2.4)
    want = np.array([[20.0 + k * 1.2, -60.0 - k * 2.4] for k in range(N)])
    assert np.abs(pos - want).max() < 0.1


def test_a_storm_that_stalls_is_still_found():
    # Moving 2.5 deg per step, then stationary: the guess overshoots by one
    # step's motion, inside the search radius.
    centres = [(20.0 + min(k, 4) * 2.5, -60.0) for k in range(N)]
    pos = gt.track_vortex((field_with(c) for c in centres), 20.0, -60.0, 2.5, 0.0)
    assert np.abs(pos - np.array(centres)).max() < 0.1


def test_the_track_ends_where_gfs_loses_the_storm_and_reading_stops():
    read = []

    def fields():
        for k, fld in enumerate(_moving(20.0, -60.0, 0.5, -0.5, lost_from=5)):
            read.append(k)
            yield fld

    pos = gt.track_vortex(fields(), 20.0, -60.0, 0.5, -0.5)
    assert np.isfinite(pos[:5]).all()
    assert np.isnan(pos[5:]).all()
    assert read == [0, 1, 2, 3, 4, 5]  # nothing fetched once the storm is lost


def test_no_vortex_at_the_cycle_is_no_track():
    pos = gt.track_vortex(_moving(20.0, -60.0, 0, 0, lost_from=0), 20.0, -60.0)
    assert np.isnan(pos).all()


def test_two_storms_share_the_fields_and_keep_their_own_tracks():
    def fields():
        for k in range(N):
            yield field_with((20.0 + 0.5 * k, -60.0), (15.0, -110.0 - 0.6 * k))

    tasks = [
        gt.TrackTask("AL01", T0, 20.0, -60.0, 0.5, 0.0),
        gt.TrackTask("EP01", T0, 15.0, -110.0, 0.0, -0.6),
    ]
    al, ep = gt.track_many(fields(), tasks)
    assert np.abs(al[-1] - [20.0 + 0.5 * (N - 1), -60.0]).max() < 0.1
    assert np.abs(ep[-1] - [15.0, -110.0 - 0.6 * (N - 1)]).max() < 0.1


def test_the_wrong_number_of_fields_is_refused():
    with pytest.raises(ValueError, match="fields for"):
        gt.track_vortex(_moving(20.0, -60.0, 0, 0, n=3), 20.0, -60.0)


def _track(storm_id="AL012022", n=4, gap_at=None) -> Track:
    fixes, t = [], T0
    for i in range(n):
        fixes.append(Fix(storm_id, t, 20.0 + 0.5 * i, -60.0 - 0.4 * i, 50.0, 1000.0,
                         quality=TrackQuality.FINAL))
        t += timedelta(hours=12 if gap_at == i else 6)
    return Track(storm_id=storm_id, fixes=tuple(fixes))


def test_tasks_carry_the_six_hour_motion_into_each_fix():
    tasks = gt.track_tasks([_track(gap_at=1)])
    assert (tasks[0].dlat_6h, tasks[0].dlon_6h) == (0.0, 0.0)  # a storm's first fix
    assert tasks[1].dlat_6h == pytest.approx(0.5) and tasks[1].dlon_6h == pytest.approx(-0.4)
    assert (tasks[2].dlat_6h, tasks[2].dlon_6h) == (0.0, 0.0)  # after a 12 h gap


def test_the_cache_writes_each_cycle_once_with_its_settings(tmp_path):
    track = _track(n=2)
    calls = []

    def fetch(t, lead):
        calls.append((t, lead))
        fix = next(f for f in track.fixes if f.valid_time == t)
        return field_with((fix.lat + 0.1 * lead / 6, fix.lon))

    report = gt.run_gfs_track_cache(gt.track_tasks([track]), tmp_path, fetch=fetch, max_workers=1)
    assert (report.n_written, report.n_failed, report.n_no_vortex) == (2, 0, 0)
    assert len(calls) == 2 * N
    assert json.loads((tmp_path / "_meta.json").read_text()) == gt.gfs_track_meta()
    gt.require_meta(tmp_path)
    pos = gt.cached_track(tmp_path, track.storm_id, T0)
    assert pos.shape == (N, 2) and abs(pos[-1, 0] - (20.0 + 0.1 * (N - 1))) < 0.1
    assert gt.cached_track(tmp_path, track.storm_id, T0 + timedelta(days=9)) is None

    again = gt.run_gfs_track_cache(gt.track_tasks([track]), tmp_path, fetch=fetch, max_workers=1)
    assert (again.n_written, again.n_skipped) == (0, 2)
    assert len(calls) == 2 * N  # nothing refetched


def test_a_cycle_whose_fields_cannot_be_fetched_is_reported_not_cached(tmp_path):
    def fetch(t, lead):
        raise OSError("404")

    report = gt.run_gfs_track_cache(gt.track_tasks([_track(n=1)]), tmp_path, fetch=fetch)
    assert (report.n_written, report.n_failed) == (0, 1)
    assert gt.cached_track(tmp_path, "AL012022", T0) is None


def test_a_cache_with_other_settings_is_refused(tmp_path):
    with pytest.raises(ValueError, match="no readable"):
        gt.require_meta(tmp_path)
    (tmp_path / "_meta.json").write_text(json.dumps({**gt.gfs_track_meta(), "smooth_cells": 9}))
    with pytest.raises(ValueError, match="other settings"):
        gt.require_meta(tmp_path)


def test_the_fetch_reads_the_run_six_hours_before_at_lead_plus_six(monkeypatch):
    seen = {}

    def fake_fetch(url, targets, session=None):
        seen["url"], seen["keys"] = url, [t[2] for t in targets]
        z = np.zeros((GRID_NLAT, GRID_NLON), dtype=np.float32)
        return {key: z for key in seen["keys"]}

    monkeypatch.setattr(gt, "fetch_grib2_messages", fake_fetch)
    gt.fetch_lead_field(T0, 48)
    # valid T0+48 h from the T0-6 h run: its f054
    assert "20220901/06" in seen["url"] and seen["url"].endswith("f054")
    assert ("UGRD", 850) in seen["keys"] and ("VGRD", 850) in seen["keys"]
    assert len(seen["keys"]) == 3
