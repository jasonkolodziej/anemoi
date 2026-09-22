"""Durable ReferenceDistribution persistence (monitoring.reference_store, #148)."""

from __future__ import annotations

import numpy as np
import pytest

from anemoi.data.sources import Flavor
from anemoi.monitoring.drift import DriftError, ReferenceDistribution
from anemoi.monitoring.reference_store import (
    REFERENCE_STORE_KEY,
    load_reference,
    reference_from_json,
    reference_to_json,
    save_reference,
)
from anemoi.tracking.checkpoint_store import CheckpointStore, S3Config

_CONFIG = S3Config(
    endpoint_url="https://example.r2.cloudflarestorage.com",
    bucket="anemoi-checkpoints", access_key_id="key", secret_access_key="secret",
)


class _FakeClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key, local_path):
        self.objects[key] = local_path.read_bytes()

    def get(self, key, local_path):
        local_path.write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))


def _make_reference() -> ReferenceDistribution:
    return ReferenceDistribution(
        flavor=Flavor.GDAS_FINETUNE,
        feature_names=("shear_magnitude_kt", "sst_c"),
        mean=np.array([12.5, 28.0]),
        std=np.array([4.0, 1.5]),
        n=250,
    )


def test_json_round_trips_a_real_reference_exactly():
    reference = _make_reference()
    restored = reference_from_json(reference_to_json(reference))
    assert restored.flavor is reference.flavor
    assert restored.feature_names == reference.feature_names
    np.testing.assert_array_equal(restored.mean, reference.mean)
    np.testing.assert_array_equal(restored.std, reference.std)
    assert restored.n == reference.n


def test_reference_from_json_raises_on_malformed_payload():
    with pytest.raises(DriftError, match="not a valid reference"):
        reference_from_json("not json")


def test_reference_from_json_raises_on_missing_fields():
    with pytest.raises(DriftError, match="not a valid reference"):
        reference_from_json('{"flavor": "gdas_finetune"}')


def test_save_then_load_round_trips_via_the_local_file(tmp_path):
    reference = _make_reference()
    path = tmp_path / "sub" / "reference.json"
    save_reference(reference, path)
    assert path.exists()

    loaded = load_reference(path)
    assert loaded is not None
    assert loaded.feature_names == reference.feature_names
    np.testing.assert_array_equal(loaded.mean, reference.mean)


def test_load_reference_returns_none_when_nothing_was_ever_fit(tmp_path):
    assert load_reference(tmp_path / "never_written.json") is None


def test_durable_round_trip_via_a_shared_checkpoint_store(tmp_path):
    """A fresh process (nothing local yet) must be able to pull a
    reference someone else fit and pushed earlier -- the real scenario
    this durable mirror exists for (a Cloudflare Container cold start)."""
    store = CheckpointStore(_CONFIG, client=_FakeClient())
    reference = _make_reference()

    writer_path = tmp_path / "writer" / "reference.json"
    save_reference(reference, writer_path, checkpoint_store=store)
    assert store.exists(REFERENCE_STORE_KEY)

    reader_path = tmp_path / "reader" / "reference.json"
    assert not reader_path.exists()
    loaded = load_reference(reader_path, checkpoint_store=store)

    assert loaded is not None
    assert loaded.feature_names == reference.feature_names
    np.testing.assert_array_equal(loaded.mean, reference.mean)
    assert reader_path.exists()  # pulled down locally, not just read from memory


def test_load_reference_degrades_honestly_when_the_store_is_unreachable(tmp_path):
    class _BrokenClient:
        def exists(self, key):
            raise ConnectionError("simulated store outage")

    store = CheckpointStore(_CONFIG, client=_BrokenClient())
    # Must not raise -- a flaky durable store must never crash the live
    # API process just because it wants to check for a reference.
    assert load_reference(tmp_path / "reference.json", checkpoint_store=store) is None
