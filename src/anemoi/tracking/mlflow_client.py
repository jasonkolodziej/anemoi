"""Optional real MLflow client construction, alongside the local-JSON
registry path `tracking.registry.ModelRegistry` already falls back to
when MLflow is absent or unreachable (Scope v2.1 §10.1 -- "MLflow server
down" must never fail a training run).

Nothing downstream *requires* this module to return a real client: every
caller passes ``mlflow_client_from_env()``'s result straight through as
`ModelRegistry`'s already-optional, already-duck-typed ``mlflow_client``
constructor argument. It returns ``None`` -- not an exception -- whenever
MLflow isn't actually usable: the ``tracking`` extra isn't installed,
``MLFLOW_TRACKING_URI`` isn't set, or the server doesn't answer at
startup. A caller never needs to know which case applied; it can pass
the result through unconditionally, exactly as if the caller had written
``mlflow_client=None`` itself.

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
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mlflow.tracking import MlflowClient

#: MLflow's own convention for where the tracking server lives
#: (mlflow.tracking.set_tracking_uri reads the same variable) -- reused
#: rather than a project-specific name, so any existing MLflow tooling
#: (the `mlflow` CLI, ad-hoc scripts) already points at the same server.
TRACKING_URI_ENV = "MLFLOW_TRACKING_URI"


#: MLflow's own HTTP retry settings, defaulted (never overridden -- an
#: explicit env value wins) so an unreachable server costs seconds, not
#: minutes. MLflow's defaults are 7 retries with a doubling backoff and a
#: 120 s timeout: about four minutes per call against a server that
#: answers 502. A stage logs several calls, so a down server once stalled a
#: GPU training run with the GPU idle (2026-11-12). Two retries still ride
#: out a blip.
FAIL_FAST_ENV = {
    "MLFLOW_HTTP_REQUEST_MAX_RETRIES": "2",
    "MLFLOW_HTTP_REQUEST_TIMEOUT": "20",
}


def mlflow_client_from_env(*, probe: bool = True) -> MlflowClient | None:
    """Build a real ``mlflow.tracking.MlflowClient`` from
    ``MLFLOW_TRACKING_URI``, or return ``None`` if MLflow isn't installed,
    the URI isn't set, or (``probe``) the server doesn't answer one
    read-only call -- every case `ModelRegistry` treats identically
    (local-JSON registry, mirrored to durable storage).

    MLflow is optional: what it records is also written to durable storage
    (`experiment_tracking.log_curriculum_stages`), so a server that's down
    at the start of a run is skipped for the whole run instead of being
    retried at every stage."""
    tracking_uri = os.environ.get(TRACKING_URI_ENV)
    if not tracking_uri:
        return None

    try:
        from mlflow.tracking import MlflowClient
    except ModuleNotFoundError:
        return None

    for name, value in FAIL_FAST_ENV.items():
        os.environ.setdefault(name, value)
    client = MlflowClient(tracking_uri=tracking_uri)
    if probe:
        try:
            client.search_experiments(max_results=1)
        except Exception as exc:  # noqa: BLE001 - any failure means "not usable now"
            print(
                f"MLflow at {tracking_uri} is unreachable ({type(exc).__name__}); "
                "continuing without it -- stage runs are still recorded in durable storage",
                file=sys.stderr,
            )
            return None
    return client
