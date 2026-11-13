"""Where the operational guidance is read from: NHC's a-deck archive.

One gzipped a-deck per storm, ``a{basin}{number}{year}.dat.gz``, holding
every technique's forecasts for it (`data.atcf.parse_adeck`). A finished
season's files are in NHC's archive (`ARCHIVE_URL`); the season in progress
is in ``aid_public`` (`data.atcf_archive.ADECK_URL`) until NHC moves it, so
a storm the archive does not have yet is looked for there.

This is a verification-only read. Nothing here is a model input, and it is
not in `data.sources`' registry of streams a cycle may read: a technique's
row for cycle ``t`` is written hours after ``t``.

`fetch_adecks` fills a local directory, skipping what is already there, and
with it NHC's own per-forecast errors (`data.nhc_verification`) that the
join is checked against. `read_adeck` reads one cached file. Downloading
and scoring are separate commands (``anemoi adeck-fetch``, then ``anemoi
baseline-backtest --adeck-dir``), as for HURDAT2 and the gridded caches, so
a backtest never touches the network.
"""

from __future__ import annotations

import gzip
import hashlib
import urllib.request
import zlib
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError

from .atcf import STORM_ID_RE, Adeck, AtcfError, parse_adeck, storm_basin
from .atcf_archive import ADECK_URL as CURRENT_SEASON_URL
from .atcf_archive import NotPublished
from .nhc_verification import (
    OFFICIAL_ERRORS_FILES,
    OFFICIAL_ERRORS_URL,
    OfficialErrors,
    OfficialErrorsError,
    parse_official_errors,
)

#: A finished season's a-decks. The one place the archive's layout is written.
ARCHIVE_URL = "https://ftp.nhc.noaa.gov/atcf/archive/{year}/a{storm}.dat.gz"

#: NHC's servers are a shared public resource: never more than this many
#: requests at a time, whatever the caller asks for.
MAX_WORKERS = 4

#: Size limits on what is read from the network and from a cached file. The
#: largest 2024 a-deck is 4 MB gzipped and 31 MB of text.
MAX_DOWNLOAD_BYTES = 64 * 2**20
MAX_ADECK_TEXT_BYTES = 512 * 2**20

_TIMEOUT_S = 120.0

