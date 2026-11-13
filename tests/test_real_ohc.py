"""CoastWatch OHC fetch + decode (data.real_ohc).

Offline tests build small CoastWatch-shaped files (the real NA/NP
coordinate arrays, NetCDF-3 through scipy and HDF5 through h5netcdf) and
serve them from a fake archive. The network-marked tests read real files
and SHIPS' developmental SOHC; they are skipped unless
ANEMOI_RUN_NETWORK_TESTS=1, and they send urllib's default User-Agent.
"""

from __future__ import annotations

import functools
import http.server
import json
import math
import os
import threading
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("xarray")
pytest.importorskip("scipy")
pytest.importorskip("h5netcdf")

import xarray as xr  # noqa: E402

from anemoi.data import real_ohc  # noqa: E402
from anemoi.data.real_ohc import (  # noqa: E402
    OhcFetchError,
    OhcNotPublished,
    OhcRejected,
    OhcUnavailable,
)

pytestmark = pytest.mark.gridded

LAND = (slice(120, 141), slice(60, 81))  # NA rows 30..35N, cols 85..80W: fill
COLD_FROM_ROW = 200  # 50N and north: 0.0, water below 26 C


def _value(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """A plane in (lat, lon), so bilinear interpolation of it is exact."""
    return (100.0 + 0.5 * lat[:, None] + 0.1 * lon[None, :]).astype(np.float32)


def _ohc(basin: str) -> np.ndarray:
    lat, lon = real_ohc.expected_coordinates(basin)
    ohc = _value(lat, lon)
    ohc[COLD_FROM_ROW:, :] = 0.0
    if basin == "na":
        ohc[LAND] = -999.0
    else:
        ohc[:, -1] = 0.0  # NP's 80.0W column: 0.0 where NA has values
        ohc[-20:, :40] = -999.0  # some fill, as every real file has
    return ohc


def _write(
    tmp: Path,
    basin: str,
    *,
    fmt: str = "netcdf3",
    ohc: np.ndarray | None = None,
    lat: np.ndarray | None = None,
    lon: np.ndarray | None = None,
    units: str = "kJ cm^-2",
    sshae: float | None = 0.29,
    date_created: str | None = None,
) -> bytes:
    want_lat, want_lon = real_ohc.expected_coordinates(basin)
    lat = want_lat if lat is None else lat
    lon = want_lon if lon is None else lon
    ohc = _ohc(basin) if ohc is None else ohc
    grid = ("time", "latitude", "longitude")
    data = {"ohc": (grid, ohc[None].astype(np.float32), {"units": units})}
    encoding: dict[str, dict] = {
        "ohc": {"_FillValue": np.float32(-999.0)},
        "latitude": {"_FillValue": None},
        "longitude": {"_FillValue": None},
        "time": {"_FillValue": None},
    }
    if sshae is not None:
        err = np.full(ohc.shape, sshae, dtype=np.float32)
        err[ohc == -999.0] = -999.0
        err[:5, :5] = 5.0  # a few large values must not move the median
        data["sshaE"] = (grid, err[None], {"units": "1"})
        encoding["sshaE"] = {"_FillValue": np.float32(-999.0)}
    ds = xr.Dataset(
        data,
        coords={
            "latitude": ("latitude", lat.astype(np.float32), {"units": "degrees_north"}),
            "longitude": ("longitude", lon.astype(np.float32), {"units": "degrees_east"}),
            "time": ("time", np.array([0.0])),
        },
        attrs={} if date_created is None else {"date_created": date_created},
    )
    path = tmp / f"{basin}-{fmt}-{len(list(tmp.iterdir()))}.nc"
    if fmt == "netcdf3":
        ds.to_netcdf(path, engine="scipy", format="NETCDF3_CLASSIC", encoding=encoding)
    else:
        ds.to_netcdf(path, engine="h5netcdf", encoding=encoding)
    return path.read_bytes()


@pytest.fixture(scope="module")
def files(tmp_path_factory) -> dict[str, bytes]:
    tmp = tmp_path_factory.mktemp("ohc")
    return {
        "na3": _write(tmp, "na"),
        "np3": _write(tmp, "np"),
        "na5": _write(tmp, "na", fmt="hdf5"),
        "np5": _write(tmp, "np", fmt="hdf5"),
    }


@pytest.fixture
def tmp(tmp_path) -> Path:
    return tmp_path


class Archive:
    """A fake CoastWatch: URL -> bytes, 404 for anything else."""

    def __init__(self, files: dict[str, bytes] | None = None) -> None:
        self.files = dict(files or {})
        self.requested: list[str] = []

    def put(self, basin: str, name_day: date, body: bytes) -> None:
        self.files[real_ohc.ohc_url(basin, name_day)] = body

    def __call__(self, url: str) -> bytes:
        self.requested.append(url)
        if url not in self.files:
            raise OhcNotPublished(url)
        return self.files[url]


def _full_archive(files: dict[str, bytes], first: date, last: date) -> Archive:
    """Every name day in [first, last] for both basins, in the format the
    real archive has on that day."""
    archive = Archive()
    day = first
    while day <= last:
        v1r1 = day >= real_ohc.V1R1_START
        archive.put("na", day, files["na5" if v1r1 else "na3"])
        archive.put("np", day, files["np5" if v1r1 else "np3"])
        day += timedelta(days=1)
    return archive


def _decode(body: bytes, basin: str = "na", name_day: date = date(2021, 8, 28)):
    return real_ohc.decode_ohc(body, basin, name_day)


# --- names and dates ----------------------------------------------------------


def test_urls_follow_the_chain_switch_at_2024_day_15():
    base = real_ohc.BASE_URL
    assert real_ohc.ohc_url("na", date(2021, 8, 28)) == f"{base}/na/2021/ohc_naQG3_2021_240.nc"
    assert real_ohc.ohc_url("np", date(2024, 1, 14)) == f"{base}/np/2024/ohc_npQG3_2024_014.nc"
    assert real_ohc.ohc_url("np", date(2024, 1, 15)) == f"{base}/np14/2024/ohc_np14QG3_2024_015.nc"
    assert real_ohc.ohc_url("na", date(2025, 3, 26)) == f"{base}/na14/2025/ohc_na14QG3_2025_085.nc"


def test_no_url_before_the_archive_or_for_another_basin():
    with pytest.raises(ValueError, match="before"):
        real_ohc.ohc_url("na", date(2020, 4, 29))
    with pytest.raises(ValueError, match="basin"):
        real_ohc.ohc_url("sp", date(2022, 1, 1))


def test_v1r1_files_are_made_the_day_after_their_name():
    assert real_ohc.V1R1_START == date(2025, 1, 1) + timedelta(days=84)  # 2025 day 085
    assert real_ohc.creation_day(date(2024, 8, 1)) == date(2024, 8, 1)
    assert real_ohc.creation_day(date(2025, 3, 25)) == date(2025, 3, 25)  # day 084, v1r0
    assert real_ohc.creation_day(date(2025, 3, 26)) == date(2025, 3, 27)  # day 085, v1r1
    assert real_ohc.creation_day(date(2026, 11, 12)) == date(2026, 11, 13)


def test_name_day_for_creation_inverts_creation_day_and_has_a_gap_at_the_switch():
    day = date(2025, 3, 1)
    while day < date(2025, 5, 1):
        assert real_ohc.name_day_for_creation(real_ohc.creation_day(day)) == day
        day += timedelta(days=1)
    assert real_ohc.name_day_for_creation(date(2025, 3, 26)) is None


# --- decoding -----------------------------------------------------------------


def test_format_is_detected_from_the_first_bytes(files):
    assert real_ohc.detect_format(files["na3"]) == "netcdf3"
    assert files["na3"][:4] == b"CDF\x01"
    assert real_ohc.detect_format(files["na5"]) == "hdf5"
    with pytest.raises(OhcRejected, match="neither"):
        real_ohc.detect_format(b"<html><body>Not Found</body></html>")


def test_both_formats_decode_to_the_same_field(files):
    a, b = _decode(files["na3"]), _decode(files["na5"])
    assert (a.file_format, b.file_format) == ("netcdf3", "hdf5")
    np.testing.assert_array_equal(a.ohc, b.ohc)
    np.testing.assert_array_equal(a.lat, b.lat)
    np.testing.assert_array_equal(a.lon, b.lon)


def test_fill_becomes_nan_and_zero_is_kept(files):
    na = _decode(files["na3"])
    assert na.ohc.dtype == np.float32
    assert na.ohc.shape == (241, 401)
    assert np.isnan(na.ohc[LAND]).all()
    assert int(np.isnan(na.ohc).sum()) == 21 * 21
    assert (na.ohc[COLD_FROM_ROW:] == 0.0).all()
    assert na.valid_cells == 241 * 401 - 21 * 21


def test_a_blank_file_is_rejected(tmp):
    """na14 2025 day 199: every variable 0.0, coordinates included."""
    zeros = np.zeros(241), np.zeros(401)
    blank = _write(tmp, "na", ohc=np.zeros((241, 401)), lat=zeros[0], lon=zeros[1], sshae=None)
    with pytest.raises(OhcRejected, match="not the NA grid"):
        _decode(blank)


def test_a_file_with_no_fill_cell_is_rejected(tmp):
    body = _write(tmp, "na", ohc=np.zeros((241, 401)))
    with pytest.raises(OhcRejected, match="no fill"):
        _decode(body)


def test_coordinates_must_be_the_basins(tmp, files):
    lat, lon = real_ohc.expected_coordinates("na")
    shifted = _write(tmp, "na", lon=lon + 0.25)
    with pytest.raises(OhcRejected, match="not the NA grid"):
        _decode(shifted)
    with pytest.raises(OhcRejected, match="not the NP grid"):
        _decode(files["na3"], "np")


def test_units_must_be_kj_per_cm2(tmp):
    with pytest.raises(OhcRejected, match="units"):
        _decode(_write(tmp, "na", units="J m-2"))


def test_a_truncated_file_is_rejected(files):
    with pytest.raises(OhcRejected):
        _decode(files["na3"][:5000])


def test_a_file_made_later_than_its_name_says_is_rejected(tmp):
    """v1r1 is made the day after its name day; anything later would hold
    data the date rule thinks isn't out yet."""
    day = date(2025, 8, 28)
    ok = _write(tmp, "na", fmt="hdf5", date_created="2025-08-29T09:24:01Z")
    assert real_ohc.decode_ohc(ok, "na", day).date_created == "2025-08-29T09:24:01Z"
    late = _write(tmp, "na", fmt="hdf5", date_created="2025-08-30T09:24:01Z")
    with pytest.raises(OhcRejected, match="date_created"):
        real_ohc.decode_ohc(late, "na", day)
    v1r0_late = _write(tmp, "na", date_created="2024-08-28T09:00:00Z")
    with pytest.raises(OhcRejected, match="date_created"):
        real_ohc.decode_ohc(v1r0_late, "na", date(2024, 8, 27))


def test_sshae_median_flags_a_degraded_file(tmp, files):
    clean = _decode(files["na3"])
    assert clean.sshae_median == pytest.approx(0.29)  # fill and the 5.0 block don't count
    assert not clean.degraded
    bad = _decode(_write(tmp, "na", sshae=0.33))
    assert bad.degraded
    assert bad.metadata()["degraded"] is True
    none = _decode(_write(tmp, "na", sshae=None))
    assert none.sshae_median is None
    assert not none.degraded


# --- placement on real_gridded's lattice ---------------------------------------


def _row_col(lat: float, lon: float) -> tuple[int, int]:
    return round((90.0 - lat) / 0.25), round((lon % 360.0) / 0.25)


def test_na_and_np_nodes_land_on_the_lattice(files):
    from anemoi.data.real_gridded import GRID_NLAT, GRID_NLON

    na, np_ = _decode(files["na3"]), _decode(files["np3"], "np")
    field = real_ohc.place([na, np_])
    assert field.shape == (GRID_NLAT, GRID_NLON) == (721, 1440)
    assert field.dtype == np.float32
    # (lat, lon, file row, file col): latitude flips, longitude wraps.
    for basin, src, lat, lon, i, j in (
        ("na", na, 25.0, -90.0, 100, 40),
        ("na", na, 0.0, -100.0, 0, 0),
        ("na", na, 10.0, 0.0, 40, 400),  # 0E: lattice column 0
        ("na", na, 49.75, -0.25, 199, 399),  # lattice column 1439
        ("np", np_, 20.0, 150.0, 80, 200),
        ("np", np_, 0.0, 100.0, 0, 0),
        ("np", np_, 49.75, 179.75, 199, 319),
    ):
        row, col = _row_col(lat, lon)
        assert field[row, col] == src.ohc[i, j], (basin, lat, lon)
    assert _row_col(0.0, 0.0) == (360, 0)
    assert _row_col(10.0, 0.0) == (320, 0)
    assert _row_col(49.75, -0.25) == (161, 1439)
    assert np.isnan(field[_row_col(60.25, -50.0)])  # north of both grids
    assert np.isnan(field[_row_col(20.0, 50.0)])  # east of NA, west of NP
    assert np.isnan(field[_row_col(-0.25, -50.0)])  # south of both


def test_np_is_written_first_and_na_wins_where_it_is_valid(files):
    na, np_ = _decode(files["na3"]), _decode(files["np3"], "np")
    field = real_ohc.place([na, np_])
    assert (real_ohc.place([np_, na]) == field)[np.isfinite(field)].all()
    row, col = _row_col(20.0, -80.0)
    assert np_.ohc[80, 720] == 0.0 and na.ohc[80, 80] > 0.0
    assert field[row, col] == na.ohc[80, 80]  # NA's value, not NP's 0.0
    row, col = _row_col(32.0, -80.0)  # NA has fill (land) here, NP 0.0
    assert np.isnan(na.ohc[128, 80])
    assert field[row, col] == 0.0
    row, col = _row_col(10.0, -95.0)  # both valid in the overlap: NA
    assert field[row, col] == na.ohc[40, 20]
    both = np.isfinite(real_ohc.place([na])) & np.isfinite(real_ohc.place([np_]))
    assert int(np.isfinite(field).sum()) == na.valid_cells + np_.valid_cells - int(both.sum())


# --- point values -------------------------------------------------------------


def test_bilinear_is_exact_at_a_node_on_every_source(files):
    na, np_ = _decode(files["na3"]), _decode(files["np3"], "np")
    field = real_ohc.place([na, np_])
    node = float(na.ohc[100, 40])  # 25N 90W
    assert real_ohc.ohc_at(25.0, -90.0, na) == node
    assert real_ohc.ohc_at(25.0, 270.0, na) == node
    assert real_ohc.ohc_at(25.0, -90.0, field) == node
    ohc_field = real_ohc.OhcField(datetime(2021, 9, 1, tzinfo=UTC), field, ())
    assert real_ohc.ohc_at(25.0, -90.0, ohc_field) == node


def test_bilinear_between_nodes(files):
    na = _decode(files["na3"])
    field = real_ohc.place([na])
    lat, lon = 25.1, -89.9
    want = 100.0 + 0.5 * lat + 0.1 * lon  # the plane the file holds
    assert real_ohc.ohc_at(lat, lon, na) == pytest.approx(want, abs=1e-4)
    assert real_ohc.ohc_at(lat, lon, field) == pytest.approx(want, abs=1e-4)
    # Mid-cell is the mean of the four corners.
    corners = na.ohc[100:102, 40:42].astype(np.float64)
    assert real_ohc.ohc_at(25.125, -89.875, na) == pytest.approx(corners.mean(), abs=1e-9)


def test_bilinear_needs_all_four_corners(files):
    na = _decode(files["na3"])
    assert math.isnan(real_ohc.ohc_at(29.9, -85.1, na))  # one corner is land
    # On a node line the next node north and east still count, on a file
    # and on the lattice alike.
    assert math.isnan(real_ohc.ohc_at(29.75, -85.25, na))
    assert math.isnan(real_ohc.ohc_at(29.75, -85.25, real_ohc.place([na])))
    assert math.isfinite(real_ohc.ohc_at(29.5, -85.5, na))
    assert math.isfinite(real_ohc.ohc_at(29.5, -85.5, real_ohc.place([na])))
    assert math.isnan(real_ohc.ohc_at(60.1, -50.0, na))  # north of the grid
    assert math.isnan(real_ohc.ohc_at(20.0, 10.0, na))  # east of NA
    assert math.isnan(real_ohc.ohc_at(20.0, -100.1, na))  # west of NA


def test_bilinear_wraps_at_greenwich_on_the_lattice(files):
    na = _decode(files["na3"])
    field = real_ohc.place([na])
    assert math.isnan(real_ohc.ohc_at(10.0, 0.1, field))  # 0.25E has no data
    lattice = np.full((721, 1440), np.nan, dtype=np.float32)
    lattice[320:322, [1439, 0]] = [[1.0, 3.0], [1.0, 3.0]]
    assert real_ohc.ohc_at(9.9, -0.125, lattice) == pytest.approx(2.0)
    assert real_ohc.ohc_at(9.9, 359.875, lattice) == pytest.approx(2.0)


# --- the date rule ------------------------------------------------------------


@pytest.mark.parametrize(
    ("t", "name_day", "url_part"),
    [
        # 2021-2023 train: old chain, creation = name day.
        (datetime(2021, 9, 1, 0, tzinfo=UTC), date(2021, 8, 30), "na/2021/ohc_naQG3_2021_242"),
        # Across the chain switch at 2024 day 15.
        (datetime(2024, 1, 16, 12, tzinfo=UTC), date(2024, 1, 14), "na/2024/ohc_naQG3_2024_014"),
        (datetime(2024, 1, 17, 0, tzinfo=UTC), date(2024, 1, 15), "na14/2024/ohc_na14QG3_2024_015"),
        # 2024 val: v1r0, creation = name day.
        (datetime(2024, 8, 1, 12, tzinfo=UTC), date(2024, 7, 30), "na14/2024/ohc_na14QG3_2024_212"),
        # Across the v1r1 naming switch at 2025 day 085.
        (datetime(2025, 3, 27, 6, tzinfo=UTC), date(2025, 3, 25), "na14/2025/ohc_na14QG3_2025_084"),
        (datetime(2025, 3, 29, 0, tzinfo=UTC), date(2025, 3, 26), "na14/2025/ohc_na14QG3_2025_085"),
        # 2025 test and live: v1r1, creation = name + 1, so name = D-3.
        (datetime(2025, 8, 1, 12, tzinfo=UTC), date(2025, 7, 29), "na14/2025/ohc_na14QG3_2025_210"),
    ],
)
def test_a_cycle_reads_the_file_made_two_days_before(files, t, name_day, url_part):
    archive = _full_archive(files, date(2021, 1, 1), date(2025, 12, 31))
    choice = real_ohc.select_file("na", t, fetch=archive)
    assert choice.file is not None
    assert choice.file.name_day == name_day
    assert url_part in choice.file.url
    assert choice.age_days == 2  # every split's inputs are the same age
    assert choice.step_backs == ()
    assert archive.requested == [choice.file.url]
    assert choice.file.file_format == ("hdf5" if name_day >= real_ohc.V1R1_START else "netcdf3")


def test_the_creation_day_no_file_has_is_stepped_over(files):
    """No file is made on 2025-03-26: day 084 is made 03-25, day 085 03-27."""
    archive = _full_archive(files, date(2025, 3, 1), date(2025, 4, 30))
    choice = real_ohc.select_file("na", datetime(2025, 3, 28, tzinfo=UTC), fetch=archive)
    assert choice.file.name_day == date(2025, 3, 25)
    assert choice.age_days == 3
    assert [(s.creation_day, s.name_day) for s in choice.step_backs] == [
        (date(2025, 3, 26), None)
    ]


def test_a_missing_file_steps_back_one_creation_day(files):
    t = datetime(2025, 9, 7, 6, tzinfo=UTC)  # D-2 creation 09-05 = name 09-04 (day 247)
    archive = _full_archive(files, date(2025, 8, 1), date(2025, 9, 30))
    del archive.files[real_ohc.ohc_url("na", date(2025, 9, 4))]
    choice = real_ohc.select_file("na", t, fetch=archive)
    assert choice.file.name_day == date(2025, 9, 3)
    assert choice.age_days == 3
    (step,) = choice.step_backs
    assert (step.creation_day, step.name_day, step.reason) == (
        date(2025, 9, 5), date(2025, 9, 4), "not published (404)",
    )


def test_a_rejected_file_is_stepped_over(files, tmp):
    t = datetime(2025, 7, 21, 0, tzinfo=UTC)  # D-2 creation 07-19 = name 07-18 (day 199)
    archive = _full_archive(files, date(2025, 7, 1), date(2025, 7, 31))
    zeros = np.zeros((241, 401))
    archive.put(
        "na", date(2025, 7, 18),
        _write(tmp, "na", fmt="hdf5", ohc=zeros, lat=np.zeros(241), lon=np.zeros(401)),
    )
    choice = real_ohc.select_file("na", t, fetch=archive)
    assert choice.file.name_day == date(2025, 7, 17)
    assert choice.age_days == 3
    assert choice.step_backs[0].reason.startswith("rejected:")
    assert "not the NA grid" in choice.step_backs[0].reason


def test_stepping_back_stops_after_the_stated_maximum(files):
    t = datetime(2024, 11, 25, 0, tzinfo=UTC)
    archive = _full_archive(files, date(2024, 11, 1), date(2024, 11, 30))
    for back in range(2, 2 + real_ohc.MAX_STEP_BACK_DAYS + 1):
        del archive.files[real_ohc.ohc_url("np", date(2024, 11, 25) - timedelta(days=back))]
    choice = real_ohc.select_file("np", t, fetch=archive)
    assert choice.file is None
    assert choice.age_days is None
    assert len(choice.step_backs) == real_ohc.MAX_STEP_BACK_DAYS + 1

    # NA still has its file, so the field has NA and reports NP missing.
    field = real_ohc.ohc_global(t, fetch=archive)
    np_meta, na_meta = field.metadata()["basins"]
    assert (np_meta["basin"], np_meta["available"]) == ("np", False)
    assert (na_meta["basin"], na_meta["available"], na_meta["age_days"]) == ("na", True, 2)
    assert math.isnan(real_ohc.ohc_at(20.0, 150.0, field))
    assert math.isfinite(real_ohc.ohc_at(25.0, -90.0, field))


def test_no_file_in_either_basin_raises():
    with pytest.raises(OhcUnavailable, match="no usable OHC file"):
        real_ohc.ohc_global(datetime(2022, 8, 1, tzinfo=UTC), fetch=Archive())


def test_a_fetch_failure_that_is_not_a_404_is_not_stepped_over(files):
    def flaky(url: str) -> bytes:
        raise OhcFetchError(f"GET {url} failed: HTTP 503")

    with pytest.raises(OhcFetchError, match="503"):
        real_ohc.select_file("na", datetime(2022, 8, 1, tzinfo=UTC), fetch=flaky)


def test_ohc_global_places_both_basins_and_reports_where_they_came_from(files):
    t = datetime(2022, 8, 3, 12, tzinfo=UTC)
    archive = _full_archive(files, date(2022, 7, 1), date(2022, 8, 31))
    field = real_ohc.ohc_global(t, fetch=archive)
    assert field.values.shape == (721, 1440)
    assert field.values.dtype == np.float32
    meta = field.metadata()
    json.dumps(meta)  # plain data
    assert [b["basin"] for b in meta["basins"]] == ["np", "na"]
    for b in meta["basins"]:
        assert b["name_day"] == b["creation_day"] == "2022-08-01"
        assert b["age_days"] == 2
        assert b["format"] == "netcdf3"
        assert b["degraded"] is False
    assert meta["valid_cells"] == int(np.isfinite(field.values).sum())
    na = _decode(files["na3"])
    assert real_ohc.ohc_at(25.0, -90.0, field) == float(na.ohc[100, 40])


def test_a_naive_cycle_time_is_utc():
    assert real_ohc.target_creation_day(datetime(2022, 8, 3, 18)) == date(2022, 8, 1)
    eastern = datetime(2022, 8, 3, 21, tzinfo=timezone(timedelta(hours=-5)))  # 08-04 02Z
    assert real_ohc.target_creation_day(eastern) == date(2022, 8, 2)


def test_the_date_rule_uses_the_availability_lag():
    from anemoi.data.availability import OHC_VALID_LAG

    assert OHC_VALID_LAG == timedelta(days=2)
    t = datetime(2023, 9, 10, 6, tzinfo=UTC)
    assert real_ohc.target_creation_day(t) == t.date() - OHC_VALID_LAG


# --- http_get against a local server -------------------------------------------


class _Handler(http.server.BaseHTTPRequestHandler):
    """Answers on the first path segment and ignores the rest, so a
    CoastWatch URL can be pointed here with its own path kept: a status
    code, ``ua`` (echoes the User-Agent), ``file`` (the served file with its
    Content-Length) or ``unsized`` (the file, ended by closing)."""

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass

    def do_GET(self) -> None:  # noqa: N802
        mode = self.path.strip("/").split("/", 1)[0]
        body: bytes = self.server.body  # type: ignore[attr-defined]
        if mode.isdigit():
            self.send_error(int(mode))
            return
        if mode == "ua":
            body = self.headers.get("User-Agent", "").encode()
        self.send_response(200)
        if mode != "unsized":
            self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(scope="module")
def server(files):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    srv.body = files["na3"]  # type: ignore[attr-defined]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


@pytest.fixture
def local(server, monkeypatch) -> str:
    """The local server's base URL, with any configured proxy bypassed."""
    for name in ("no_proxy", "NO_PROXY"):
        monkeypatch.setenv(name, "127.0.0.1")
    return server


def _via(local: str, mode: str) -> real_ohc.Fetch:
    """``http_get`` with every CoastWatch URL sent to the local server's
    ``mode``."""
    return lambda url: real_ohc.http_get(url.replace(real_ohc.BASE_URL, f"{local}/{mode}"))


def test_http_get_returns_the_body(local, files):
    assert real_ohc.http_get(f"{local}/file/x.nc") == files["na3"]
    assert real_ohc.http_get(f"{local}/unsized/x.nc") == files["na3"]


def test_only_a_404_is_not_published(local):
    with pytest.raises(OhcNotPublished):
        real_ohc.http_get(f"{local}/404/x.nc")
    for code in (403, 429, 500, 503):
        with pytest.raises(OhcFetchError, match=f"HTTP {code}") as err:
            real_ohc.http_get(f"{local}/{code}/x.nc")
        assert type(err.value) is OhcFetchError


def test_http_get_caps_the_download(local, files, monkeypatch):
    monkeypatch.setattr(real_ohc, "MAX_DOWNLOAD_BYTES", len(files["na3"]) - 1)
    for mode in ("file", "unsized"):
        with pytest.raises(OhcFetchError, match="more than"):
            real_ohc.http_get(f"{local}/{mode}/x.nc")


def test_http_get_sends_the_adapters_user_agent_unless_told_not_to(local):
    assert real_ohc.http_get(f"{local}/ua/x.nc") == b"anemoi-api/1.0"
    assert real_ohc.http_get(f"{local}/ua/x.nc", user_agent=None).startswith(b"Python-urllib/")


def test_over_http_only_a_404_is_stepped_over(local):
    t = datetime(2021, 9, 1, tzinfo=UTC)
    choice = real_ohc.select_file("na", t, fetch=_via(local, "file"))
    assert choice.file is not None and choice.age_days == 2
    choice = real_ohc.select_file("na", t, fetch=_via(local, "404"))
    assert choice.file is None
    assert [s.reason for s in choice.step_backs] == ["not published (404)"] * 4
    for code in (403, 429, 503):
        with pytest.raises(OhcFetchError, match=f"HTTP {code}") as err:
            real_ohc.select_file("na", t, fetch=_via(local, str(code)))
        assert type(err.value) is OhcFetchError


# --- network: real files ----------------------------------------------------

#: urllib's own User-Agent, not the adapter's default.
_plain_get = functools.partial(real_ohc.http_get, user_agent=None)


@pytest.mark.network
@pytest.mark.parametrize(
    ("basin", "name_day", "file_format", "shape", "fill_cells"),
    [
        ("na", date(2021, 8, 28), "netcdf3", (241, 401), 36_416),  # old chain
        ("np", date(2024, 8, 27), "netcdf3", (241, 721), 55_676),  # np14 v1r0
        ("na", date(2025, 8, 28), "hdf5", (241, 401), 36_416),  # na14 v1r1
    ],
)
def test_a_real_file_from_each_chain(basin, name_day, file_format, shape, fill_cells):
    f = real_ohc.fetch_ohc_file(basin, name_day, fetch=_plain_get)  # units checked on decode
    assert f.file_format == file_format
    assert f.ohc.shape == shape
    assert int(np.isnan(f.ohc).sum()) == fill_cells
    assert float(np.nanmin(f.ohc)) == 0.0
    assert float(np.nanmax(f.ohc)) < 300.0
    assert f.creation_day == real_ohc.creation_day(name_day)
    assert not f.degraded
    lat, lon, i, j = (25.0, -90.0, 100, 40) if basin == "na" else (20.0, 150.0, 80, 200)
    assert np.isfinite(f.ohc[i, j])
    assert real_ohc.place([f])[_row_col(lat, lon)] == f.ohc[i, j]


# --- network: SHIPS SOHC regression -------------------------------------------
#
# SHIPS' developmental SOHC is this product, bilinear at the best-track
# centre, from the file named for the calendar day before the case's UTC
# date (docs/skill_gap_plan.md Phase 3). It holds at open-ocean Atlantic
# cases of 2021-2022: all four NA corners valid and the centre not in a cell
# that touches the 80.0W column. SHIPS' AL file takes that column from NP,
# which holds 0.0 there over the Caribbean, so SOHC comes out low on both
# sides of 80.0W, not only west of it: Lisa (AL152022, 2022-11-01 06Z,
# 79.9W) reads 33 where NA alone gives 85.1 and NP's column over NA's 33.4.
# That leaves 555 of 702 cases (the Phase 0 count of 557 excluded only
# 80.0-80.25W, and Lisa and Nicole's 79.8W case are the difference).

SHIPS_AL_URL = (
    "https://rammb-data.cira.colostate.edu/ships/data/AL/lsdiaga_1982_2025_sat_ts_7day.txt"
)
#: Every record of the 7-day file is 183 lines and 33,003 bytes.
SHIPS_RECORD_BYTES = 33_003
#: Records 13148-13849 are AL 2021-2022 in the 2025 edition (posted
#: 2026-10-19); the window brackets them with room to spare, and the test
#: checks it does.
SHIPS_WINDOW = (13_100, 13_900)
SHIPS_MISSING = 9999
SOHC_TOLERANCE = 0.5
#: Cases whose bilinear cell touches 80.0W (west longitude, exclusive).
STRIP_80W = (79.75, 80.25)
#: Busiest case days per year until each year has this many cases; set
#: ANEMOI_OHC_SHIPS_ALL=1 to read every day (~125 files, ~350 MB).
SAMPLE_CASES_PER_YEAR = 50


@dataclass(frozen=True, slots=True)
class ShipsCase:
    storm_id: str
    time: datetime
    lat: float
    lon_w: float  # SHIPS gives degrees west, positive
    sohc: int  # kJ/cm2 at t=0, SHIPS_MISSING when absent

    @property
    def lon(self) -> float:
        return -self.lon_w

    @property
    def file_day(self) -> date:
        return self.time.date() - timedelta(days=1)


def parse_ships(blob: bytes) -> list[ShipsCase]:
    """Cases (HEAD..LAST blocks) in a slice of a SHIPS developmental file.
    The label is at columns 156:160; a row's t=0 value is its third 5-char
    field. A block cut off by either end of the slice is skipped."""
    cases: list[ShipsCase] = []
    head: str | None = None
    sohc: int | None = None
    for raw in blob.split(b"\n"):
        line = raw.decode("ascii", errors="replace")
        label = line[156:160]
        if label == "HEAD":
            head, sohc = line, None
        elif head is None:
            continue
        elif label == "SOHC":
            field = line[10:15].strip()
            sohc = int(field) if field else SHIPS_MISSING
        elif label == "LAST":
            vmax, lat, lon_w, mslp, storm_id = head[15:156].split()[:5]
            yy, mm, dd, hh = int(head[6:8]), int(head[8:10]), int(head[10:12]), int(head[13:15])
            when = datetime(2000 + yy if yy < 50 else 1900 + yy, mm, dd, hh, tzinfo=UTC)
            cases.append(ShipsCase(storm_id, when, float(lat), float(lon_w), sohc))
            head = None
    return cases


def ships_window() -> bytes:
    start, end = (n * SHIPS_RECORD_BYTES for n in SHIPS_WINDOW)
    req = urllib.request.Request(SHIPS_AL_URL, headers={"Range": f"bytes={start}-{end - 1}"})
    with urllib.request.urlopen(req, timeout=300) as resp:  # noqa: S310
        assert resp.status == 206, resp.status
        return resp.read()


def al_2021_2022(cases: list[ShipsCase]) -> list[ShipsCase]:
    years = [c.time.year for c in cases]
    assert min(years) < 2021 and max(years) > 2022, "the SHIPS window no longer brackets 2021-22"
    return [c for c in cases if c.storm_id.startswith("AL") and c.time.year in (2021, 2022)]


def open_ocean(cases: list[ShipsCase], na_file: real_ohc.OhcFile) -> list[ShipsCase]:
    """Cases whose four NA corners are valid (the fill mask is static, so
    any NA file decides) and whose cell does not touch the 80.0W column."""
    return [
        c for c in cases
        if math.isfinite(real_ohc.ohc_at(c.lat, c.lon, na_file))
        and not STRIP_80W[0] < c.lon_w < STRIP_80W[1]
    ]


def sample_days(cases: list[ShipsCase], per_year: int | None) -> list[date]:
    """The file days to read: all of them, or per year the busiest days
    (ties to the earlier day) until the year has ``per_year`` cases."""
    by_day: dict[date, int] = defaultdict(int)
    for c in cases:
        by_day[c.file_day] += 1
    if per_year is None:
        return sorted(by_day)
    chosen: list[date] = []
    for year in sorted({c.time.year for c in cases}):
        days = sorted((d for d in by_day if (d + timedelta(days=1)).year == year),
                      key=lambda d: (-by_day[d], d))
        taken = 0
        for d in days:
            if taken >= per_year:
                break
            chosen.append(d)
            taken += by_day[d]
    return sorted(chosen)


def compare(
    cases: list[ShipsCase], days: list[date], fetch: real_ohc.Fetch,
) -> list[tuple[ShipsCase, float]]:
    """``(case, ohc_at on the file named for the day before)`` for every
    case whose file day is in ``days``."""
    wanted = set(days)
    out: list[tuple[ShipsCase, float]] = []
    by_day: dict[date, list[ShipsCase]] = defaultdict(list)
    for c in cases:
        if c.file_day in wanted:
            by_day[c.file_day].append(c)
    for day in sorted(by_day):
        f = real_ohc.fetch_ohc_file("na", day, fetch=fetch)
        out.extend((c, real_ohc.ohc_at(c.lat, c.lon, f)) for c in by_day[day])
    return out


@pytest.mark.network
def test_sohc_equals_bilinear_ohc_on_the_file_named_for_the_day_before():
    cases = al_2021_2022(parse_ships(ships_window()))
    assert len(cases) == 702
    assert all(c.sohc != SHIPS_MISSING for c in cases)

    every = os.environ.get("ANEMOI_OHC_SHIPS_ALL") == "1"
    days = sample_days(cases, None)
    mask = real_ohc.fetch_ohc_file("na", days[0], fetch=_plain_get)
    usable = open_ocean(cases, mask)
    assert len(usable) == 555

    results = compare(usable, sample_days(usable, None if every else SAMPLE_CASES_PER_YEAR),
                      _plain_get)
    assert len(results) >= (555 if every else 100)
    far = [(c.storm_id, c.time.isoformat(), c.sohc, v) for c, v in results
           if not abs(v - c.sohc) <= SOHC_TOLERANCE]
    assert far == []
