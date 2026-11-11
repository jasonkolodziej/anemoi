"""Which HURDAT2 file to train on: the newest NHC has published (#216).

Both images baked in one pinned file, ``hurdat2-atl-1851-2023-042624.txt``,
and every training run -- scheduled, preseason or data-volume -- parsed
it. NHC publishes each season's final best track the following spring, so
2024's (and later) was never seen: the data-volume trigger counted fixes in
a file that never changed (always 0), the monthly and preseason retrains
retrained on identical data, and Stage B's test seasons were empty.

`fetch_latest_hurdat2` reads NHC's HURDAT2 directory listing, picks the
Atlantic file with the latest final season (and, for that season, the
latest release date), downloads it, and writes a manifest beside it --
file name, URL, sha256, last season -- that training records on every
registered model. If the listing can't be read it falls back to the pinned
file, and says so in the manifest rather than pretending.

Run at image build (both images) and at the start of every training job
(``docker/cloud-run-training/entrypoint.sh``), via ``anemoi hurdat2-fetch``.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections.abc import Callable
from pathlib import Path

INDEX_URL = "https://www.nhc.noaa.gov/data/hurdat/"
PINNED_NAME = "hurdat2-atl-1851-2023-042624.txt"
#: Atlantic files only: ``hurdat2-1851-2024-040425.txt`` and the older
#: ``hurdat2-atl-1851-2023-042624.txt`` naming; never ``hurdat2-nepac-…``.
#: The trailing six digits are the release date, MMDDYY.
_NAME_RE = re.compile(r"hurdat2-(?:atl-)?1851-(\d{4})-(\d{2})(\d{2})(\d{2})\.txt")

_TIMEOUT_S = 60.0


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "anemoi/1.0"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:  # noqa: S310
        return resp.read()


def latest_name(index_html: str) -> str | None:
    """The Atlantic HURDAT2 file with the latest final season in a listing,
    the latest release of it when there are several; None if there's none."""
    best: tuple[tuple[int, int, int, int], str] | None = None
    for match in _NAME_RE.finditer(index_html):
        season, mm, dd, yy = (int(g) for g in match.groups())
        key = (season, 2000 + yy, mm, dd)
        if best is None or key > best[0]:
            best = (key, match.group(0))
    return best[1] if best else None


def last_season(name: str) -> int:
    match = _NAME_RE.fullmatch(name)
    if not match:
        raise ValueError(f"not a HURDAT2 Atlantic file name: {name!r}")
    return int(match.group(1))


def manifest_path(dest: Path | str) -> Path:
    return Path(dest).with_suffix(".json")


def fetch_latest_hurdat2(
    dest: Path | str, *, fetch: Callable[[str], bytes] = _get,
) -> dict[str, object]:
    """Download the newest Atlantic HURDAT2 to ``dest`` and write its
    manifest (`manifest_path`). Falls back to the pinned file when the
    listing can't be read or names none (``"fallback": true``). Raises only
    when no file at all can be downloaded."""
    dest = Path(dest)
    fallback_reason = None
    try:
        name = latest_name(fetch(INDEX_URL).decode("utf-8", errors="replace"))
        if name is None:
            fallback_reason = "no Atlantic HURDAT2 file in the listing"
    except Exception as exc:  # noqa: BLE001 - the pinned file is still a real archive
        name, fallback_reason = None, f"listing unreadable: {type(exc).__name__}: {exc}"
    name = name or PINNED_NAME
    url = INDEX_URL + name
    body = fetch(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    manifest: dict[str, object] = {
        "file": name,
        "url": url,
        "sha256": hashlib.sha256(body).hexdigest(),
        "last_season": last_season(name),
        "fallback": fallback_reason is not None,
    }
    if fallback_reason:
        manifest["fallback_reason"] = fallback_reason
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
