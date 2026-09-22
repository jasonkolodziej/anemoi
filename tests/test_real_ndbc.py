"""Real NDBC buoy/C-MAN realtime2 fetch/parse (data.real_ndbc, #147).

Offline tests fake a real realtime2 response (format-compliant, same
"constructed station, not a transcription" convention as test_atcf.py's
fixtures -- what's under test is the parser, not any specific station's
real readings). The network-marked test at the bottom hits the real
endpoint; skipped unless ANEMOI_RUN_NETWORK_TESTS=1.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from anemoi.data.real_ndbc import (
    NdbcFetchError,
    fetch_ndbc_realtime2,
    parse_ndbc_realtime2,
)

# Real realtime2 format: two header rows (names, units) then newest-first
# data rows, whitespace-separated, "MM" for a missing value.
REALTIME2_FIXTURE = """\
#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS PTDY  TIDE
#yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC  nmi  hPa    ft
2026 09 22 22 10 270  3.0  4.0    MM    MM    MM  MM 1011.9  27.6  28.8  24.9   MM   MM    MM
2026 09 22 22 00 260  3.0  3.0   0.8   7.0   5.6  84 1012.0  27.8  28.8  24.9   MM -0.4    MM
"""


def test_parses_real_rows_newest_first():
    obs = parse_ndbc_realtime2(REALTIME2_FIXTURE, "41002")
    assert len(obs) == 2
    assert obs[0].valid_time == datetime(2026, 9, 22, 22, 10, tzinfo=UTC)
    assert obs[1].valid_time == datetime(2026, 9, 22, 22, 0, tzinfo=UTC)


def test_missing_sentinel_becomes_none_not_a_fabricated_zero():
    obs = parse_ndbc_realtime2(REALTIME2_FIXTURE, "41002")
    assert obs[0].wave_height_m is None
    assert obs[0].tide_ft is None


def test_real_values_are_parsed_as_floats():
    obs = parse_ndbc_realtime2(REALTIME2_FIXTURE, "41002")
    assert obs[1].wave_height_m == pytest.approx(0.8)
    assert obs[1].dominant_wave_period_s == pytest.approx(7.0)
    assert obs[1].pressure_tendency_hpa == pytest.approx(-0.4)


def test_station_id_is_carried_through():
    obs = parse_ndbc_realtime2(REALTIME2_FIXTURE, "41002")
    assert all(o.station_id == "41002" for o in obs)


def test_a_row_with_the_wrong_column_count_is_skipped_not_fatal():
    text = REALTIME2_FIXTURE + "2026 09 22 21 50 malformed-short-row\n"
    obs = parse_ndbc_realtime2(text, "41002")
    assert len(obs) == 2  # the malformed row is skipped, not raised on


def test_raises_when_there_is_no_header_row():
    with pytest.raises(NdbcFetchError, match="no header row"):
        parse_ndbc_realtime2("not a real ndbc file\n", "41002")


def test_a_station_missing_wave_columns_still_parses():
    # A land C-MAN station's real column set can omit wave sensors entirely
    # (confirmed live against a real station) -- header-driven parsing
    # must not assume every column is always present.
    text = (
        "#YY  MM DD hh mm WDIR WSPD GST   PRES  ATMP  DEWP  VIS PTDY  TIDE\n"
        "#yr  mo dy hr mn degT m/s  m/s    hPa  degC  degC  nmi  hPa    ft\n"
        "2026 09 22 22 10 300  2.1  3.6 1011.7  29.8  23.1   MM   MM    MM\n"
    )
    obs = parse_ndbc_realtime2(text, "CDRF1")
    assert obs[0].wind_speed_mps == pytest.approx(2.1)
    assert obs[0].wave_height_m is None  # never in this station's column set at all


# --- network tests (real endpoint, opt-in only) -----------------------------


@pytest.mark.network
def test_fetch_ndbc_realtime2_reads_a_real_station():
    text = fetch_ndbc_realtime2("41002")
    obs = parse_ndbc_realtime2(text, "41002")
    assert len(obs) > 0
    # Real, live data -- assert shape/sanity, not a specific reading.
    assert obs[0].valid_time.year == datetime.now(UTC).year
    if obs[0].wind_speed_mps is not None:
        assert 0.0 <= obs[0].wind_speed_mps <= 100.0
