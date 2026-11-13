"""ATCF a-deck parser (`data.atcf.parse_adeck`) and the a-deck cache
(`data.adeck_source`).

The fixture rows follow the real archive's layout (BASIN, CY, DTG, TECHNUM,
TECH, TAU, LAT, LON, VMAX, MSLP, TY, RAD, ...), including the quirks the
parser exists for -- wind-radii repeats, ``0N, 0W`` and ``VMAX 0`` sentinels,
an east longitude, rows from another cyclone -- but describe a constructed
storm. The fetch tests inject the fetcher; the one test that reaches NHC is
marked ``network``.
"""

from __future__ import annotations

import gzip
import threading
import time
from datetime import UTC, datetime

import pytest

from anemoi.data import adeck_source
from anemoi.data.adeck_source import (
    ARCHIVE_URL,
    MAX_WORKERS,
    adeck_name,
    adeck_path,
    adeck_urls,
    fetch_adecks,
    read_adeck,
    read_cached_adecks,
    read_cached_official_errors,
)
from anemoi.data.atcf import AtcfError, parse_adeck
from anemoi.data.atcf_archive import ADECK_URL, NotPublished
from anemoi.data.nhc_verification import OfficialErrorsError

T0 = datetime(1999, 8, 25, 12, tzinfo=UTC)

ADECK = """\
AL, 01, 1999082512, 01, CARQ,  -6, 126N,  362W,  45,    0, TS,  34, AAA,    0,    0,    0,    0,
AL, 01, 1999082512, 01, CARQ,   0, 132N,  371W,  55,  992, TS,  34, NEQ,   60,   60,   40,   50,
AL, 01, 1999082512, 01, CARQ,   0, 132N,  371W,  55,  992, TS,  50, NEQ,   30,   30,    0,    0,
AL, 01, 1999082512, 03, OFCL,  12, 140N,  385W,  60,  988, TS,  34, NEQ,   70,   60,   40,   60,
AL, 01, 1999082512, 03, OFCL,  12, 140N,  385W,  60,  988, TS,  50, NEQ,   30,   30,    0,    0,
AL, 01, 1999082512, 03, OFCL,  12, 141N,  385W,  60,  988, TS,  64, NEQ,    0,    0,    0,    0,
AL, 01, 1999082512, 03, OFCL,  24, 150N,  400W,  70,  980, HU,  34, NEQ,   80,   70,   50,   70,
AL, 01, 1999082512, 03, OFCO,  24, 151N,  401W,  65,  982, HU,  34, NEQ,   80,   70,   50,   70,
AL, 01, 1999082512, 03, AVNI,  12, 139N,  384W,  58,    0,   ,  34, NEQ,    0,    0,    0,    0,
AL, 01, 1999082512, 03, CLP5,  12, 138N,  383W,   0,    0,   ,
AL, 01, 1999082512, 03, IVCN,  12,   0N,    0W,  61,    0,   ,
AL, 01, 1999082512, 03, EMXI,  12, 452N,   25E,  50,    0,   ,
AL, 01, 1999082512, 03, EMXI,  24, 455N, 1805W,  45,    0,   ,
CP, 01, 1999082518, 03, OFCL,  12, 145N,  395W,  65,  985, HU,  34, NEQ,   70,   60,   40,   60,
AL, 02, 1999082512, 03, OFCL,  12, 200N,  500W,  30, 1005, TD,  34, NEQ,    0,    0,    0,    0,
AL, 01, 1999082515, 03, OFCL,  12, 140N,  385W,  60,  988, TS,  34, NEQ,    0,    0,    0,    0,
AL, 01, 19990825, 03, OFCL,  12, 140N,  385W,  60,
AL, 01, 1999082512, 03, OFCL,  36, 15XN,  410W,  75,  975, HU,
AL, 01, 1999082512, 03, OFCL

"""


def test_parse_adeck_keeps_the_first_of_each_point_and_counts_disagreeing_repeats():
    adeck = parse_adeck(ADECK, "AL011999")
    point = adeck.get("OFCL", T0, 12)
    assert (point.lat, point.lon, point.max_wind_kt, point.min_pressure_mb) == (
        14.0, -38.5, 60.0, 988.0,
    )
    # the 50 kt repeat agrees with the 34 kt row; the 64 kt one does not
    assert adeck.conflicts == {"OFCL": 1}
    assert adeck.get("CARQ", T0, 0).min_pressure_mb == 992.0
    assert adeck.get("CARQ", T0, -6).min_pressure_mb is None  # MSLP 0: not given


def test_parse_adeck_reads_sentinels_as_absent_never_as_zero():
    adeck = parse_adeck(ADECK, "AL011999")
    clp5 = adeck.get("CLP5", T0, 12)
    assert clp5.has_position and clp5.max_wind_kt is None  # VMAX 0: track only
    ivcn = adeck.get("IVCN", T0, 12)
    assert not ivcn.has_position and ivcn.lat is None and ivcn.max_wind_kt == 61.0


