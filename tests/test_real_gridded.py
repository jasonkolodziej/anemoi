"""Real GriddedFields from ERA5 (Zarr) and GDAS/GFS (GRIB2) (PLAN.md §4:
Gridded fields). Requires the optional `gridded` extra.

The network-marked tests hit real, verified-working public endpoints
(anonymous ARCO-ERA5 Zarr on GCS; anonymous byte-range GRIB2 fetch against
NOAA's AWS Open Data bucket) but are skipped by default -- set
ANEMOI_RUN_NETWORK_TESTS=1 to run them. Everything else here constructs
synthetic inputs matching the real, verified schema of each source, so the
mapping/unit-conversion logic is tested without a network dependency.
"""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pytest

pytest.importorskip("xarray")
try:
    import eccodes  # noqa: F401
except (ImportError, RuntimeError) as exc:
    # eccodes' native library can be present-but-broken on a given machine
    # (gribapi.bindings raises RuntimeError, not ImportError, when it can't
    # find the compiled library) -- pytest.importorskip only catches
    # ImportError, so that failure mode would otherwise abort collection of
    # this whole file, including the ERA5-only tests that never touch
    # eccodes at all. Skip GDAS-specific tests explicitly instead (see
    # NEEDS_ECCODES below); everything else still runs.
    _ECCODES_ERROR = str(exc)
else:
    _ECCODES_ERROR = None

NEEDS_ECCODES = pytest.mark.skipif(
    _ECCODES_ERROR is not None, reason=f"eccodes unavailable: {_ECCODES_ERROR}"
)

from anemoi.data.real_gridded import (  # noqa: E402
    GDAS_LEVEL_MESSAGES,
    GDAS_MSLP_KEY,
    GDAS_SST_PLACEHOLDER_C,
    GRID_NLAT,
    GRID_NLON,
    OHC_PLACEHOLDER_KJ_CM2,
    _crop_box,
    _parse_grib2_index,
    _specific_humidity_to_rh_pct,
    era5_deps_available,
    era5_to_gridded_fields,
    fetch_gdas_grib2_fields,
    gdas_to_gridded_fields,
    open_era5,
    require_era5_deps,
)
from anemoi.data.sources import Flavor  # noqa: E402

T = datetime(2026, 8, 6, 6, tzinfo=UTC)

pytestmark = pytest.mark.gridded


# --- _crop_box ---------------------------------------------------------------


def _global_grid_with_marker(marker_lat: float, marker_lon: float, value: float = 999.0) -> np.ndarray:
    grid = np.zeros((GRID_NLAT, GRID_NLON))
    lat_idx = round((90.0 - marker_lat) / 0.25)
    lon_idx = round((marker_lon % 360.0) / 0.25)
    grid[lat_idx, lon_idx] = value
    return grid


def test_crop_box_centers_on_the_requested_lat_lon():
    grid = _global_grid_with_marker(marker_lat=20.0, marker_lon=280.0)  # 280E == -80W
    box = _crop_box(grid, center_lat=20.0, center_lon=-80.0, box_deg=10.0)
    center = box.shape[0] // 2, box.shape[1] // 2
    assert box[center] == pytest.approx(999.0)


def test_crop_box_shape_matches_requested_box_degrees():
    grid = np.zeros((GRID_NLAT, GRID_NLON))
    box = _crop_box(grid, center_lat=15.0, center_lon=-45.0, box_deg=8.0)
    expected_side = 2 * round(8.0 / 2.0 / 0.25) + 1
    assert box.shape == (expected_side, expected_side)


def test_crop_box_wraps_longitude_across_the_seam():
    """A storm near the 0/360 seam (rare for the Atlantic, but the grid is
    global) must not silently truncate the box at the array edge."""
    grid = _global_grid_with_marker(marker_lat=10.0, marker_lon=1.0)
    box = _crop_box(grid, center_lat=10.0, center_lon=1.0, box_deg=10.0)
    assert box.max() == pytest.approx(999.0)
    assert box.shape == (41, 41)  # no truncation from wraparound


def test_crop_box_rejects_the_wrong_global_shape():
    with pytest.raises(ValueError, match="721, 1440"):
        _crop_box(np.zeros((10, 10)), 0.0, 0.0, 10.0)


# --- specific humidity -> RH ---------------------------------------------------


