"""Copy a gridded cache to local disk once, before training reads it.

On Cloud Run the caches are a Cloud Storage bucket mounted with gcsfuse at
``/cache``. Training streams each window's fields from the cache on demand
(`training.streaming.WindowDataset`), every epoch: Stage A alone is ~32k
files read 60 times per gridded model. gcsfuse doesn't keep file contents
between opens, so every read is a round trip to the bucket -- across
regions for the GPU job (us-east4 reading us-central1) -- and the GPU waits
on it. The whole ERA5 cache is ~2.4 GB and the GDAS f006 one ~0.2 GB, small
next to the job's memory, so one parallel copy into ``/tmp`` (memory-backed
on Cloud Run) at startup turns ~2.5 million remote reads into ~45k.

Parallel because each file is small (~35-65 KB) and a gcsfuse read is
latency-bound, not bandwidth-bound: many concurrent copies hide the round
trip.
"""

from __future__ import annotations

import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LocalizeReport:
    n_copied: int
    n_skipped: int
    n_bytes: int
    elapsed_s: float


def _files(src: Path) -> list[Path]:
    out: list[Path] = []
    for root, _dirs, names in os.walk(src):
        out.extend(Path(root) / n for n in names)
    return out


def localize_cache(src: Path | str, dst: Path | str, *, workers: int = 64) -> LocalizeReport:
    """Copy every file under ``src`` to the same relative path under
    ``dst``. A file already at ``dst`` with the same size is skipped, so a
    rerun only fills gaps. Raises if any copy fails: a partial local cache
    would silently train on fewer samples, so the caller falls back to
    ``src`` instead."""
    src, dst = Path(src), Path(dst)
    if not src.is_dir():
        raise FileNotFoundError(f"cache directory not found: {src}")
    start = time.monotonic()
    files = _files(src)

    def copy(path: Path) -> tuple[bool, int]:
        target = dst / path.relative_to(src)
        size = path.stat().st_size
        if target.exists() and target.stat().st_size == size:
            return False, 0
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        return True, size

    copied = skipped = n_bytes = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for did_copy, size in pool.map(copy, files):
            if did_copy:
                copied += 1
                n_bytes += size
            else:
                skipped += 1
    return LocalizeReport(copied, skipped, n_bytes, time.monotonic() - start)
