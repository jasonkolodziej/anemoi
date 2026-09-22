"""Real NOAA GEFS ensemble member fetch (data.real_ensemble, #147).

Requires the optional `gridded` extra (eccodes/requests, same as GDAS).
The network-marked tests hit the real, verified-working AWS Open Data
GEFS archive but are skipped by default -- set ANEMOI_RUN_NETWORK_TESTS=1
to run them. Everything else exercises path construction and member
validation, no network needed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

try:
    import eccodes  # noqa: F401
except (ImportError, RuntimeError) as exc:
    _ECCODES_ERROR = str(exc)
else:
    _ECCODES_ERROR = None

NEEDS_ECCODES = pytest.mark.skipif(
    _ECCODES_ERROR is not None, reason=f"eccodes unavailable: {_ECCODES_ERROR}"
)

from anemoi.data.real_ensemble import (  # noqa: E402
    GEFS_PERTURBED_MEMBERS,
    _gefs_member_url,
    fetch_gefs_ensemble_grib2_fields,
    fetch_gefs_member_grib2_fields,
)

pytestmark = pytest.mark.gridded

T = datetime(2026, 9, 22, tzinfo=UTC)


def test_perturbed_member_url_matches_the_real_verified_path():
    url = _gefs_member_url(T, member=1, lead_hours=6)
    assert url == (
        "https://noaa-gefs-pds.s3.amazonaws.com/gefs.20260922/00/atmos/pgrb2ap5/"
        "gep01.t00z.pgrb2a.0p50.f006"
    )


def test_control_member_zero_uses_gec00_not_gep00():
    url = _gefs_member_url(T, member=0, lead_hours=6)
    assert "gec00" in url
    assert "gep00" not in url


def test_member_out_of_range_raises():
    with pytest.raises(ValueError, match="member must be"):
        _gefs_member_url(T, member=31, lead_hours=6)
    with pytest.raises(ValueError, match="member must be"):
        _gefs_member_url(T, member=-1, lead_hours=6)


def test_thirty_perturbed_members_are_registered():
    assert GEFS_PERTURBED_MEMBERS == tuple(range(1, 31))


# --- network tests (real endpoint, opt-in only) -----------------------------


@pytest.mark.network
@NEEDS_ECCODES
def test_fetch_gefs_member_reads_the_real_noaa_archive():
    # A few hours back from "now", floored to a real synoptic hour, so the
    # cycle is guaranteed published (GEFS runs 4x/day at 00/06/12/18Z).
    now = datetime.now(UTC)
    target = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=12)
    target = target.replace(hour=(target.hour // 6) * 6)

    fields = fetch_gefs_member_grib2_fields(target, member=1, lead_hours=6)
    assert ("HGT", 500) in fields
    # Plausible real 500 mb geopotential height in meters, same bound
    # test_real_gridded.py uses for the equivalent GDAS field.
    assert 4000.0 < fields[("HGT", 500)].mean() < 6200.0


@pytest.mark.network
@NEEDS_ECCODES
def test_fetch_gefs_ensemble_reads_multiple_real_distinct_members():
    now = datetime.now(UTC)
    target = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=12)
    target = target.replace(hour=(target.hour // 6) * 6)

    ensemble = fetch_gefs_ensemble_grib2_fields(target, members=(0, 1, 2))
    assert set(ensemble) == {0, 1, 2}
    means = {m: fields[("HGT", 500)].mean() for m, fields in ensemble.items()}
    # Real ensemble members must be distinct fetches, not the same file
    # three times -- a real ensemble has real spread, even if small.
    assert len(set(means.values())) == 3
