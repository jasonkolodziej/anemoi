"""Durable persistence for `monitoring.drift.ReferenceDistribution` (#148).

The reference distribution -- the real Stage B (GDAS_FINETUNE) feature
statistics `detect_feature_drift` compares live samples against -- is fit
once, offline (`anemoi drift-reference-fit`), from real cached GDAS
fields, not by the live API process itself. This module is how that
fitted result reaches a running `RealState`: local JSON (readable without
any credentials, matching `tracking.registry`'s own local-first design)
plus a best-effort durable mirror via the same `CheckpointStore`
`tracking.registry.ModelRegistry` already uses for its own JSON payload --
same reasoning applies here: a Cloudflare Container's ephemeral disk has
nothing on it at cold start, so without a durable mirror a freshly-started
API process would never see a reference someone fit hours or days earlier
from a different machine.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from ..data.sources import Flavor
from .drift import DriftError, ReferenceDistribution

#: Durable-storage key `ModelRegistry`'s own REGISTRY_STORE_KEY lives
#: alongside -- one shared checkpoint_store, several JSON payloads at
#: distinct keys, same pattern this codebase already uses for the
#: registry itself.
REFERENCE_STORE_KEY = "monitoring/drift_reference_gdas_finetune.json"


def reference_to_json(reference: ReferenceDistribution) -> str:
    return json.dumps(
        {
            "flavor": reference.flavor.value,
            "feature_names": list(reference.feature_names),
            "mean": reference.mean.tolist(),
            "std": reference.std.tolist(),
            "n": reference.n,
        },
        indent=2,
        sort_keys=True,
    )


def reference_from_json(text: str) -> ReferenceDistribution:
    try:
        data = json.loads(text)
        return ReferenceDistribution(
            flavor=Flavor(data["flavor"]),
            feature_names=tuple(data["feature_names"]),
            mean=np.array(data["mean"], dtype=float),
            std=np.array(data["std"], dtype=float),
            n=int(data["n"]),
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        raise DriftError(f"not a valid reference distribution payload: {exc}") from exc


def save_reference(reference: ReferenceDistribution, path: Path, checkpoint_store=None) -> None:
    """Write ``path`` locally, then best-effort push to durable storage --
    same "local write always succeeds, the durable mirror is opportunistic"
    contract `ModelRegistry._save`/`_push_to_checkpoint_store` already use."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(reference_to_json(reference))
    if checkpoint_store is None:
        return
    try:
        checkpoint_store.upload(path, REFERENCE_STORE_KEY)
    except Exception:  # noqa: BLE001 - fitting a reference must never fail on a flaky store
        pass


def load_reference(path: Path, checkpoint_store=None) -> ReferenceDistribution | None:
    """Best-effort pull from durable storage (if configured), then read
    ``path`` -- ``None`` if nothing has ever been fit yet, not an
    exception; a fresh deployment with no reference fit is a real, valid
    state (drift reporting degrades honestly, same as skew's "not yet
    built" note), not a startup failure."""
    path = Path(path)
    if checkpoint_store is not None:
        try:
            if checkpoint_store.exists(REFERENCE_STORE_KEY):
                bucket = checkpoint_store.config.bucket
                checkpoint_store.download(f"s3://{bucket}/{REFERENCE_STORE_KEY}", path)
        except Exception:  # noqa: BLE001 - a stale/local-only reference must still be usable
            pass
    if not path.exists():
        return None
    return reference_from_json(path.read_text())