def test_specific_humidity_at_saturation_gives_rh_near_100():
    from anemoi.data.real_gridded import _saturation_vapor_pressure_hpa_array

    temp_c = np.array([20.0])
    es = _saturation_vapor_pressure_hpa_array(temp_c)
    q_sat = 0.622 * es / (700.0 - 0.378 * es)  # invert the forward formula
    rh = _specific_humidity_to_rh_pct(q_sat, temp_c, pressure_hpa=700.0)
    assert rh[0] == pytest.approx(100.0, abs=0.5)


def test_specific_humidity_is_clipped_to_the_unit_range():
    rh = _specific_humidity_to_rh_pct(
        np.array([0.0, 10.0]), np.array([20.0, 20.0]), pressure_hpa=700.0
    )
    assert rh[0] == pytest.approx(0.0)
    assert rh[1] <= 100.0


# --- ERA5/GDAS dependency isolation ---------------------------------------------


def test_era5_deps_do_not_require_eccodes(monkeypatch):
    """ERA5 is a Zarr read and never touches GRIB parsing -- require_era5_deps
    must succeed even when eccodes is entirely unimportable, which is a real,
    observed failure mode on this machine (gribapi.bindings' "Cannot find the
    ecCodes library" RuntimeError, not even an ImportError)."""
    import builtins

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "eccodes" or name.startswith("eccodes."):
            raise RuntimeError("simulated: cannot find the ecCodes library")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    require_era5_deps()  # must not raise
    assert era5_deps_available()


def test_open_era5_reuses_a_passed_in_store_instead_of_reopening():
    """era5_cache shares one store handle across many samples to avoid
    reopening the Zarr store per fetch (~1-2s each, see
    docs/capacity_ablation.md's benchmark) -- open_era5 must call .sel() on
    exactly the store it was given, not open a fresh one."""

    class FakeStore:
        def __init__(self):
            self.sel_calls = 0
            self.last_kwargs = None

        def sel(self, **kwargs):
            self.sel_calls += 1
            self.last_kwargs = kwargs
            return "selected"

    store = FakeStore()
    result = open_era5(T, store=store)
    assert store.sel_calls == 1
    assert "time" in store.last_kwargs
    assert result == "selected"


@NEEDS_ECCODES
def test_fetch_gdas_grib2_fields_uses_a_passed_in_session_not_the_module():
    """gdas_cache shares one requests.Session across many concurrent samples
    to reuse the connection pool (~8 requests/sample to the same host) --
    fetch_gdas_grib2_fields must call .get() on the session it was given,
    not the plain requests module. Fails fast on the first (.idx) request
    via a distinctive exception so this doesn't need real network access or
    a real GRIB2 payload for eccodes to parse."""

    class Sentinel(Exception):
        pass

    class FakeSession:
        def __init__(self):
            self.get_calls = 0

        def get(self, *args, **kwargs):
            self.get_calls += 1
            raise Sentinel("session.get was called")

    session = FakeSession()
    with pytest.raises(Sentinel):
        fetch_gdas_grib2_fields(T, session=session)
    assert session.get_calls == 1


# --- GDAS .idx parsing ---------------------------------------------------------


def test_parse_grib2_index_gives_contiguous_byte_ranges():
    idx_text = (
        "1:0:d=2026080606:PRMSL:mean sea level:anl:\n"
        "2:1000:d=2026080606:UGRD:850 mb:anl:\n"
        "3:2500:d=2026080606:VGRD:850 mb:anl:\n"
    )
    ranges = _parse_grib2_index(idx_text)
    assert ranges[("PRMSL", "mean sea level")] == (0, 1000)
    assert ranges[("UGRD", "850 mb")] == (1000, 2500)
    assert ranges[("VGRD", "850 mb")] == (2500, None)  # last message: fetch to EOF


# --- era5_to_gridded_fields (synthetic Dataset matching the real schema) ------


