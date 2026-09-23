"""Durable storage for served cycle results and drift samples (#175).

`RealState` runs in a Cloudflare Container that restarts on every deploy and,
since #172, every time it sleeps. Anything held only in its memory -- each
storm's cycle results, the drift monitor's live samples -- disappeared on each
restart, so the console showed storms with no cycles minutes after one ran.

What's stored is the served `schemas.CycleResult` (exactly what
`GET /storms/{id}/cycles/{cycle}` returns), not the internal `CycleOutput`:
the API never serves anything else, and the served shape is plain JSON with
no numpy arrays or nested domain objects to round-trip.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable, Iterable, Iterator, MutableMapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from . import schemas

if TYPE_CHECKING:
    from ..inference.cycle import CycleOutput
    from ..tracking.checkpoint_store import CheckpointStore

CYCLES_PREFIX = "api/cycles/"
DRIFT_LIVE_KEY = "api/drift_live.json"


def cycle_key(storm_id: str, label: str) -> str:
    return f"{CYCLES_PREFIX}{storm_id}/{label}.json"


def _put_text(store: CheckpointStore, key: str, text: str) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "object.json"
        path.write_text(text, encoding="utf-8")
        store.upload(path, key)


def _get_text(store: CheckpointStore, key: str) -> str:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "object.json"
        store.download(f"s3://{store.config.bucket}/{key}", path)
        return path.read_text(encoding="utf-8")


def save_cycle_result(store: CheckpointStore, result: schemas.CycleResult) -> None:
    _put_text(store, cycle_key(result.storm_id, result.payload.cycle), result.model_dump_json())


def load_cycle_result(store: CheckpointStore, storm_id: str, label: str) -> schemas.CycleResult:
    return schemas.CycleResult.model_validate_json(_get_text(store, cycle_key(storm_id, label)))


def list_cycle_labels(store: CheckpointStore) -> dict[str, set[str]]:
    """Every stored cycle label, by storm -- one listing, no downloads."""
    index: dict[str, set[str]] = {}
    for key in store.list(CYCLES_PREFIX):
        rest = key[len(CYCLES_PREFIX):]
        storm_id, _, filename = rest.partition("/")
        if storm_id and filename.endswith(".json") and "/" not in filename:
            index.setdefault(storm_id, set()).add(filename[: -len(".json")])
    return index


def save_drift_live(store: CheckpointStore, features: list[np.ndarray], models: set[str]) -> None:
    body = {
        "features": [np.asarray(f, dtype=float).tolist() for f in features],
        "models": sorted(models),
    }
    _put_text(store, DRIFT_LIVE_KEY, json.dumps(body))


def load_drift_live(store: CheckpointStore) -> tuple[list[np.ndarray], set[str]] | None:
    if not store.exists(DRIFT_LIVE_KEY):
        return None
    body: dict[str, Any] = json.loads(_get_text(store, DRIFT_LIVE_KEY))
    return [np.asarray(f, dtype=float) for f in body["features"]], set(body["models"])


class CycleHistory(MutableMapping):
    """A storm's cycles, keyed by label.

    Holds both kinds a restart can leave: `CycleOutput`s run by this process,
    and labels stored by an earlier container lifetime, whose `CycleResult`
    is downloaded only when first read. Every stored label is known up front
    (so `last_cycle` and a storm's cycle list are right straight after a cold
    start) without downloading every result a storm has ever had.
    """

    def __init__(
        self,
        storm_id: str = "",
        loader: Callable[[str, str], schemas.CycleResult] | None = None,
    ) -> None:
        self._storm_id = storm_id
        self._loader = loader
        self._items: dict[str, CycleOutput | schemas.CycleResult | None] = {}

    def add_stored(self, labels: Iterable[str]) -> None:
        for label in labels:
            self._items.setdefault(label, None)

    def __getitem__(self, label: str) -> CycleOutput | schemas.CycleResult:
        value = self._items[label]
        if value is None:
            if self._loader is None:
                raise KeyError(label)
            try:
                value = self._loader(self._storm_id, label)
            except Exception as exc:  # noqa: BLE001 - unreadable reads as missing, retried next time
                raise KeyError(label) from exc
            self._items[label] = value
        return value

    def __setitem__(self, label: str, value: CycleOutput | schemas.CycleResult) -> None:
        self._items[label] = value

    def __delitem__(self, label: str) -> None:
        del self._items[label]

    def __iter__(self) -> Iterator[str]:
        # A snapshot: request threads iterate (a storm's cycle list, its
        # last_cycle) while another thread's run_cycle adds a label.
        return iter(list(self._items))

    def __len__(self) -> int:
        return len(self._items)
