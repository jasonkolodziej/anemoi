"""Durable checkpoint storage (PLAN.md §4 "Models" row).

CheckpointStore's public surface is exercised entirely against an in-memory
fake client -- the same duck-typing tests.test_registry.py uses for its
MLflow stub -- so this suite needs no real R2/S3 credentials. The boto3
adapter's wiring gets one lightweight test guarded by importorskip; it never
makes a network call.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from anemoi.tracking.checkpoint_store import CheckpointStore, CheckpointStoreError, S3Config

CONFIG = S3Config(
    endpoint_url="https://example.r2.cloudflarestorage.com",
    bucket="anemoi-checkpoints",
    access_key_id="key",
    secret_access_key="secret",
)


class FakeClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key, local_path):
        self.objects[key] = Path(local_path).read_bytes()

    def get(self, key, local_path):
        if key not in self.objects:
            raise KeyError(key)
        Path(local_path).write_bytes(self.objects[key])

    def exists(self, key):
        return key in self.objects

    def list_keys(self, prefix):
        return sorted(k for k in self.objects if k.startswith(prefix))


def test_upload_returns_an_s3_uri_and_stores_the_bytes(tmp_path):
    store = CheckpointStore(CONFIG, client=FakeClient())
    ckpt = tmp_path / "stage_a.pt"
    ckpt.write_bytes(b"weights")

    uri = store.upload(ckpt, "lstm/stage_a/v1.pt")

    assert uri == "s3://anemoi-checkpoints/lstm/stage_a/v1.pt"
    assert store.exists("lstm/stage_a/v1.pt")


def test_download_round_trips_the_uploaded_bytes(tmp_path):
    store = CheckpointStore(CONFIG, client=FakeClient())
    ckpt = tmp_path / "stage_a.pt"
    ckpt.write_bytes(b"weights")
    uri = store.upload(ckpt, "lstm/stage_a/v1.pt")

    restored = tmp_path / "restored.pt"
    store.download(uri, restored)

    assert restored.read_bytes() == b"weights"


def test_upload_missing_file_raises():
    store = CheckpointStore(CONFIG, client=FakeClient())
    with pytest.raises(CheckpointStoreError, match="no such checkpoint"):
        store.upload("/does/not/exist.pt", "x")


def test_download_rejects_a_uri_from_a_different_bucket(tmp_path):
    store = CheckpointStore(CONFIG, client=FakeClient())
    with pytest.raises(CheckpointStoreError, match="not in this store's bucket"):
        store.download("s3://other-bucket/x.pt", tmp_path / "x.pt")


def test_list_filters_by_prefix(tmp_path):
    store = CheckpointStore(CONFIG, client=FakeClient())
    for key in ("lstm/stage_a/v1.pt", "lstm/stage_b/v1.pt", "cnn/stage_a/v1.pt"):
        ckpt = tmp_path / "ckpt.pt"
        ckpt.write_bytes(b"x")
        store.upload(ckpt, key)

    assert store.list("lstm/") == ["lstm/stage_a/v1.pt", "lstm/stage_b/v1.pt"]


def test_s3config_from_env_reads_the_documented_variable_names(monkeypatch):
    monkeypatch.setenv("S3_ARTIFACT_API_ENDPOINT", "https://x.r2.cloudflarestorage.com")
    monkeypatch.setenv("S3_ARTIFACT_BUCKET", "anemoi-checkpoints")
    monkeypatch.setenv("S3_ARTIFACT_ACCESS_KEYID", "key")
    monkeypatch.setenv("S3_ARTIFACT_SECRET_ACCESS_KEY", "secret")

    config = S3Config.from_env()

    assert config.bucket == "anemoi-checkpoints"
    assert config.endpoint_url == "https://x.r2.cloudflarestorage.com"


def test_s3config_from_env_raises_a_clear_error_when_incomplete(monkeypatch):
    for var in (
        "S3_ARTIFACT_API_ENDPOINT",
        "S3_ARTIFACT_BUCKET",
        "S3_ARTIFACT_ACCESS_KEYID",
        "S3_ARTIFACT_SECRET_ACCESS_KEY",
    ):
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(CheckpointStoreError, match="example.env"):
        S3Config.from_env()


@pytest.mark.storage
def test_boto3_adapter_configures_the_client_for_the_given_endpoint(monkeypatch):
    boto3 = pytest.importorskip("boto3")
    captured = {}

    def fake_client(service, **kwargs):
        captured["service"] = service
        captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(boto3, "client", fake_client)
    from anemoi.tracking.checkpoint_store import _Boto3Client

    _Boto3Client(CONFIG)

    assert captured["service"] == "s3"
    assert captured["kwargs"]["endpoint_url"] == CONFIG.endpoint_url
    assert captured["kwargs"]["aws_access_key_id"] == CONFIG.access_key_id
    assert captured["kwargs"]["aws_secret_access_key"] == CONFIG.secret_access_key