def test_parse_adeck_converts_tenths_and_hemispheres_and_wraps_longitude():
    adeck = parse_adeck(ADECK, "AL011999")
    east = adeck.get("EMXI", T0, 12)
    assert (east.lat, east.lon) == (45.2, 2.5)
    past_the_dateline = adeck.get("EMXI", T0, 24)
    assert past_the_dateline.lon == pytest.approx(179.5)  # 180.5W is 179.5E


def test_parse_adeck_matches_rows_by_cyclone_number_not_basin_column():
    adeck = parse_adeck(ADECK, "AL011999")
    # A CP row for cyclone 01 in AL01's own file is kept, and counted.
    assert adeck.get("OFCL", datetime(1999, 8, 25, 18, tzinfo=UTC), 12) is not None
    assert adeck.n_basin_mismatch == 1
    # Cyclone 02's row is dropped, and counted.
    assert adeck.n_other_storm == 1
    assert all(p.lat != 20.0 for p in adeck.points.values())


def test_parse_adeck_counts_unreadable_rows_instead_of_raising():
    adeck = parse_adeck(ADECK, "AL011999")
    # off-synoptic DTG, eight-digit DTG, malformed latitude, a bare prefix row
    assert adeck.n_skipped == 4
    assert adeck.n_rows == len([ln for ln in ADECK.splitlines() if ln.strip()])
    assert adeck.get("OFCL", T0, 36) is None


def test_parse_adeck_technique_filter_reads_only_what_is_asked():
    adeck = parse_adeck(ADECK, "AL011999", techniques={"AVNI", "OFCO"})
    assert adeck.techniques() == ("AVNI", "OFCO")
    assert adeck.init_times("OFCO") == frozenset({T0})
    assert adeck.n_skipped == 0  # the unreadable rows are all OFCL's


def test_parse_adeck_rejects_a_bad_storm_id_and_text_with_no_record():
    with pytest.raises(AtcfError):
        parse_adeck(ADECK, "AL01199")
    with pytest.raises(AtcfError):
        parse_adeck("\n\nnot an a-deck\n", "AL011999")


def test_adeck_names_urls_and_paths_come_only_from_valid_storm_ids(tmp_path):
    assert adeck_name("AL092024") == "aal092024.dat.gz"
    assert adeck_urls("EP072024") == (
        ARCHIVE_URL.format(year="2024", storm="ep072024"),
        ADECK_URL.format(storm="ep072024"),
    )
    assert adeck_path(tmp_path, "CP012024") == tmp_path / "acp012024.dat.gz"
    for bad in ("../etc/passwd", "al092024", "AL09202"):
        with pytest.raises(AtcfError):
            adeck_name(bad)


class _FakeNhc:
    """A fetcher over a dict of URL -> bytes: anything else is a 404."""

    def __init__(self, files: dict[str, bytes], *, fail: set[str] = frozenset()):
        self.files = files
        self.fail = fail
        self.calls: list[str] = []
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def __call__(self, url: str) -> bytes:
        with self._lock:
            self.calls.append(url)
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.01)
            if url in self.fail:
                raise TimeoutError("timed out")
            if url not in self.files:
                raise NotPublished(url)
            return self.files[url]
        finally:
            with self._lock:
                self.active -= 1


def _archive(storm_id: str) -> str:
    return adeck_urls(storm_id)[0]


def _errors_url(basin: str) -> str:
    return adeck_source.OFFICIAL_ERRORS_URL.format(name=adeck_source.OFFICIAL_ERRORS_FILES[basin])


#: Bodies of the two kinds of file, as far as `fetch_adecks` checks them.
ARCHIVED = gzip.compress(b"archived")
ERRORS = b"Date/Time  STMID  012hT01\n"
#: What a server can send with status 200 instead of the file.
ERROR_PAGE = b"<html>oops</html>"


def test_fetch_adecks_skips_cached_files_falls_back_and_records_each_outcome(tmp_path):
    (tmp_path / "aal012024.dat.gz").write_bytes(b"cached")
    nhc = _FakeNhc(
        {
            _archive("AL022024"): ARCHIVED,
            adeck_urls("AL032024")[1]: gzip.compress(b"current season"),
            _errors_url("AL"): ERRORS,
        },
        fail={_archive("EP012024")},
    )
    report = fetch_adecks(
        ["AL012024", "AL022024", "AL032024", "AL042024", "EP012024", "AL022024"],
        tmp_path, fetch=nhc,
    )
    assert report.cached == ["aal012024.dat.gz"]
    assert report.fetched["aal022024.dat.gz"] == _archive("AL022024")
    assert report.fetched["aal032024.dat.gz"] == adeck_urls("AL032024")[1]
    assert sorted(report.not_published) == sorted(
        ["aal042024.dat.gz", adeck_source.OFFICIAL_ERRORS_FILES["EP"]]
    )
    assert "TimeoutError" in report.failed["aep012024.dat.gz"]
    assert (tmp_path / "aal022024.dat.gz").read_bytes() == ARCHIVED
    assert (tmp_path / "aal012024.dat.gz").read_bytes() == b"cached"
    assert not list(tmp_path.glob("*.part"))
    assert _archive("AL012024") not in nhc.calls
    assert nhc.calls.count(_archive("AL022024")) == 1  # a repeated id is fetched once


