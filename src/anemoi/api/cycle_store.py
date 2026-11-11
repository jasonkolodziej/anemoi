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
    from ..data.besttrack import Track
    from ..inference.cycle import CycleOutput
    from ..tracking.checkpoint_store import CheckpointStore

CYCLES_PREFIX = "api/cycles/"
DRIFT_LIVE_KEY = "api/drift_live.json"
#: One record per cycle *run* (#214) -- a replaced manual run keeps its own.
CYCLE_INPUTS_PREFIX = "archive/cycles/"
#: How many fixes up to the cycle time the input record keeps: the LSTM's
#: window (`capacity_ablation.SEQUENCE_LENGTH` + 1 = 9) with room to spare.
FIX_WINDOW = 12


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


def cycle_inputs_prefix(result: schemas.CycleResult) -> str:
    label = result.payload.cycle
    started = result.provenance.started_at if result.provenance else result.payload.issued_at
    return (
        f"{CYCLE_INPUTS_PREFIX}{label[:4]}/{result.storm_id}/{label}/"
        f"{started:%Y%m%dT%H%M%SZ}/"
    )


def save_cycle_inputs(
    store: CheckpointStore, result: schemas.CycleResult, track: Track, fields: object | None,
) -> str:
    """What one cycle run ran on (#214), under ``archive/cycles/{year}/
    {storm}/{label}/{started}/``:

    * ``manifest.json`` -- the served result (with its ``run`` and
      ``provenance``: fix source, model versions, fusion, gridded source,
      commit, config digest) and the storm's fixes up to the cycle time, as
      known when it ran;
    * ``fields.npz`` -- the storm-centred gridded fields the models read,
      when there were any (`data.gridded_cache`'s format).

    With the commit, these are enough to rebuild every model's input
    tensor. Returns the prefix written.
    """
    from ..data.gridded_cache import FetchTask, save_cached_fields

    prefix = cycle_inputs_prefix(result)
    target = result.provenance.fix.valid_time if result.provenance else None
    window = [f for f in track.fixes if target is None or f.valid_time <= target][-FIX_WINDOW:]
    manifest = {
        "result": result.model_dump(mode="json"),
        "fix_window": [
            {
                "valid_time": f.valid_time.isoformat(), "lat": f.lat, "lon": f.lon,
                "max_wind_kt": f.max_wind_kt, "min_pressure_mb": f.min_pressure_mb,
                "quality": f.quality.value,
            }
            for f in window
        ],
        "fields": "fields.npz" if fields is not None else None,
    }
    if fields is not None and result.provenance is not None:
        fix = result.provenance.fix
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fields.npz"
            save_cached_fields(
                path, fields,  # type: ignore[arg-type]
                FetchTask(result.storm_id, fix.valid_time, fix.lat, fix.lon),
            )
            store.upload(path, prefix + "fields.npz")
    _put_text(store, prefix + "manifest.json", json.dumps(manifest, indent=1))
    return prefix


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
