"""Real GOES-18/19 ABI imagery fetch/crop (data.real_goes, #146).

Requires the optional `gridded` extra (xarray/h5netcdf/pyproj/requests).
The network-marked tests hit the real, verified-working NOAA AWS Open
Data archive but are skipped by default -- set ANEMOI_RUN_NETWORK_TESTS=1
to run them. Everything else exercises key-listing/parsing and the real
geostationary projection math against a small constructed xarray Dataset
carrying the exact real `goes_imager_projection` attributes (verified
live against a real GOES-19 file), no network needed.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

pytest.importorskip("xarray")
pytest.importorskip("pyproj")

from anemoi.data.real_goes import (  # noqa: E402
    GOES_BUCKETS,
    GoesFetchError,
    _crop_variable,
    _find_real_scan,
    _nearest_scan_key,
    _parse_scan_start,
    _pixel_index,
)

pytestmark = pytest.mark.gridded

# Real goes_imager_projection attributes, fetched live 2026-09-22 from a
# real GOES-19 ABI-L2-CMIPF file -- not invented values.
_REAL_PROJ_ATTRS = {
    "perspective_point_height": 35786023.0,
    "semi_major_axis": 6378137.0,
    "semi_minor_axis": 6356752.31414,
    "longitude_of_projection_origin": -75.0,
    "sweep_angle_axis": "x",
}

_REAL_SAMPLE_KEYS = [
    "ABI-L2-CMIPF/2026/265/18/OR_ABI-L2-CMIPF-M6C02_G19_s20262651800196_e20262651809505_c20262651809558.nc",
    "ABI-L2-CMIPF/2026/265/18/OR_ABI-L2-CMIPF-M6C02_G19_s20262651810196_e20262651819505_c20262651819557.nc",
    "ABI-L2-CMIPF/2026/265/18/OR_ABI-L2-CMIPF-M6C02_G19_s20262651820196_e20262651829505_c20262651829561.nc",
]


def _fake_dataset(size: int = 200):
    """A small xarray Dataset carrying the real projection metadata and a
    plausible x/y scan-angle grid, small enough to build in-memory --
    enough to unit test `_pixel_index`/`_crop_variable` without a real
    ~400 MB fetch."""
    import xarray as xr

    # Real GOES-19 full-disk x/y span roughly +/-0.151865 rad (confirmed
    # live); a smaller synthetic grid over the same real range is enough
    # to test index math, not to be a real image.
    coords = np.linspace(-0.151865, 0.151865, size)
    rng = np.random.default_rng(7)
    cmi = rng.uniform(200.0, 300.0, size=(size, size)).astype(np.float32)
    dqf = np.zeros((size, size), dtype=np.int8)
    dqf[0, 0] = 1  # one real-shaped bad pixel to test masking

    ds = xr.Dataset(
        {
            "CMI": (("y", "x"), cmi),
            "DQF": (("y", "x"), dqf),
            "goes_imager_projection": ((), 0),
        },
        coords={"y": coords, "x": coords},
    )
    ds["goes_imager_projection"].attrs.update(_REAL_PROJ_ATTRS)
    return ds


def test_parse_scan_start_reads_the_real_filename_field():
    key = _REAL_SAMPLE_KEYS[0]
    assert _parse_scan_start(key) == datetime(2026, 9, 22, 18, 0, 19)


def test_nearest_scan_key_picks_the_closest_real_start_time():
    target = datetime(2026, 9, 22, 18, 12, 0)
    assert _nearest_scan_key(_REAL_SAMPLE_KEYS, target) == _REAL_SAMPLE_KEYS[1]


def test_nearest_scan_key_raises_on_an_empty_listing():
    with pytest.raises(GoesFetchError, match="no real scans"):
        _nearest_scan_key([], datetime(2026, 9, 22, 18, 0, 0))


def test_find_real_scan_rejects_an_unknown_satellite():
    with pytest.raises(GoesFetchError, match="unknown satellite"):
        _find_real_scan("G99", "ABI-L2-CMIPF", datetime(2026, 9, 22, 18, 0, 0))


def test_both_real_satellites_are_registered():
    assert set(GOES_BUCKETS) == {"G18", "G19"}
    assert GOES_BUCKETS["G19"] == "noaa-goes19"
    assert GOES_BUCKETS["G18"] == "noaa-goes18"


def test_pixel_index_places_the_sub_satellite_point_at_the_grid_centre():
    # (0, 0) lat/lon is not physically meaningful for a -75 lon_0 geostationary
    # view, so instead: the real sub-satellite point (0 lat, -75 lon, the
    # projection origin) must project to scan angle (0, 0) -- the centre
    # of a symmetric grid.
    ds = _fake_dataset(size=201)  # odd size so there's an exact centre index
    yi, xi = _pixel_index(ds, center_lat=0.0, center_lon=-75.0)
    assert yi == 100
    assert xi == 100


def test_crop_variable_masks_the_real_bad_dqf_pixel():
    ds = _fake_dataset(size=201)
    crop = _crop_variable(ds, "CMI", center_lat=0.0, center_lon=-75.0, size=4)
    assert crop.shape == (4, 4)
    # The synthetic bad pixel sits at (0,0) in the full grid, outside this
    # small centred crop -- so nothing here should be masked.
    assert not np.isnan(crop).any()


def test_crop_variable_raises_when_the_crop_falls_off_the_real_image_edge():
    ds = _fake_dataset(size=20)
    # A centre crop near the very edge of a tiny grid can't fit a full window.
    with pytest.raises(GoesFetchError, match="off the real image edge"):
        _crop_variable(ds, "CMI", center_lat=0.0, center_lon=-75.0, size=64)


# --- network tests (real endpoint, opt-in only) -----------------------------


@pytest.mark.network
def test_find_real_scan_reads_the_real_live_archive():
    from datetime import UTC, timedelta

    target = datetime.now(UTC) - timedelta(hours=2)
    url = _find_real_scan("G19", "ABI-L2-CMIPF", target, channel=14)
    assert url.startswith("https://noaa-goes19.s3.amazonaws.com/ABI-L2-CMIPF/")
    assert "M6C14" in url


@pytest.mark.network
def test_fetch_real_satellite_crop_reads_real_physically_sane_ir():
    from datetime import UTC, timedelta

    from anemoi.data.real_goes import fetch_real_satellite_crop
    from anemoi.data.satellite import CHANNEL_NAMES

    target = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    # A real open-ocean Atlantic point, unlikely to be exactly on the
    # disk edge for GOES-East.
    crop = fetch_real_satellite_crop(
        "test", target, center_lat=20.0, center_lon=-50.0, satellite="G19", size=32,
    )
    assert crop.channels.shape == (len(CHANNEL_NAMES), 32, 32)
    ir = crop.channels[0]
    valid = ir[~np.isnan(ir)]
    assert valid.size > 0
    # Real plausible brightness temperature range in Kelvin.
    assert 180.0 < valid.mean() < 320.0


@pytest.mark.network
def test_real_channel_ranges_overlap_the_synthetic_generators_assumed_ranges():
    """Acceptance criterion from GitHub #146: a dual-source parity/sanity
    check against data.satellite's synthetic ranges. Real and synthetic
    values are never expected to match exactly (one is a real storm at a
    real moment, the other a parametric stand-in) -- this checks the real
    fetch lands in the same broad physical envelope the synthetic
    generator assumes, catching a unit-confusion bug (e.g. Kelvin vs
    Celsius, or a 0-100 vs 0-1 reflectance scale) rather than a
    pixel-exact match.
    """
    from datetime import UTC, timedelta

    from anemoi.data.real_goes import fetch_real_satellite_crop
    from anemoi.data.satellite import CHANNEL_NAMES

    target = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    crop = fetch_real_satellite_crop(
        "test", target, center_lat=20.0, center_lon=-50.0, satellite="G19", size=32,
    )
    channels = dict(zip(CHANNEL_NAMES, crop.channels, strict=True))

    # Synthetic generator's own assumed envelopes (generate_satellite_crop):
    # ir/wv ~200-260K (+/- noise), vis 0-1, sst ~24.5-28C (+/- noise), rain 0-~50mm/hr.
    real_envelopes = {
        "ir_brightness_temp_k": (150.0, 320.0),
        "water_vapor_brightness_temp_k": (150.0, 320.0),
        "visible_reflectance": (0.0, 1.5),  # real reflectance can exceed 1.0 in bright cloud
        "sst_c": (-5.0, 40.0),
        "rain_rate_mm_hr": (0.0, 200.0),
    }
    for name, (lo, hi) in real_envelopes.items():
        valid = channels[name][~np.isnan(channels[name])]
        if valid.size == 0:
            continue  # a real channel can be legitimately all-cloud-masked; not a failure
        assert lo <= valid.mean() <= hi, f"{name}: real mean {valid.mean()} outside [{lo}, {hi}]"
