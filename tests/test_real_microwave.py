"""Real RSS SSMIS microwave bytemap fetch/decode (data.real_microwave, #147).

The byte layout under test here was verified two independent ways before
writing any of this -- RSS's own reference Python reader (fetched directly
from ftp.remss.com:/ssmi/ssmi_support/python/) and their public "Gridded
Binary Files" documentation (https://remss.com/missions/ssmi/) -- see the
module docstring for the full citation. The network-marked test at the
bottom hits the real FTP server; skipped unless both ANEMOI_RUN_NETWORK_TESTS=1
and real RSS_FTP_USERNAME/RSS_FTP_PASSWORD are set (anonymous access was
discontinued by RSS, confirmed live), since CI has neither.
"""

from __future__ import annotations

import gzip
import os
from datetime import date

import numpy as np
import pytest

from anemoi.data.real_microwave import (
    SSMIS_SATELLITES,
    MicrowaveFetchError,
    RSSFtpCredentials,
    _bytemap_path,
    decode_ssmis_bytemap,
    fetch_and_decode_ssmis_daily,
)

_N_VARS = 5
_N_LAT = 720
_N_LON = 1440


def _make_bytemap(cell_overrides: dict[tuple[int, int, int, int], int] | None = None) -> bytes:
    """A real-shape (2, 5, 720, 1440) uint8 array, all zero except the
    given (pass, var, lat, lon) -> byte overrides, gzip'd like a real file."""
    bmap = np.zeros((2, _N_VARS, _N_LAT, _N_LON), dtype=np.uint8)
    for (pass_i, var_i, lat_i, lon_i), value in (cell_overrides or {}).items():
        bmap[pass_i, var_i, lat_i, lon_i] = value
    return gzip.compress(bmap.tobytes())


def test_bytemap_path_matches_the_real_verified_layout():
    expected = "/ssmi/f18/bmaps_v08/y2026/m09/f18_20260922v8.gz"
    assert _bytemap_path("f18", date(2026, 9, 22)) == expected


def test_bytemap_path_rejects_an_unknown_satellite():
    with pytest.raises(MicrowaveFetchError, match="unknown SSMIS satellite"):
        _bytemap_path("f99", date(2026, 9, 22))


def test_every_registered_satellite_produces_a_valid_path():
    for sat in SSMIS_SATELLITES:
        path = _bytemap_path(sat, date(2026, 1, 1))
        assert path.startswith(f"/ssmi/{sat}/bmaps_v08/")


def test_credentials_from_env_raises_a_clear_error_when_missing(monkeypatch):
    monkeypatch.delenv("RSS_FTP_USERNAME", raising=False)
    monkeypatch.delenv("RSS_FTP_PASSWORD", raising=False)
    with pytest.raises(MicrowaveFetchError, match="RSS_FTP_USERNAME"):
        RSSFtpCredentials.from_env()


def test_credentials_from_env_reads_real_values(monkeypatch):
    monkeypatch.setenv("RSS_FTP_USERNAME", "someone@example.com")
    monkeypatch.setenv("RSS_FTP_PASSWORD", "hunter2")
    creds = RSSFtpCredentials.from_env()
    assert creds.username == "someone@example.com"
    assert creds.password == "hunter2"


def test_decode_applies_the_real_scale_and_offset_per_variable():
    # byte 100 at wind_speed_mps (var index 1): 100 * 0.2 + 0.0 = 20.0 m/s
    # byte 100 at cloud_mm (var index 3): 100 * 0.01 - 0.05 = 0.95 mm
    raw = _make_bytemap({
        (0, 1, 10, 20): 100,
        (0, 3, 10, 20): 100,
    })
    result = decode_ssmis_bytemap(raw, "f18", date(2026, 9, 22))
    assert result.variables["wind_speed_mps"][0, 10, 20] == pytest.approx(20.0)
    assert result.variables["cloud_mm"][0, 10, 20] == pytest.approx(0.95)


def test_decode_masks_every_byte_above_250_as_missing():
    # 251 (missing-due-to-rain), 252 (ice), 253 (bad obs), 254 (no obs),
    # 255 (land) -- all real flag values, all must decode to NaN.
    raw = _make_bytemap({
        (0, 1, 0, i): value for i, value in enumerate([251, 252, 253, 254, 255])
    })
    result = decode_ssmis_bytemap(raw, "f18", date(2026, 9, 22))
    wind = result.variables["wind_speed_mps"][0, 0, :5]
    assert np.isnan(wind).all()


def test_decode_keeps_the_zero_pass_as_ascending_and_one_as_descending():
    raw = _make_bytemap({(0, 1, 5, 5): 50, (1, 1, 5, 5): 150})
    result = decode_ssmis_bytemap(raw, "f18", date(2026, 9, 22))
    wind = result.variables["wind_speed_mps"]
    assert wind[0, 5, 5] == pytest.approx(50 * 0.2)
    assert wind[1, 5, 5] == pytest.approx(150 * 0.2)


def test_decode_grid_matches_the_real_documented_cell_centres():
    raw = _make_bytemap()
    result = decode_ssmis_bytemap(raw, "f18", date(2026, 9, 22))
    # RSS's own docs: cell (0,0) is centred at -89.875 lat, 0.125 lon.
    assert result.lat[0] == pytest.approx(-89.875)
    assert result.lon[0] == pytest.approx(0.125)
    assert result.lat[-1] == pytest.approx(89.875)
    assert result.lon[-1] == pytest.approx(359.875)


def test_decode_raises_on_a_truncated_file_instead_of_silently_reshaping():
    truncated = gzip.compress(b"\x00" * 100)
    with pytest.raises(MicrowaveFetchError, match="expected"):
        decode_ssmis_bytemap(truncated, "f18", date(2026, 9, 22))


def test_decode_raises_on_invalid_gzip():
    with pytest.raises(MicrowaveFetchError, match="gzip"):
        decode_ssmis_bytemap(b"not gzip data", "f18", date(2026, 9, 22))


# --- network tests (real endpoint, opt-in, needs real credentials) ---------

_HAS_RSS_CREDENTIALS = bool(os.environ.get("RSS_FTP_USERNAME")) and bool(
    os.environ.get("RSS_FTP_PASSWORD")
)

needs_rss_credentials = pytest.mark.skipif(
    not _HAS_RSS_CREDENTIALS,
    reason="RSS_FTP_USERNAME/RSS_FTP_PASSWORD not set -- real account required, "
    "anonymous access discontinued",
)


@pytest.mark.network
@needs_rss_credentials
def test_fetch_and_decode_reads_a_real_recent_ssmis_file():
    from datetime import timedelta

    # Yesterday, not today -- today's file may not have finished uploading
    # yet (confirmed live: files land ~13:00-21:00 UTC for the prior day).
    yesterday = date.today() - timedelta(days=1)
    result = fetch_and_decode_ssmis_daily("f18", yesterday)
    assert result.variables["wind_speed_mps"].shape == (2, _N_LAT, _N_LON)
    valid = result.variables["wind_speed_mps"]
    valid = valid[~np.isnan(valid)]
    # Real global ocean wind speed climatology -- not exact, just physically sane.
    assert valid.size > 0
    assert 0.0 <= valid.mean() <= 20.0
