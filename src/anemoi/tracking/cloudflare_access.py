"""Cloudflare Access service-token headers for the MLflow tracking client
(PLAN.md §4 "Models" / `tracking.registry.ModelRegistry`'s optional MLflow
mirror, `docker/mlflow/`).

The MLflow server in `docker/mlflow/` is meant to sit behind a Cloudflare
Tunnel, gated by Cloudflare Access -- every request needs
``CF-Access-Client-Id``/``CF-Access-Client-Secret`` service-token headers,
or Access intercepts the request with its own login flow before it ever
reaches MLflow. `mlflow.tracking.MlflowClient`'s REST client has no
constructor argument for extra headers, but MLflow has a plugin system for
exactly this: registering a ``RequestHeaderProvider`` (this module, wired
up via this package's own ``mlflow.request_header_provider`` entry point in
``pyproject.toml``) makes MLflow call it on every outgoing request
automatically -- no ``MLFLOW_TRACKING_AUTH`` selection needed, unlike the
separate ``RequestAuthProvider`` mechanism MLflow also has.

Picked up automatically once this package (with the ``tracking`` extra,
i.e. mlflow itself, installed) is present -- MLflow discovers registered
providers via ``importlib.metadata`` entry points at import time, not an
explicit registration call anywhere in this codebase. A no-op (``in_context
()`` returns False) when the two env vars below aren't set, so having this
installed is harmless against an MLflow server that isn't behind Access
(e.g. local dev against `docker/mlflow/` directly).
"""

from __future__ import annotations

import os

from mlflow.tracking.request_header.abstract_request_header_provider import (
    RequestHeaderProvider,
)

#: A Cloudflare Zero Trust service token generated for this project's
#: Access application (Access > Service Auth > Service Tokens in the
#: Cloudflare dashboard) -- never checked in; set alongside the existing
#: S3_ARTIFACT_*/MLFLOW_DB_* vars in the repo root .env (see example.env).
CLIENT_ID_ENV = "CF_ACCESS_CLIENT_ID"
CLIENT_SECRET_ENV = "CF_ACCESS_CLIENT_SECRET"


class CloudflareAccessRequestHeaderProvider(RequestHeaderProvider):
    """Adds the Cloudflare Access service-token headers to every MLflow
    REST request when a token is configured in the environment."""

    def in_context(self) -> bool:
        return bool(os.environ.get(CLIENT_ID_ENV)) and bool(os.environ.get(CLIENT_SECRET_ENV))

    def request_headers(self) -> dict[str, str]:
        return {
            "CF-Access-Client-Id": os.environ[CLIENT_ID_ENV],
            "CF-Access-Client-Secret": os.environ[CLIENT_SECRET_ENV],
        }
