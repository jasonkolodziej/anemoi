"""Durable archive of NHC's as-issued storm data (#213).

Training uses synthetic working tracks: final best-track positions plus
noise (`data.besttrack.emulate_working_track`) whose sizes are placeholders.
The only way to calibrate that noise -- or to train on what the model really
sees live -- is pairs of (as-issued working fix, final best-track fix) for
the same storm and time (`data.atcf.pair_by_valid_time`,
`data.besttrack.recalibrate_from_pairs`). The final half is published every
spring in HURDAT2. The working half is not kept by anyone in a form we can
rely on:

* ``atcf/com/{id}-tcvitals-arch.dat`` holds the season's TC-Vitals while a
  storm is current; nothing documents how long it stays.
* ``atcf/btk/b{id}.dat`` -- the working b-deck -- is overwritten with the
  final best track after the season.
* ``atcf/aid_public/a{id}.dat.gz`` -- the a-deck, whose CARQ lines carry the
  as-issued initial conditions -- is the closest thing to a record, and is
  not guaranteed either.
* ``CurrentStorms.json`` is a moment's index, gone the next minute.

The live path held these in memory for 30 minutes and persisted only the
last 20 fixes of cycles a real model contributed to. So every season
without this archive is a season whose working fixes can't be recovered.

`archive_atcf` copies each file verbatim into durable storage, every time
it runs (the cycle Workflow calls it after each synoptic cycle's runs, via
``POST /v1/internal/archive-atcf``; ``anemoi atcf-archive`` runs it by
hand). Each file is keyed by when it was fetched and a digest of its bytes,
and is only written when that content isn't stored yet -- so every revision
NHC ever served is kept once, and nothing is ever overwritten::

    archive/atcf/{year}/_currentstorms/{fetched}_{sha12}.json
    archive/atcf/{year}/{storm_id}/{product}/{fetched}_{sha12}{ext}

with ``product`` one of ``tcvitals``, ``bdeck``, ``adeck``. Every basin NHC
lists is archived, not only the trained ones: an EP storm's pairs are as
good a noise estimate as an AL one's, and deciding later costs nothing.

A storm stays on the list for `RECENT_WINDOW` after it leaves
``CurrentStorms.json`` (``archive/atcf/_recent.json`` remembers when each
was last seen -- one file, not one per year, so a storm last seen on 31
December is still followed on 1 January), so its final bulletins and the
post-storm b-deck are caught too.

Reading back: `archived_tcvitals` returns every archived TC-Vitals bulletin
for a season, each revision once, in the order NHC issued them.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError

from .atcf import TcVitalsError, parse_tcvitals
from .besttrack import Fix
from .live_atcf import CURRENT_STORMS_URL, TCVITALS_ARCH_URL

if TYPE_CHECKING:
    from ..tracking.checkpoint_store import CheckpointStore

ARCHIVE_PREFIX = "archive/atcf/"
BDECK_URL = "https://ftp.nhc.noaa.gov/atcf/btk/b{storm}.dat"
ADECK_URL = "https://ftp.nhc.noaa.gov/atcf/aid_public/a{storm}.dat.gz"

#: product -> (URL template taking the storm id, file extension).
PRODUCTS: dict[str, tuple[Callable[[str], str], str]] = {
    "tcvitals": (lambda sid: TCVITALS_ARCH_URL.format(storm_id=sid.lower()), ".dat"),
    "bdeck": (lambda sid: BDECK_URL.format(storm=sid.lower()), ".dat"),
    "adeck": (lambda sid: ADECK_URL.format(storm=sid.lower()), ".dat.gz"),
}

#: How long a storm keeps being archived after it leaves CurrentStorms.json.
RECENT_WINDOW = timedelta(days=3)

_TIMEOUT_S = 20.0


class NotPublished(RuntimeError):
    """The file doesn't exist upstream (yet) -- e.g. no a-deck for a storm
    in its first hours. Not an error worth retrying."""


def _get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "anemoi-api/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310
            return resp.read()
    except HTTPError as exc:
        if exc.code == 404:
            raise NotPublished(url) from exc
        raise
    except URLError:
        raise


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()[:12]


def snapshot_key(year: int, storm_id: str, product: str, fetched_at: datetime, body: bytes) -> str:
    ext = PRODUCTS[product][1]
    return f"{ARCHIVE_PREFIX}{year}/{storm_id}/{product}/{fetched_at:%Y%m%dT%H%M%SZ}_{_digest(body)}{ext}"


def currentstorms_key(year: int, fetched_at: datetime, body: bytes) -> str:
    return f"{ARCHIVE_PREFIX}{year}/_currentstorms/{fetched_at:%Y%m%dT%H%M%SZ}_{_digest(body)}.json"


#: When each storm was last in CurrentStorms.json. Not per year: a per-year
#: file started empty on 1 January and dropped a storm seen on 31 December.
RECENT_KEY = f"{ARCHIVE_PREFIX}_recent.json"


def _stored_digests(store: CheckpointStore, prefix: str) -> set[str]:
    """Digests already archived under ``prefix`` (from the key names alone)."""
    digests = set()
    for key in store.list(prefix):
        name = key.rsplit("/", 1)[-1]
        stem = name.split(".", 1)[0]
        if "_" in stem:
            digests.add(stem.rsplit("_", 1)[-1])
    return digests


def _put_bytes(store: CheckpointStore, key: str, body: bytes) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "object"
        path.write_bytes(body)
        store.upload(path, key)


def _get_text(store: CheckpointStore, key: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "object"
        store.download(f"s3://{store.config.bucket}/{key}", path)
        return path.read_text(encoding="utf-8", errors="replace")


@dataclass
class ArchiveReport:
    """What one `archive_atcf` pass did, for logs and the Workflow output."""

    storms: list[str] = field(default_factory=list)
    written: list[str] = field(default_factory=list)
    unchanged: int = 0
    not_published: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "storms": self.storms,
            "written": len(self.written),
            "unchanged": self.unchanged,
            "not_published": self.not_published,
            "failed": self.failed,
        }


def archive_atcf(
    store: CheckpointStore,
    *,
    now: datetime | None = None,
    fetch: Callable[[str], bytes] = _get_bytes,
) -> ArchiveReport:
    """Archive CurrentStorms.json and every current or recently current
    storm's TC-Vitals, b-deck and a-deck. Best-effort per file: one failed
    fetch or upload is recorded and the rest carry on. Raises only when the
    storm index itself can't be fetched, since then nothing else can be
    known (the caller reports it; the next pass tries again)."""
    now = now or datetime.now(UTC)
    year = now.year
    report = ArchiveReport()

    index = fetch(CURRENT_STORMS_URL)
    _write_if_new(store, currentstorms_key(year, now, index), index,
                  f"{ARCHIVE_PREFIX}{year}/_currentstorms/", report)
    try:
        current = [
            s["id"].upper() for s in json.loads(index).get("activeStorms", []) if "id" in s
        ]
    except (ValueError, AttributeError) as exc:
        report.failed["_currentstorms"] = f"unparseable: {exc}"
        current = []

    recent = _load_recent(store)
    for storm_id in current:
        recent[storm_id] = now.isoformat()
    # Only storms inside the window are kept, so the file stays small.
    recent = {
        sid: seen for sid, seen in recent.items()
        if now - datetime.fromisoformat(seen) <= RECENT_WINDOW
    }
    storms = sorted(recent)
    report.storms = storms

    for storm_id in storms:
        # A storm's files carry its own season, which differs from `now`'s
        # year only for a storm still listed across New Year.
        season = int(storm_id[-4:]) if storm_id[-4:].isdigit() else year
        for product, (url_for, _ext) in PRODUCTS.items():
            label = f"{storm_id}/{product}"
            try:
                body = fetch(url_for(storm_id))
            except NotPublished:
                report.not_published.append(label)
                continue
            except Exception as exc:  # noqa: BLE001 - one file must not sink the pass
                report.failed[label] = f"fetch: {exc}"
                continue
            prefix = f"{ARCHIVE_PREFIX}{season}/{storm_id}/{product}/"
            _write_if_new(store, snapshot_key(season, storm_id, product, now, body), body, prefix, report)

    try:
        _put_bytes(store, RECENT_KEY, json.dumps(recent, sort_keys=True).encode())
    except Exception as exc:  # noqa: BLE001
        report.failed["_recent"] = f"upload: {exc}"
    return report


def _write_if_new(
    store: CheckpointStore, key: str, body: bytes, prefix: str, report: ArchiveReport,
) -> None:
    try:
        if _digest(body) in _stored_digests(store, prefix):
            report.unchanged += 1
            return
        _put_bytes(store, key, body)
        report.written.append(key)
    except Exception as exc:  # noqa: BLE001 - recorded, the pass carries on
        report.failed[key] = f"upload: {exc}"


def _load_recent(store: CheckpointStore) -> dict[str, str]:
    key = RECENT_KEY
    try:
        if not store.exists(key):
            return {}
        data = json.loads(_get_text(store, key))
    except Exception:  # noqa: BLE001 - a lost index only shortens the window once
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def archived_tcvitals(store: CheckpointStore, season: int) -> dict[str, list[Fix]]:
    """Every archived TC-Vitals bulletin of ``season``, by storm.

    Each snapshot is the file as NHC served it at the time, so later
    snapshots repeat earlier lines; a bulletin is kept once (its first
    appearance), in the order the snapshots were taken. Revisions -- a
    corrected bulletin for a valid time already issued -- are distinct
    lines and all kept, so a caller can choose the as-issued one (first)
    or the latest."""
    by_storm: dict[str, list[Fix]] = {}
    prefix = f"{ARCHIVE_PREFIX}{season}/"
    keys = sorted(k for k in store.list(prefix) if "/tcvitals/" in k)
    seen: dict[str, set[str]] = {}
    for key in keys:
        storm_id = key[len(prefix):].split("/", 1)[0]
        lines = seen.setdefault(storm_id, set())
        for line in _get_text(store, key).splitlines():
            if not line.strip() or line in lines:
                continue
            lines.add(line)
            try:
                fixes = [f for f in parse_tcvitals(line) if f.storm_id == storm_id]
            except TcVitalsError:
                continue  # kept verbatim in the archive; just not a usable fix

            by_storm.setdefault(storm_id, []).extend(fixes)
    return by_storm
