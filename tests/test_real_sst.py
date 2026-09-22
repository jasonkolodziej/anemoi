"""Real NCEI OISST v2.1 SST fetch (data.real_sst, #147).

Requires the optional `gridded` extra (xarray + h5netcdf/h5py). The
network-marked test hits the real, verified-working NCEI archive but is
skipped by default -- set ANEMOI_RUN_NETWORK_TESTS=1 to run it. Everything
else here exercises `sst_at`'s nearest-cell/longitude-normalisation logic
against a small constructed grid, no network needed.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

pytest.importorskip("xarray")
try:
    import h5netcdf  # noqa: F401
except ImportError:
    pytest.skip("h5netcdf unavailable", allow_module_level=True)

from anemoi.data.real_sst import fetch_oisst_sst, sst_at  # noqa: E402

pytestmark = pytest.mark.gridded


def _small_grid():
    # A tiny, real-shape-consistent 4x4 grid: lat/lon centres 0.25 degrees
    # apart, one NaN cell to prove missing data survives the lookup.
    lat = np.array([-0.375, -0.125, 0.125, 0.375])
    lon = np.array([0.125, 0.375, 0.625, 0.875])
    sst = np.array(
        [
            [20.0, 21.0, 22.0, 23.0],
            [24.0, 25.0, np.nan, 27.0],
            [28.0, 29.0, 30.0, 31.0],
            [32.0, 33.0, 34.0, 35.0],
        ]
    )
    return sst, lat, lon


def test_sst_at_finds_the_nearest_cell():
    sst, lat, lon = _small_grid()
    # 0.1 is nearest lat[2]=0.125; 0.3 is nearest lon[1]=0.375 -> sst[2,1]
    assert sst_at(sst, lat, lon, 0.1, 0.3) == pytest.approx(29.0)


def test_sst_at_normalises_negative_longitude_to_0_360():
    sst, lat, lon = _small_grid()
    # -359.875 == 0.125 in 0..360 convention
    assert sst_at(sst, lat, lon, -0.4, -359.875) == pytest.approx(20.0)


def test_sst_at_returns_nan_over_a_real_missing_cell():
    sst, lat, lon = _small_grid()
    assert np.isnan(sst_at(sst, lat, lon, -0.1, 0.6))


# --- network tests (real endpoint, opt-in only) -----------------------------


@pytest.mark.network
def test_fetch_oisst_sst_reads_real_recent_data():
    sst, lat, lon = fetch_oisst_sst(date.today() - timedelta(days=1))
    assert sst.shape == (720, 1440)
    valid = sst[~np.isnan(sst)]
    assert valid.size > 0
    # Real global SST range: sea ice freezing point to max plausible tropical.
    assert -2.0 <= valid.min()
    assert valid.max() <= 36.0
