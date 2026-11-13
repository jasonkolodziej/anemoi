"""NHC's per-forecast official error files (`data.nhc_verification`).

The fixture copies the published file's header and column layout, with
constructed rows; the one test that reads NHC's real file is marked
``network``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from anemoi.data.nhc_verification import (
    OFFICIAL_ERRORS_FILES,
    OFFICIAL_ERRORS_URL,
    OfficialErrorsError,
    parse_official_errors,
)

PREAMBLE = """\
Verification statistics for:    EAST PAC 1989-2025
Model(s) verified:              OFCL
Min, max wind speed included:   00 200 kt.
Subtropical stage (if any) included.
Extratropical stage (if any) excluded.
Dissipation forecasts excluded.
Initial position domain:  00N-90N  140W-075W
A-decks taken from subdirectory:   data
B-decks taken from subdirectory:   data

"""
COLUMNS = (
    "Date/Time", "STMID", "F012", "F024", "Lat", "Lon", "WS",
    "000hT01", "012hT01", "024hT01", "048hT01", "000hI01", "012hI01", "024hI01", "048hI01",
)
ROWS = (
    ("24-08-2024/18:00:00", "EP072024", "1.00", "1.00", "17.6", "130.5", "85",
     "3.1", "18.7", "30.2", "-9999.0", "0.0", "-5.0", "10.0", "-9999.0"),
    ("25-08-2024/00:00:00", "EP072024", "1.00", "1.00", "17.8", "131.6", "90",
     "0.0", "22.0", "-9999.0", "55.5", "0.0", "5.0", "-9999.0", "-15.0"),
    ("25-08-2024/06:00:00", "EP072024", "short", "row"),
)
#: The published file is whitespace-aligned; the parser splits on runs of it.
TEXT = PREAMBLE + "\n".join("  ".join(fields) for fields in (COLUMNS, *ROWS)) + "\n"


def test_parse_official_errors_reads_columns_by_name_and_skips_missing_leads():
    errors = parse_official_errors(TEXT)
    t0 = datetime(2024, 8, 24, 18, tzinfo=UTC)
    t1 = datetime(2024, 8, 25, 0, tzinfo=UTC)
    assert errors.track_nm[("EP072024", t0, 12)] == 18.7
    assert errors.track_nm[("EP072024", t1, 48)] == 55.5
    assert ("EP072024", t0, 48) not in errors.track_nm  # -9999: not verified
    assert ("EP072024", t1, 24) not in errors.track_nm
    assert errors.intensity_kt[("EP072024", t0, 24)] == 10.0  # signed: too strong
    assert errors.intensity_kt[("EP072024", t1, 48)] == -15.0
    assert len(errors.track_nm) == 6


def test_parse_official_errors_reads_the_stated_initial_position_domain():
    errors = parse_official_errors(TEXT)
    assert errors.domain == (0.0, 90.0, -140.0, -75.0)
    assert errors.in_domain(17.6, -130.5)
    assert not errors.in_domain(17.6, -140.5)  # CPHC's area: not in NHC's file


def test_parse_official_errors_without_a_domain_line_covers_everything():
    text = "\n".join(ln for ln in TEXT.splitlines() if "domain" not in ln)
    errors = parse_official_errors(text)
    assert errors.domain is None and errors.in_domain(10.0, 170.0)


def test_parse_official_errors_rejects_a_file_without_the_column_header():
    with pytest.raises(OfficialErrorsError):
        parse_official_errors("<html>Not Found</html>\n")


@pytest.mark.network
def test_real_atlantic_file_gives_nhcs_published_2024_48h_error():
    """NHC's own figure for the 2024 Atlantic official 48 h track error is
    45.4 n mi over 214 forecasts; the parsed file must give it back."""
    from anemoi.data.adeck_source import _get

    text = _get(OFFICIAL_ERRORS_URL.format(name=OFFICIAL_ERRORS_FILES["AL"])).decode("ascii")
    errors = parse_official_errors(text)
    values = [
        v for (storm, _t, lead), v in errors.track_nm.items()
        if lead == 48 and storm.endswith("2024")
    ]
    assert len(values) == 214
    assert sum(values) / len(values) == pytest.approx(45.4, abs=0.05)
    assert errors.domain == (0.0, 90.0, -110.0, 0.0)