def _synthetic_era5_dataset():
    """Full (721, 1440) global 0.25 deg grid, matching the real ARCO-ERA5
    shape -- _crop_box requires it, and a scaled-down grid would silently
    skip exercising the actual crop-indexing logic."""
    xr = pytest.importorskip("xarray")
    levels = [200, 500, 700, 850]
    lat = np.linspace(90, -90, GRID_NLAT)
    lon = np.linspace(0, 359.75, GRID_NLON)
    shape3d = (len(levels), len(lat), len(lon))

    return xr.Dataset(
        {
            "u_component_of_wind": (("level", "latitude", "longitude"), 15.0 * np.ones(shape3d)),
            "v_component_of_wind": (("level", "latitude", "longitude"), 5.0 * np.ones(shape3d)),
            "geopotential": (("level", "latitude", "longitude"), 57500.0 * np.ones(shape3d)),
            "temperature": (("level", "latitude", "longitude"), 281.0 * np.ones(shape3d)),
            "specific_humidity": (("level", "latitude", "longitude"), 0.008 * np.ones(shape3d)),
            "mean_sea_level_pressure": (("latitude", "longitude"), 101200.0 * np.ones((len(lat), len(lon)))),
            "sea_surface_temperature": (("latitude", "longitude"), 301.65 * np.ones((len(lat), len(lon)))),
        },
        coords={"level": levels, "latitude": lat, "longitude": lon, "time": np.datetime64("2026-08-06T06:00:00")},
    )


def test_era5_to_gridded_fields_converts_units_correctly():
    ds = _synthetic_era5_dataset()
    fields = era5_to_gridded_fields(ds, center_lat=0.0, center_lon=0.0, box_deg=20.0)

    assert fields.flavor is Flavor.ERA5_PRETRAIN
    assert fields.u200.mean() == pytest.approx(15.0)
    assert fields.z500.mean() == pytest.approx(57500.0 / 9.80665)  # geopotential -> height
    assert fields.mslp.mean() == pytest.approx(1012.0)  # Pa -> hPa
    assert fields.sst.mean() == pytest.approx(28.5)  # K -> degC
    assert np.all(fields.ohc == OHC_PLACEHOLDER_KJ_CM2)
    assert 0.0 <= fields.rh700.mean() <= 100.0


# --- gdas_to_gridded_fields (synthetic message dict matching the real schema) --


def _synthetic_gdas_fields():
    grid = lambda v: np.full((GRID_NLAT, GRID_NLON), v)  # noqa: E731
    fields = {(sn, lvl): grid(10.0) for sn, lvl in GDAS_LEVEL_MESSAGES}
    fields[("HGT", 500)] = grid(5750.0)
    fields[("TMP", 700)] = grid(281.0)
    fields[("RH", 700)] = grid(62.0)
    fields[GDAS_MSLP_KEY] = grid(101200.0)
    return fields


def test_gdas_to_gridded_fields_converts_units_correctly():
    fields = gdas_to_gridded_fields(
        _synthetic_gdas_fields(), center_lat=15.0, center_lon=-60.0, valid_time=T, box_deg=20.0
    )
    assert fields.flavor is Flavor.GDAS_FINETUNE
    assert fields.z500.mean() == pytest.approx(5750.0)  # HGT is already meters, no conversion
    assert fields.rh700.mean() == pytest.approx(62.0)  # RH reported directly
    assert fields.mslp.mean() == pytest.approx(1012.0)  # Pa -> hPa
    assert np.all(fields.sst == GDAS_SST_PLACEHOLDER_C)
    assert np.all(fields.ohc == OHC_PLACEHOLDER_KJ_CM2)


def test_gdas_missing_message_raises_a_clear_error():
    incomplete = _synthetic_gdas_fields()
    del incomplete[("UGRD", 200)]
    with pytest.raises(KeyError):
        gdas_to_gridded_fields(incomplete, center_lat=15.0, center_lon=-60.0, valid_time=T)


# --- network tests (real endpoints, opt-in only) -------------------------------


@pytest.mark.network
def test_open_era5_reads_the_real_arco_era5_store():
    ds = open_era5(T)
    fields = era5_to_gridded_fields(ds, center_lat=20.0, center_lon=-60.0)
    assert fields.shape == (41, 41)
    assert 250.0 < fields.t700.mean() < 300.0  # plausible 700 mb temperature in Kelvin


@pytest.mark.network
@NEEDS_ECCODES
def test_fetch_gdas_grib2_fields_reads_the_real_noaa_archive():
    messages = fetch_gdas_grib2_fields(T)
    fields = gdas_to_gridded_fields(messages, center_lat=20.0, center_lon=-60.0, valid_time=T)
    assert fields.shape == (41, 41)
    assert 4000.0 < fields.z500.mean() < 6200.0  # plausible 500 mb geopotential height in meters
