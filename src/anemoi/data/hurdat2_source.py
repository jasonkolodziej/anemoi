"""Which HURDAT2 files to train on: the newest NHC has published (#216).

Both images baked in one pinned file, ``hurdat2-atl-1851-2023-042624.txt``,
and every training run -- scheduled, preseason or data-volume -- parsed
it. NHC publishes each season's final best track the following spring, so
2024's (and later) was never seen: the data-volume trigger counted fixes in
a file that never changed (always 0), the monthly and preseason retrains
retrained on identical data, and Stage B's test seasons were empty.

NHC keeps two archives (`ARCHIVES`): the Atlantic, and the Northeast and
North Central Pacific (Eastern and Central Pacific storms together).
`fetch_latest_hurdat2` reads NHC's HURDAT2 directory listing and, for each
archive that holds a basin asked for, picks the file with the latest final
season (and, for that season, the latest release date). It writes them to
one file, one after the other -- storm ids never collide across basins, so
`data.hurdat2.parse_hurdat2` reads the result as it reads either -- with a
manifest beside it: file names, URLs, sha256, last season, basins. Training
records that on every registered model. If the listing can't be read it
falls back to the pinned files, and says so in the manifest rather than
pretending.

Run at image build (both images) and at the start of every training job
(``docker/cloud-run-training/entrypoint.sh``), via ``anemoi hurdat2-fetch``.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .basins import TRAINING_BASINS

INDEX_URL = "https://www.nhc.noaa.gov/data/hurdat/"


@dataclass(frozen=True, slots=True)
class Archive:
    """One of NHC's HURDAT2 archives: the basins its storms come from, how
    its files are named, and the file to fall back to."""

    key: str
    basins: tuple[str, ...]
    #: Matches a file name; the groups are the last season and the release
    #: date as MM, DD, YY.
    name_re: re.Pattern[str]
    pinned_name: str


#: ``hurdat2-1851-2024-040425.txt`` and the older
#: ``hurdat2-atl-1851-2023-042624.txt`` naming; never ``hurdat2-nepac-…``.
ATLANTIC = Archive(
    key="atl",
    basins=("AL",),
    name_re=re.compile(r"hurdat2-(?:atl-)?1851-(\d{4})-(\d{2})(\d{2})(\d{2})\.txt"),
    pinned_name="hurdat2-atl-1851-2023-042624.txt",
)
#: ``hurdat2-nepac-1949-2024-031725.txt``: Eastern and Central Pacific
#: storms (``EP…``/``CP…`` ids) in one file.
NORTHEAST_PACIFIC = Archive(
    key="nepac",
    basins=("EP", "CP"),
    name_re=re.compile(r"hurdat2-nepac-1949-(\d{4})-(\d{2})(\d{2})(\d{2})\.txt"),
    pinned_name="hurdat2-nepac-1949-2024-031725.txt",
)
#: In the order their files are written to the combined archive.
ARCHIVES: tuple[Archive, ...] = (ATLANTIC, NORTHEAST_PACIFIC)

PINNED_NAME = ATLANTIC.pinned_name

_TIMEOUT_S = 60.0


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "anemoi/1.0"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310
        return resp.read()


def archives_for(basins: Iterable[str]) -> tuple[Archive, ...]:
    """The archives holding any of ``basins``, in `ARCHIVES` order. Raises
    for a basin NHC's HURDAT2 doesn't cover (the Western Pacific, North
    Indian Ocean and Southern Hemisphere are JTWC's)."""
    wanted = tuple(basins)
    covered = {b for archive in ARCHIVES for b in archive.basins}
    missing = [b for b in wanted if b not in covered]
    if missing:
        raise ValueError(
            f"no HURDAT2 archive holds {missing}; NHC's cover {sorted(covered)}"
        )
    return tuple(a for a in ARCHIVES if set(a.basins) & set(wanted))


def latest_name(index_html: str, archive: Archive = ATLANTIC) -> str | None:
    """``archive``'s file with the latest final season in a listing, the
    latest release of it when there are several; None if there's none."""
    best: tuple[tuple[int, int, int, int], str] | None = None
    for match in archive.name_re.finditer(index_html):
        season, mm, dd, yy = (int(g) for g in match.groups())
        key = (season, 2000 + yy, mm, dd)
        if best is None or key > best[0]:
            best = (key, match.group(0))
    return best[1] if best else None


def last_season(name: str) -> int:
    for archive in ARCHIVES:
        match = archive.name_re.fullmatch(name)
        if match:
            return int(match.group(1))
    raise ValueError(f"not a HURDAT2 file name: {name!r}")


def manifest_path(dest: Path | str) -> Path:
    return Path(dest).with_suffix(".json")


def fetch_latest_hurdat2(
    dest: Path | str,
    *,
    basins: Iterable[str] = TRAINING_BASINS,
    fetch: Callable[[str], bytes] = _get,
) -> dict[str, object]:
    """Download the newest HURDAT2 for ``basins`` to ``dest`` and write its
    manifest (`manifest_path`): one file per archive that holds any of
    them (`archives_for`), written one after the other.

    An archive falls back to its pinned file when the listing can't be read
    or names none (``"fallback": true``). All or nothing: if any archive
    can't be downloaded at all this raises and ``dest`` is left as it was,
    so the file on disk never holds fewer basins than it says.
    """
    dest = Path(dest)
    archives = archives_for(basins)
    try:
        listing: str | None = fetch(INDEX_URL).decode("utf-8", errors="replace")
        listing_error = None
    except Exception as exc:  # noqa: BLE001 - the pinned files are still real archives
        listing, listing_error = None, f"listing unreadable: {type(exc).__name__}: {exc}"

    bodies: list[bytes] = []
    sources: list[dict[str, Any]] = []
    for archive in archives:
        name = latest_name(listing, archive) if listing is not None else None
        fallback_reason = listing_error
        if name is None and fallback_reason is None:
            fallback_reason = f"no {archive.key} HURDAT2 file in the listing"
        name = name or archive.pinned_name
        url = INDEX_URL + name
        body = fetch(url)
        bodies.append(body)
        source: dict[str, Any] = {
            "basins": list(archive.basins),
            "file": name,
            "url": url,
            "sha256": hashlib.sha256(body).hexdigest(),
            "last_season": last_season(name),
            "fallback": fallback_reason is not None,
        }
        if fallback_reason:
            source["fallback_reason"] = fallback_reason
        sources.append(source)

    # One archive is written byte for byte, as it always was; several are
    # joined on line ends, so no storm's last row runs into the next header.
    if len(bodies) == 1:
        combined = bodies[0]
    else:
        combined = b"".join(b if b.endswith(b"\n") else b + b"\n" for b in bodies)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(combined)
    reasons = [str(s["fallback_reason"]) for s in sources if s["fallback"]]
    manifest: dict[str, object] = {
        "file": "+".join(str(s["file"]) for s in sources),
        "sha256": hashlib.sha256(combined).hexdigest(),
        # The newest season any archive has. An archive released later than
        # the others lags it; each source's own `last_season` says by how much.
        "last_season": max(s["last_season"] for s in sources),
        "basins": [b for s in sources for b in s["basins"]],
        "fallback": bool(reasons),
        "sources": sources,
    }
    if len(sources) == 1:
        manifest["url"] = sources[0]["url"]
    if reasons:
        manifest["fallback_reason"] = "; ".join(dict.fromkeys(reasons))
    manifest_path(dest).write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def describe(path: Path | str) -> dict[str, str]:
    """What a HURDAT2 file on disk is, as registry tags: its manifest's file
    name and last season when there is one, and always its own sha256 (the
    bytes are what was trained on, whatever the manifest says)."""
    path = Path(path)
    tags = {"hurdat2_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    try:
        manifest = json.loads(manifest_path(path).read_text())
        tags["hurdat2_file"] = str(manifest["file"])
        tags["hurdat2_last_season"] = str(manifest["last_season"])
    except (OSError, ValueError, KeyError):
        pass
    return tags