def test_fetch_adecks_never_runs_more_than_four_requests(tmp_path):
    storms = [f"AL{n:02d}2024" for n in range(1, 13)]
    nhc = _FakeNhc({_archive(s): ARCHIVED for s in storms})
    fetch_adecks(storms, tmp_path, fetch=nhc, max_workers=32, official_errors=False)
    assert MAX_WORKERS == 4
    assert 1 <= nhc.max_active <= MAX_WORKERS
    assert len(nhc.calls) == len(storms)
    with pytest.raises(ValueError):
        fetch_adecks(storms, tmp_path, fetch=nhc, max_workers=0)


def test_fetch_adecks_does_not_cache_a_body_that_is_not_the_file(tmp_path):
    nhc = _FakeNhc({_archive("AL012024"): ERROR_PAGE, _errors_url("AL"): ERROR_PAGE})
    report = fetch_adecks(["AL012024"], tmp_path, fetch=nhc)
    assert set(report.failed) == {"aal012024.dat.gz", adeck_source.OFFICIAL_ERRORS_FILES["AL"]}
    assert "not an a-deck" in report.failed["aal012024.dat.gz"]
    assert "Date/Time" in report.failed[adeck_source.OFFICIAL_ERRORS_FILES["AL"]]
    assert list(tmp_path.iterdir()) == []
    # Nothing was kept, so the next run asks again rather than calling it cached.
    nhc.files = {_archive("AL012024"): ARCHIVED, _errors_url("AL"): ERRORS}
    again = fetch_adecks(["AL012024"], tmp_path, fetch=nhc)
    assert not again.failed and not again.cached and len(again.fetched) == 2


def test_a_cached_error_file_that_is_not_nhcs_is_named_with_the_way_out(tmp_path):
    name = adeck_source.OFFICIAL_ERRORS_FILES["EP"]
    (tmp_path / name).write_bytes(ERROR_PAGE)
    with pytest.raises(OfficialErrorsError, match=f"{name}.*run `anemoi adeck-fetch` again"):
        read_cached_official_errors(tmp_path)
    (tmp_path / name).write_bytes(ERRORS)
    errors, (record,) = read_cached_official_errors(tmp_path)
    assert set(errors) == {"EP"} and record["file"] == name


def test_fetch_adecks_refuses_an_id_that_is_not_an_atcf_storm_id(tmp_path):
    with pytest.raises(AtcfError):
        fetch_adecks(["../../x"], tmp_path, fetch=_FakeNhc({}))


def test_read_cached_adecks_reads_gzip_and_records_missing_and_unreadable(tmp_path):
    with gzip.open(tmp_path / "aal011999.dat.gz", "wt") as fh:
        fh.write(ADECK)
    (tmp_path / "aal021999.dat.gz").write_bytes(b"not gzip at all")
    cached = read_cached_adecks(tmp_path, ["AL011999", "AL021999", "AL031999"], {"OFCL"})
    assert set(cached.adecks) == {"AL011999"}
    assert cached.adecks["AL011999"].techniques() == ("OFCL",)
    assert cached.missing == ["AL031999"]
    assert "AL021999" in cached.unreadable
    (record,) = cached.records
    assert record["storm_id"] == "AL011999" and len(record["sha256"]) == 64
    assert record["n_other_storm"] == 1 and record["conflicts"] == {"OFCL": 1}
    assert read_adeck(tmp_path / "aal011999.dat.gz", "AL011999").get("OFCL", T0, 12) is not None


@pytest.mark.network
def test_real_archived_adeck_carries_the_default_techniques(tmp_path):
    """NHC's 2024 archive: Alberto's a-deck has every technique the default
    comparison reads, at the leads it is scored on."""
    report = fetch_adecks(["AL012024"], tmp_path, official_errors=False)
    assert not report.failed and not report.not_published
    adeck = read_adeck(adeck_path(tmp_path, "AL012024"), "AL012024")
    for tech in ("OFCL", "AVNI", "AVNO", "EMXI", "EMX2", "OCD5", "XTRP", "CARQ"):
        assert tech in adeck.techniques(), tech
    init = datetime(2024, 6, 19, 12, tzinfo=UTC)
    assert adeck.get("OFCL", init, 12).has_position
    # AVNO-6 reads the run 6 h earlier at tau + 6: it must exist there
    assert adeck.get("AVNO", datetime(2024, 6, 19, 6, tzinfo=UTC), 18) is not None
