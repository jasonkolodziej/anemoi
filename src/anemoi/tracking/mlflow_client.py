"""Optional real MLflow client construction, alongside the local-JSON
registry path `tracking.registry.ModelRegistry` already falls back to
when MLflow is absent or unreachable (Scope v2.1 §10.1 -- "MLflow server
down" must never fail a training run).

Nothing downstream *requires* this module to return a real client: every
caller passes ``mlflow_client_from_env()``'s result straight through as
`ModelRegistry`'s already-optional, already-duck-typed ``mlflow_client``
constructor argument. It returns ``None`` -- not an exception -- whenever
MLflow isn't actually usable: the ``tracking`` extra isn't installed, or
``MLFLOW_TRACKING_URI`` isn't set. A caller never needs to know which case
applied; it can pass the result through unconditionally, exactly as if the
caller had written ``mlflow_client=None`` itself.

The Cloudflare Access service-token headers `docker/mlflow/`'s server
needs (when deployed behind a Cloudflare Tunnel + Access, per that
directory's README) are added automatically by
`tracking.cloudflare_access.CloudflareAccessRequestHeaderProvider`, a
plugin MLflow discovers on its own via the ``mlflow.request_header_provider``
entry point this package registers in ``pyproject.toml`` -- nothing to
wire up here or at any call site.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mlflow.tracking import MlflowClient

#: MLflow's own convention for where the tracking server lives
#: (mlflow.tracking.set_tracking_uri reads the same variable) -- reused
#: rather than a project-specific name, so any existing MLflow tooling
#: (the `mlflow` CLI, ad-hoc scripts) already points at the same server.
TRACKING_URI_ENV = "MLFLOW_TRACKING_URI"


def mlflow_client_from_env() -> MlflowClient | None:
    """Build a real ``mlflow.tracking.MlflowClient`` from
    ``MLFLOW_TRACKING_URI``, or return ``None`` if MLflow isn't installed
    or the URI isn't set -- the two cases `ModelRegistry` already treats
    identically (local-JSON-only)."""
    tracking_uri = os.environ.get(TRACKING_URI_ENV)
    if not tracking_uri:
        return None

    try:
        from mlflow.tracking import MlflowClient
    except ModuleNotFoundError:
        return None

    return MlflowClient(tracking_uri=tracking_uri)
