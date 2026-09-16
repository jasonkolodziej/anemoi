"""Anemoi-API: the developer interface (Branding Brief v1.2, product module table).

A FastAPI service over the reference implementation's operational logic:
cycle scheduling, the source registry, the model/god catalog, the demo
inference path (``run_cycle``), the model registry, and monitoring. It does
not add forecast skill or new data ingestion -- it disseminates what
``anemoi.inference`` already computes, over HTTP instead of stdout.

See ``docs/api.md`` for the design policy and the wiki's API page for the
full endpoint reference this package implements.
"""

from __future__ import annotations

__all__ = ["__api_version__"]

__api_version__ = "1.0.0"