#: The first bytes of every gzip stream: what an a-deck must start with.
_GZIP_MAGIC = b"\x1f\x8b"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "anemoi/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310
            body = resp.read(MAX_DOWNLOAD_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 404:
            raise NotPublished(url) from exc
        raise
    if len(body) > MAX_DOWNLOAD_BYTES:
        raise ValueError(f"{url}: more than {MAX_DOWNLOAD_BYTES} bytes")
    return body


def adeck_name(storm_id: str) -> str:
    """``AL092024`` -> ``aal092024.dat.gz``. Raises for anything that is not
    an ATCF storm id, so an id never becomes an unexpected path or URL."""
    if not STORM_ID_RE.fullmatch(storm_id):
        raise AtcfError(f"not an ATCF storm id: {storm_id!r}")
    return f"a{storm_id.lower()}.dat.gz"


def adeck_urls(storm_id: str) -> tuple[str, str]:
    """Where a storm's a-deck may be: the season archive, then ``aid_public``."""
    adeck_name(storm_id)
    storm = storm_id.lower()
    return (
        ARCHIVE_URL.format(year=storm_id[-4:], storm=storm),
        CURRENT_SEASON_URL.format(storm=storm),
    )


def adeck_path(cache_dir: Path | str, storm_id: str) -> Path:
    return Path(cache_dir) / adeck_name(storm_id)


def file_record(path: Path | str) -> dict[str, object]:
    """A cached file's name, size and sha256, for a report's provenance."""
    body = Path(path).read_bytes()
    return {
        "file": Path(path).name,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


@dataclass(slots=True)
class AdeckFetchReport:
    """What one `fetch_adecks` call did, by file name."""

    fetched: dict[str, str] = field(default_factory=dict)  # name -> url
    cached: list[str] = field(default_factory=list)
    not_published: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "fetched": dict(sorted(self.fetched.items())),
            "cached": sorted(self.cached),
            "not_published": sorted(self.not_published),
            "failed": dict(sorted(self.failed.items())),
        }


def _check_adeck(body: bytes) -> None:
    if not body.startswith(_GZIP_MAGIC):
        raise ValueError("not gzip data, so not an a-deck")


def _check_official_errors(body: bytes) -> None:
    parse_official_errors(body.decode("ascii", errors="replace"))


def _fetch_one(
    path: Path, urls: tuple[str, ...], fetch: Callable[[str], bytes],
    check: Callable[[bytes], None],
) -> tuple[str, str]:
    """Download the first of ``urls`` that exists to ``path``. Returns
    ``(outcome, detail)``: ``cached``, ``fetched`` (detail: the URL),
    ``not_published`` or ``failed`` (detail: why).

    A body ``check`` rejects is not written. Any non-empty file is kept as
    cached on the next run, so an error page a server sent with status 200
    would otherwise stay in the cache for good."""
    if path.exists() and path.stat().st_size > 0:
        return "cached", ""
    for url in urls:
        try:
            body = fetch(url)
        except NotPublished:
            continue
        except Exception as exc:  # noqa: BLE001 - one file must not sink the rest
            return "failed", f"{type(exc).__name__}: {exc}"
        try:
            check(body)
        except ValueError as exc:
            return "failed", f"{url}: {exc}"
        partial = path.with_name(path.name + ".part")
        partial.write_bytes(body)
        partial.replace(path)
        return "fetched", url
    return "not_published", ""


def fetch_adecks(
    storm_ids: Iterable[str],
    cache_dir: Path | str,
    *,
    fetch: Callable[[str], bytes] | None = None,
    max_workers: int = MAX_WORKERS,
    official_errors: bool = True,
) -> AdeckFetchReport:
    """Download each storm's a-deck into ``cache_dir``, and (unless
    ``official_errors`` is off) NHC's per-forecast official errors for the
    storms' basins that have one.

    Files already there are kept, so a re-run fetches only what is missing.
    A file that does not exist upstream is recorded as not published and
    one that fails, or whose body is not that kind of file (an a-deck is
    gzip; an error file has NHC's column header), as failed and is not
    written; neither stops the others. At most
    `MAX_WORKERS` requests run at a time. ``fetch`` (a URL to its bytes,
    raising `NotPublished` for a 404) defaults to a plain HTTPS GET.
    """
    fetch = fetch or _get
    if max_workers < 1:
        raise ValueError(f"max_workers must be at least 1, got {max_workers}")
    cache = Path(cache_dir)
    storms = list(dict.fromkeys(storm_ids))
    jobs: dict[Path, tuple[tuple[str, ...], Callable[[bytes], None]]] = {
        adeck_path(cache, storm_id): (adeck_urls(storm_id), _check_adeck) for storm_id in storms
    }
    if official_errors:
        for basin in sorted({storm_basin(s) for s in storms}):
            name = OFFICIAL_ERRORS_FILES.get(basin)
            if name is not None:
                jobs[cache / name] = (
                    (OFFICIAL_ERRORS_URL.format(name=name),), _check_official_errors,
                )
    cache.mkdir(parents=True, exist_ok=True)

    report = AdeckFetchReport()
    with ThreadPoolExecutor(max_workers=min(max_workers, MAX_WORKERS)) as pool:
        outcomes = pool.map(
            lambda job: _fetch_one(job[0], job[1][0], fetch, job[1][1]), jobs.items(),
        )
        for path, (outcome, detail) in zip(jobs, outcomes, strict=True):
            if outcome == "fetched":
                report.fetched[path.name] = detail
            elif outcome == "failed":
                report.failed[path.name] = detail
            else:
                getattr(report, outcome).append(path.name)
    return report


def read_adeck(
    path: Path | str, storm_id: str, techniques: Iterable[str] | None = None,
) -> Adeck:
    """Read one cached a-deck (gzipped, as NHC serves it). The text is
    capped at `MAX_ADECK_TEXT_BYTES`, so a file that is not what it claims
    cannot exhaust memory; bytes that are not ASCII are replaced."""
    with gzip.open(Path(path), "rb") as fh:
        body = fh.read(MAX_ADECK_TEXT_BYTES + 1)
    if len(body) > MAX_ADECK_TEXT_BYTES:
        raise AtcfError(f"{path}: more than {MAX_ADECK_TEXT_BYTES} bytes of text")
    return parse_adeck(body.decode("ascii", errors="replace"), storm_id, techniques)


@dataclass(slots=True)
class CachedAdecks:
    """The a-decks a directory holds for a list of storms."""

    adecks: dict[str, Adeck] = field(default_factory=dict)
    #: One provenance record per file read (`file_record`, plus what the
    #: parser left out), in the storms' order.
    records: list[dict[str, object]] = field(default_factory=list)
    #: Storms with no file in the directory.
    missing: list[str] = field(default_factory=list)
    #: storm -> why its file could not be read.
    unreadable: dict[str, str] = field(default_factory=dict)


def read_cached_adecks(
    cache_dir: Path | str, storm_ids: Iterable[str], techniques: Iterable[str] | None = None,
) -> CachedAdecks:
    """Read every storm's a-deck that ``cache_dir`` holds. A missing or
    unreadable file is recorded, not raised: the storm then has no
    guidance, which a comparison reports rather than hides."""
    wanted = None if techniques is None else frozenset(techniques)
    out = CachedAdecks()
    for storm_id in dict.fromkeys(storm_ids):
        path = adeck_path(cache_dir, storm_id)
        if not path.exists():
            out.missing.append(storm_id)
            continue
        try:
            adeck = read_adeck(path, storm_id, wanted)
        except (OSError, EOFError, ValueError, zlib.error) as exc:  # bad gzip: OSError
            out.unreadable[storm_id] = f"{type(exc).__name__}: {exc}"
            continue
        out.adecks[storm_id] = adeck
        out.records.append({
            "storm_id": storm_id,
            **file_record(path),
            "n_rows": adeck.n_rows,
            "n_skipped": adeck.n_skipped,
            "n_other_storm": adeck.n_other_storm,
            "n_basin_mismatch": adeck.n_basin_mismatch,
            "conflicts": dict(sorted(adeck.conflicts.items())),
        })
    return out


def read_cached_official_errors(
    cache_dir: Path | str,
) -> tuple[dict[str, OfficialErrors], list[dict[str, object]]]:
    """NHC's per-forecast official errors that ``cache_dir`` holds, by
    basin, with a provenance record per file. Empty when it holds none.
    Raises `OfficialErrorsError` naming a file that is not one of NHC's,
    since `fetch_adecks` keeps any non-empty file and would not replace it."""
    errors: dict[str, OfficialErrors] = {}
    records: list[dict[str, object]] = []
    for basin, name in OFFICIAL_ERRORS_FILES.items():
        path = Path(cache_dir) / name
        if not path.exists():
            continue
        try:
            errors[basin] = parse_official_errors(
                path.read_text(encoding="ascii", errors="replace")
            )
        except OfficialErrorsError as exc:
            raise OfficialErrorsError(
                f"{path}: {exc}; delete it and run `anemoi adeck-fetch` again"
            ) from exc
        records.append({
            "basin": basin, **file_record(path), "url": OFFICIAL_ERRORS_URL.format(name=name),
        })
    return errors, records
