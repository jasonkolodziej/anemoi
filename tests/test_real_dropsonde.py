"""Real NOAA/AFRC dropsonde fetch/decode (data.real_dropsonde, #147).

Requires the optional `gridded` extra (eccodes). The network-marked tests
hit the real, verified-working HRD FTP archive but are skipped by default
-- set ANEMOI_RUN_NETWORK_TESTS=1 to run them. Everything else exercises
path construction and the missing-value masking logic against small
constructed arrays, no network/eccodes needed for those.
"""

from __future__ import annotations

import numpy as np
import pytest

try:
    import eccodes
except (ImportError, RuntimeError) as exc:
    _ECCODES_ERROR = str(exc)
else:
    _ECCODES_ERROR = None

NEEDS_ECCODES = pytest.mark.skipif(
    _ECCODES_ERROR is not None, reason=f"eccodes unavailable: {_ECCODES_ERROR}"
)

from anemoi.data.real_dropsonde import (  # noqa: E402
    _CODES_MISSING_DOUBLE,
    _CODES_MISSING_LONG,
    _mask_missing,
    _mission_dir,
    fetch_and_parse_dropsonde_mission,
    list_dropsonde_missions,
    parse_dropsonde_mission_tarball,
)

pytestmark = pytest.mark.gridded


def test_mission_dir_matches_the_real_verified_layout():
    assert _mission_dir(2026) == "/hrd/pub/data/dropsonde/HURR26/operproc"
    assert _mission_dir(2005) == "/hrd/pub/data/dropsonde/HURR05/operproc"


def test_mask_missing_turns_the_double_sentinel_into_nan():
    raw = np.array([1013.0, -1e100, 850.0])
    out = _mask_missing(raw)
    assert out[0] == pytest.approx(1013.0)
    assert np.isnan(out[1])
    assert out[2] == pytest.approx(850.0)


def test_mask_missing_turns_the_long_sentinel_into_nan():
    raw = np.array([180.0, 2147483647.0])
    out = _mask_missing(raw)
    assert out[0] == pytest.approx(180.0)
    assert np.isnan(out[1])


def test_mask_missing_leaves_real_values_untouched():
    raw = np.array([0.0, -50.0, 12345.6])
    out = _mask_missing(raw)
    np.testing.assert_array_equal(out, raw)


@NEEDS_ECCODES
def test_hardcoded_missing_sentinels_match_the_real_eccodes_constants():
    # Cross-check against eccodes' own constants rather than trusting the
    # hardcoded copy drifts never happen.
    assert _CODES_MISSING_DOUBLE == eccodes.CODES_MISSING_DOUBLE
    assert _CODES_MISSING_LONG == eccodes.CODES_MISSING_LONG


def test_parse_mission_tarball_raises_on_a_non_tar_blob():
    from anemoi.data.real_dropsonde import DropsondeFetchError

    with pytest.raises(DropsondeFetchError, match="not a valid tar"):
        parse_dropsonde_mission_tarball("fake_mission", b"not a real tarball")


# --- network tests (real endpoint, opt-in only) -----------------------------


@pytest.mark.network
def test_list_dropsonde_missions_reads_the_real_archive():
    missions = list_dropsonde_missions(2026)
    assert len(missions) > 0
    for mission_id in missions:
        assert mission_id[:8].isdigit()  # YYYYMMDD prefix, real convention


@pytest.mark.network
@NEEDS_ECCODES
def test_fetch_and_parse_reads_a_real_mission_end_to_end():
    missions = list_dropsonde_missions(2026)
    assert missions, "no real 2026 missions found to test against"
    profiles = fetch_and_parse_dropsonde_mission(2026, missions[0])
    assert len(profiles) > 0

    p = profiles[0]
    assert p.release_time.year == 2026
    valid_pressure = p.pressure_pa[~np.isnan(p.pressure_pa)]
    assert valid_pressure.size > 0
    # Plausible real surface-to-flight-level pressure range in Pa.
    assert 40000.0 < valid_pressure.max() <= 105000.0
    # Real profile is surface-first: pressure decreases monotonically.
    assert np.all(np.diff(valid_pressure) <= 1.0)
