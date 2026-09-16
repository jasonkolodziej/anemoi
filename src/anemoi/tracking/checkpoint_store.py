"""Durable checkpoint storage (PLAN.md §4 "Models" row; Layer 4 -- tracking).

A rented GPU pod is torn down between runs, so ``training.curriculum.StageResult
.checkpoint_uri`` needs somewhere durable to point at. This is the S3-compatible
(Cloudflare R2 or AWS S3) counterpart to :mod:`anemoi.tracking.registry`'s
MLflow-optional pattern: the storage backend is duck-typed behind a small
put/get/exists/list_keys surface so tests run without real credentials, and
:meth:`S3Config.from_env` is the one place that reads the ``S3_ARTIFACT_*``
variables (see ``example.env``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

_BOTO3_HINT = "checkpoint upload/download needs the 'storage' extra: uv sync --extra storage"

_ENV_VARS = {
    "endpoint_url": "S3_ARTIFACT_API_ENDPOINT",
    "bucket": "S3_ARTIFACT_BUCKET",
    "access_key_id": "S3_ARTIFACT_ACCESS_KEYID",
    "secret_access_key": "S3_ARTIFACT_SECRET_ACCESS_KEY",
}


class CheckpointStoreError(RuntimeError):
    pass


def require_boto3() -> None:
    try:
        import boto3  # noqa: F401
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(_BOTO3_HINT) from exc


@dataclass(frozen=True, slots=True)
class S3Config:
    endpoint_url: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    #: Cloudflare R2 buckets have a single region, conventionally "auto".
    region: str = "auto"

    @classmethod
    def from_env(cls) -> S3Config:
        missing = [env for env in _ENV_VARS.values() if not os.environ.get(env)]
        if missing:
            raise CheckpointStoreError(
                f"missing environment variable(s) {missing} -- copy example.env to "
                ".env and fill in the R2/S3 credentials"
            )
        values = {field: os.environ[env] for field, env in _ENV_VARS.items()}
        return cls(**values)


class _StorageClient(Protocol):
    def put(self, key: str, local_path: Path) -> None: ...
    def get(self, key: str, local_path: Path) -> None: ...
    def exists(self, key: str) -> bool: ...
    def list_keys(self, prefix: str) -> list[str]: ...


class CheckpointStore:
    """Durable checkpoint storage behind a small, duck-typed client surface.

    ``client`` need only implement :class:`_StorageClient`; the real backend is
    a thin boto3 adapter (below) built lazily from ``config``, and tests pass
    an in-memory stub instead -- the same pattern
    :class:`anemoi.tracking.registry.ModelRegistry` uses for its MLflow client.
    """

    def __init__(self, config: S3Config, client: _StorageClient | None = None) -> None:
        self.config = config
        self._client = client if client is not None else _Boto3Client(config)

    def upload(self, local_path: Path | str, key: str) -> str:
        local_path = Path(local_path)
        if not local_path.is_file():
            raise CheckpointStoreError(f"no such checkpoint file: {local_path}")
        self._client.put(key, local_path)
        return f"s3://{self.config.bucket}/{key}"

    def download(self, uri: str, local_path: Path | str) -> Path:
        key = self._key_from_uri(uri)
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self._client.get(key, local_path)
        return local_path

    def exists(self, key: str) -> bool:
        return self._client.exists(key)

    def list(self, prefix: str = "") -> list[str]:
        return self._client.list_keys(prefix)

    def _key_from_uri(self, uri: str) -> str:
        bucket_prefix = f"s3://{self.config.bucket}/"
        if not uri.startswith(bucket_prefix):
            raise CheckpointStoreError(
                f"uri {uri!r} is not in this store's bucket (expected prefix {bucket_prefix!r})"
            )
        return uri[len(bucket_prefix) :]


class _Boto3Client:
    """Adapter from the store's put/get/exists/list_keys surface onto boto3."""

    def __init__(self, config: S3Config) -> None:
        require_boto3()
        import boto3

        self._bucket = config.bucket
        self._s3 = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            region_name=config.region,
        )

    def put(self, key: str, local_path: Path) -> None:
        self._s3.upload_file(str(local_path), self._bucket, key)

    def get(self, key: str, local_path: Path) -> None:
        self._s3.download_file(self._bucket, key, str(local_path))

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                return False
            raise

    def list_keys(self, prefix: str) -> list[str]:
        paginator = self._s3.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            keys.extend(obj["Key"] for obj in page.get("Contents", []))
        return keys
