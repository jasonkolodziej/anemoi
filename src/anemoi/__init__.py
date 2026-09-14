"""Anemoi hurricane forecast platform.

Reference implementation of Scope v2.1. The package is organised around the two
things v2.1 changed:

* :mod:`anemoi.data` and :mod:`anemoi.training.curriculum` implement the
  train/serve consistency policy (§4.6) -- ERA5 pretrains, GDAS serves, and
  final best-track never becomes a model input.
* :mod:`anemoi.inference.scheduler` implements the corrected operational timing
  (§6.2) -- cycle t runs on the t-6 NWP cycle, gated on TC-Vitals arrival, with
  products due ahead of the t+3:00 advisory.

Product modules (Branding Brief §2.3): **Anemoi-Core** is the fused
deterministic engine, **Anemoi-Spread** the diffusion ensemble generator, and
**Anemoi-Fusion** the consensus weighting layer. :mod:`anemoi.branding` maps
each architecture to its wind god.
"""

from __future__ import annotations

__version__ = "2.1.0"

from .branding import GODS, Module, god
from .data.sources import Flavor, Role
from .time_utils import cycle_label, select_nwp_cycle

__all__ = [
    "__version__",
    "Flavor",
    "Role",
    "cycle_label",
    "select_nwp_cycle",
    "GODS",
    "Module",
    "god",
]
