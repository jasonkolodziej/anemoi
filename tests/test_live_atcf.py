"""Live current-storm ingestion (real-time NHC feed, data.live_atcf).

Offline tests fake ``live_atcf._get`` (the one function that talks to the
network) with format-compliant fixture text -- same "constructed storm, not
a transcription" convention as ``test_atcf.py``'s fixtures, since what's
under test here is the fetch-orchestration/degradation logic, not the
parsers themselves (already covered by test_atcf.py). Real endpoint
coverage is network-marked, opt-in only, at the bottom -- see
test_real_gridded.py for the same pattern.
"""

from __future__ import annotations

import pytest

from anemoi.data import live_atcf
from anemoi.data.live_atcf import (
    LiveAtcfError,
    fetch_current_storm_ids,
    fetch_current_storms,
    fetch_live_track,
    fetch_live_tracks,
)

CURRENT_STORMS_FIXTURE = """\
{"activeStorms": [{"id": "al992026", "name": "TEST"}, {"id": "al982026", "name": "OTHER"}]}
"""

# Same fixture convention as test_atcf.py's TCVITALS_ONE -- out of order and
# with one off-synoptic row, to prove fetch_live_track sorts/dedupes/drops.
TCVITALS_ARCH_ONE = (
    "NHC 99L TEST      20260921 0600 210N 0700W 270 046 0995 1012 0300 26 050\n"
    "NHC 99L TEST      20260920 1200 200N 0690W 270 046 1000 1012 0300 18 050\n"
    "NHC 99L TEST      20260920 1500 201N 0692W 270 046 0999 1012 0300 18 050\n"  # off-synoptic
)


def test_fetch_current_storm_ids_parses_and_uppercases(monkeypatch):
    monkeypatch.setattr(live_atcf, "_get", lambda url: CURRENT_STORMS_FIXTURE)
    assert fetch_current_storm_ids() == ["AL992026", "AL982026"]


def test_fetch_current_storms_pairs_ids_with_real_names(monkeypatch):
    monkeypatch.setattr(live_atcf, "_get", lambda url: CURRENT_STORMS_FIXTURE)
    assert fetch_current_storms() == [("AL992026", "TEST"), ("AL982026", "OTHER")]


def test_fetch_current_storm_ids_raises_on_malformed_json(monkeypatch):
    monkeypatch.setattr(live_atcf, "_get", lambda url: "not json")
    with pytest.raises(LiveAtcfError, match="not valid JSON"):
        fetch_current_storm_ids()


def test_fetch_live_track_sorts_dedupes_and_drops_off_synoptic(monkeypatch):
    monkeypatch.setattr(live_atcf, "_get", lambda url: TCVITALS_ARCH_ONE)
    track = fetch_live_track("AL992026")
    assert track.storm_id == "AL992026"
    assert len(track.fixes) == 2  # the off-synoptic 1500Z row is dropped
    assert [f.valid_time.hour for f in track.fixes] == [12, 6]  # in ascending order
    assert track.quality.value == "working"
    assert track.name is None  # TC-Vitals itself carries no name


def test_fetch_live_track_carries_the_name_passed_in(monkeypatch):
    # TC-Vitals bulletins have no name field -- fetch_live_tracks passes one
    # through from CurrentStorms.json instead (see the test below).
    monkeypatch.setattr(live_atcf, "_get", lambda url: TCVITALS_ARCH_ONE)
    track = fetch_live_track("AL992026", name="Fay")
    assert track.name == "Fay"


def test_fetch_live_track_raises_when_nothing_parses(monkeypatch):
    # Only the off-synoptic row -- parse_tcvitals drops it, leaving no fixes.
    monkeypatch.setattr(
        live_atcf, "_get",
        lambda url: "NHC 99L TEST      20260920 1500 201N 0692W 270 046 0999 1012 0300 18 050\n",
    )
    with pytest.raises(LiveAtcfError, match="no parseable fixes"):
        fetch_live_track("AL992026")


def test_fetch_live_tracks_skips_a_storm_whose_own_fetch_fails(monkeypatch):
    """fetch_live_tracks must be fault-isolated per storm -- one storm's
    real fetch/parse failure (a 404, a malformed bulletin) must not drop
    every other currently-active storm from the result."""
    monkeypatch.setattr(live_atcf, "_get", lambda url: CURRENT_STORMS_FIXTURE)

    def fake_fetch_live_track(storm_id, name=None):
        if storm_id == "AL982026":
            raise LiveAtcfError("simulated 404")
        return live_atcf.Track(
            storm_id=storm_id,
            fixes=(
                live_atcf.parse_tcvitals(
                    "NHC 99L TEST      20260921 0600 210N 0700W 270 046 0995 1012 0300 26 050\n"
                )[0],
            ),
            name=name,
        )

    monkeypatch.setattr(live_atcf, "fetch_live_track", fake_fetch_live_track)
    tracks = fetch_live_tracks()
    assert [t.storm_id for t in tracks] == ["AL992026"]
    assert tracks[0].name == "TEST"  # threaded through from CurrentStorms.json


def test_fetch_live_tracks_returns_empty_when_index_unreachable(monkeypatch):
    def raise_error(url):
        raise LiveAtcfError("simulated network failure")

    monkeypatch.setattr(live_atcf, "_get", raise_error)
    assert fetch_live_tracks() == []


# --- network tests (real endpoints, opt-in only) ----------------------------


@pytest.mark.network
def test_fetch_current_storm_ids_reads_the_real_nhc_index():
    ids = fetch_current_storm_ids()
    # Count/content changes daily (it's whatever NHC is tracking right
    # now) -- assert shape, not specific storms: AL/EP/CP/WP/SH basin
    # code + 2-digit cyclone number + 4-digit year.
    for storm_id in ids:
        assert storm_id[:2] in {"AL", "EP", "CP", "WP", "SH"}
        assert storm_id[2:4].isdigit()
        assert storm_id[4:].isdigit() and len(storm_id[4:]) == 4


@pytest.mark.network
def test_fetch_live_tracks_reads_real_nhc_bulletins():
    tracks = fetch_live_tracks()
    # No active storms right now is a legitimate real outcome (this isn't
    # a "must always find one" test) -- but whatever comes back must be
    # real, well-formed WORKING tracks.
    for track in tracks:
        assert track.quality.value == "working"
        assert len(track.fixes) >= 1
