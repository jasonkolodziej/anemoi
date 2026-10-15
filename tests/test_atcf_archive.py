"""NHC's as-issued storm files, archived before they're gone (#213)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from anemoi.data import atcf_archive, live_atcf
from anemoi.data.atcf_archive import (
    NotPublished,
    archive_atcf,
    archived_tcvitals,
)
from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config

NOW = datetime(2026, 9, 21, 7, 40, tzinfo=UTC)
INDEX = json.dumps({"activeStorms": [{"id": "al092026", "name": "Isaias"}, {"id": "ep142026"}]})
VITALS_1 = "NHC 09L ISAIAS    20260921 0000 200N 0690W 270 046 1000 1012 0300 18 050\n"
VITALS_2 = VITALS_1 + "NHC 09L ISAIAS    20260921 0600 205N 0700W 270 046 0998 1012 0300 21 050\n"
# NHC's correction of the 06Z position, issued after the first 06Z bulletin.
VITALS_3 = VITALS_2 + "NHC 09L ISAIAS    20260921 0600 207N 0703W 270 046 0998 1012 0300 21 050\n"


class _MemoryS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key, local_path):
        self.objects[key] = Path(local_path).read_bytes()

    def get(self, key, local_path):
        Path(local_path).write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return [k for k in self.objects if k.startswith(prefix)]


@pytest.fixture
def s3():
    return _MemoryS3()


@pytest.fixture
def store(s3):
    config = S3Config(endpoint_url="https://example.r2.cloudflarestorage.com", bucket="t",
                      access_key_id="k", secret_access_key="s")
    return CheckpointStore(config, client=s3)


def _fetcher(files: dict[str, bytes | str]):
    def fetch(url: str) -> bytes:
        for suffix, body in files.items():
            if url.endswith(suffix):
                return body.encode() if isinstance(body, str) else body
        raise NotPublished(url)
    return fetch


def _keys(s3, part):
    return sorted(k for k in s3.objects if part in k)


def test_every_file_is_archived_verbatim_for_every_basin(store, s3):
    report = archive_atcf(store, now=NOW, fetch=_fetcher({
        "CurrentStorms.json": INDEX,
        "al092026-tcvitals-arch.dat": VITALS_1,
        "bal092026.dat": "AL, 09, 2026092100, , BEST, 0, 200N, 690W, 35\n",
        "aal092026.dat.gz": b"\x1f\x8b binary a-deck",
        "ep142026-tcvitals-arch.dat": "x",
    }))
    assert report.storms == ["AL092026", "EP142026"]
    assert len(_keys(s3, "/_currentstorms/")) == 1
    (vitals_key,) = _keys(s3, "AL092026/tcvitals/")
    assert vitals_key.startswith("archive/atcf/2026/AL092026/tcvitals/20260921T074000Z_")
    assert s3.objects[vitals_key] == VITALS_1.encode()
    assert s3.objects[_keys(s3, "AL092026/adeck/")[0]] == b"\x1f\x8b binary a-deck"
    assert _keys(s3, "EP142026/tcvitals/")  # not only the trained basin
    # Files NHC hasn't published yet are reported, not failures.
    assert "EP142026/bdeck" in report.not_published
    assert report.failed == {}


def test_only_new_content_is_written_and_nothing_is_overwritten(store, s3):
    files = {"CurrentStorms.json": INDEX, "al092026-tcvitals-arch.dat": VITALS_1}
    archive_atcf(store, now=NOW, fetch=_fetcher(files))
    before = dict(s3.objects)

    again = archive_atcf(store, now=NOW + timedelta(hours=6), fetch=_fetcher(files))
    assert again.written == []  # identical content: nothing new
    assert again.unchanged == 2

    files["al092026-tcvitals-arch.dat"] = VITALS_2
    later = archive_atcf(store, now=NOW + timedelta(hours=12), fetch=_fetcher(files))
    assert [k for k in later.written if "/tcvitals/" in k]
    assert len(_keys(s3, "AL092026/tcvitals/")) == 2
    for key, body in before.items():
        if not key.endswith("_recent.json"):
            assert s3.objects[key] == body


def test_a_storm_is_still_archived_for_a_few_days_after_it_leaves_the_index(store, s3):
    archive_atcf(store, now=NOW, fetch=_fetcher({
        "CurrentStorms.json": INDEX, "al092026-tcvitals-arch.dat": VITALS_1,
    }))
    gone = json.dumps({"activeStorms": []})
    two_days = archive_atcf(store, now=NOW + timedelta(days=2), fetch=_fetcher({
        "CurrentStorms.json": gone, "al092026-tcvitals-arch.dat": VITALS_2,
    }))
    assert "AL092026" in two_days.storms
    assert len(_keys(s3, "AL092026/tcvitals/")) == 2  # its final bulletins caught

    week = archive_atcf(store, now=NOW + timedelta(days=7), fetch=_fetcher({
        "CurrentStorms.json": gone,
    }))
    assert week.storms == []


def test_a_storm_seen_on_new_years_eve_is_still_followed_on_new_years_day(store, s3):
    """The recently-seen record was per year, so 1 January started empty
    and dropped a storm last listed on 31 December (Copilot review, #213)."""
    eve = datetime(2026, 12, 31, 19, 30, tzinfo=UTC)
    archive_atcf(store, now=eve, fetch=_fetcher({
        "CurrentStorms.json": INDEX, "al092026-tcvitals-arch.dat": VITALS_1,
    }))
    new_year = archive_atcf(store, now=eve + timedelta(hours=6), fetch=_fetcher({
        "CurrentStorms.json": json.dumps({"activeStorms": []}),
        "al092026-tcvitals-arch.dat": VITALS_2,
    }))
    assert "AL092026" in new_year.storms
    # Filed under the storm's own season, not the calendar year it ran in.
    assert len(_keys(s3, "archive/atcf/2026/AL092026/tcvitals/")) == 2


def test_the_cli_archives_lists_and_needs_credentials(store, monkeypatch, capsys):
    from anemoi import cli
    from anemoi.tracking import checkpoint_store

    archive_atcf(store, now=NOW, fetch=_fetcher({
        "CurrentStorms.json": INDEX, "al092026-tcvitals-arch.dat": VITALS_2,
    }))
    monkeypatch.setattr(checkpoint_store.S3Config, "from_env", classmethod(lambda cls: store.config))
    monkeypatch.setattr(checkpoint_store, "CheckpointStore", lambda config: store)

    assert cli.main(["atcf-archive", "--list", "2026"]) == 0
    out = capsys.readouterr().out
    assert "AL092026: 2 bulletin(s), 2 valid time(s), 2026-09-21 00Z .. 2026-09-21 06Z" in out

    monkeypatch.setattr(
        atcf_archive, "archive_atcf",
        lambda st: atcf_archive.ArchiveReport(storms=["AL092026"], written=["k"]),
    )
    assert cli.main(["atcf-archive"]) == 0
    assert '"written": 1' in capsys.readouterr().out

    def no_credentials(cls):
        raise checkpoint_store.CheckpointStoreError("S3_ARTIFACT_BUCKET is not set")

    monkeypatch.setattr(checkpoint_store.S3Config, "from_env", classmethod(no_credentials))
    assert cli.main(["atcf-archive"]) == 1
    assert "needs real S3_ARTIFACT_* durable storage credentials" in capsys.readouterr().out


def test_one_failed_file_does_not_stop_the_others(store, s3):
    def fetch(url):
        if "tcvitals" in url and "al09" in url:
            raise TimeoutError("NHC slow")
        return _fetcher({"CurrentStorms.json": INDEX, "ep142026-tcvitals-arch.dat": "x"})(url)

    report = archive_atcf(store, now=NOW, fetch=fetch)
    assert "AL092026/tcvitals" in report.failed
    assert _keys(s3, "EP142026/tcvitals/")


def test_an_unreachable_index_raises_so_the_caller_reports_it(store):
    def fetch(url):
        raise TimeoutError("down")

    with pytest.raises(TimeoutError):
        archive_atcf(store, now=NOW, fetch=fetch)


def test_archived_tcvitals_keeps_every_revision_once_in_issue_order(store):
    for i, body in enumerate((VITALS_1, VITALS_2, VITALS_3)):
        archive_atcf(store, now=NOW + timedelta(hours=6 * i), fetch=_fetcher({
            "CurrentStorms.json": INDEX, "al092026-tcvitals-arch.dat": body,
        }))
    fixes = archived_tcvitals(store, 2026)["AL092026"]
    assert [f.valid_time.hour for f in fixes] == [0, 6, 6]
    as_issued, corrected = fixes[1], fixes[2]
    assert (as_issued.lat, corrected.lat) == (20.5, 20.7)


def test_the_live_track_uses_nhcs_latest_revision(monkeypatch):
    """It kept the first bulletin per valid time, so a corrected position
    never reached the track (#213)."""
    monkeypatch.setattr(live_atcf, "_get", lambda url: VITALS_3)
    track = live_atcf.fetch_live_track("AL092026")
    assert [f.valid_time.hour for f in track.fixes] == [0, 6]
    assert track.fixes[-1].lat == 20.7


def test_the_internal_route_and_workflow_step_exist():
    root = Path(__file__).parents[1]
    workflow = (root / "docker" / "api" / "src" / "cycleWorkflow.ts").read_text()
    assert "/v1/internal/archive-atcf" in workflow
    assert "'archive atcf'" in workflow
    from anemoi.api.routers import internal

    assert any(r.path == "/internal/archive-atcf" for r in internal.router.routes)


def test_real_state_reports_rather_than_raises(monkeypatch, tmp_path, store, s3):
    from anemoi.api.real_state import RealState

    hurdat2 = tmp_path / "h.txt"
    radii = ", ".join(["-999"] * 12)
    hurdat2.write_text(f"AL012026, T, 1,\n20260901, 0000,  , TS, 20.0N,  60.0W,  40, 1005, {radii},\n")
    state = RealState(hurdat2_path=str(hurdat2), registry_root=str(tmp_path / "r"),
                      checkpoint_store=store, cache_dir=str(tmp_path / "g"))
    real = atcf_archive.archive_atcf
    monkeypatch.setattr(
        atcf_archive, "archive_atcf",
        lambda st: real(st, now=NOW, fetch=_fetcher({"CurrentStorms.json": INDEX})),
    )
    assert state.archive_atcf()["storms"] == ["AL092026", "EP142026"]

    def down(st):
        raise TimeoutError("NHC down")

    monkeypatch.setattr(atcf_archive, "archive_atcf", down)
    assert "NHC down" in state.archive_atcf()["error"]
