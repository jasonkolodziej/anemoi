"""What a version records about the basins it covers (docs/multi_basin.md).

One model per architecture is trained on every configured basin. Its
validation metrics already carry, per basin, its own errors, its sample
counts, and what persistence scores on exactly the same windows
(`real_run.validation_metrics`). From those:

* `basin_tags` gives the two registry tags the serving side reads:
  ``trained_basins`` -- the basins it had training samples from (a gridded
  model has none where no field was cached) -- and ``verified_basins``, the
  ones where it also beat persistence on the promotion metric
  (`metrics.basin.verified_basins`, `ModelRegistry.verified_basins`);
* `resolve_basin_inputs` fixes which of its basin input columns are live.
  A column for a basin it had no training samples from is blanked, once,
  here -- on the artifacts every later step reads (the joint latents
  fusion and diffusion train on, and the ``basin_inputs`` tag serving
  builds inputs from) -- so a model is never fed an input whose weights
  were never trained, and training and serving can't disagree about it.
"""

from __future__ import annotations

from dataclasses import replace

from ..metrics.basin import trained_basins, verified_basins
from ..tracking.experiment_tracking import TRAINED_BASINS_TAG, VERIFIED_BASINS_TAG
from .promotion import PRIMARY_METRIC, MetricSet


def basin_tags(val_metrics: MetricSet) -> dict[str, str]:
    """The registry tags saying which basins a version trained on and which
    it is verified in, from its validation metrics. Empty for a run that
    recorded no per-basin sample counts -- its tags are left to whatever
    else sets them."""
    trained = trained_basins(val_metrics.values)
    if trained is None:
        return {}
    return {
        TRAINED_BASINS_TAG: ",".join(trained),
        VERIFIED_BASINS_TAG: ",".join(verified_basins(val_metrics.values, PRIMARY_METRIC)),
    }


def served_columns(columns: tuple[str, ...], trained: tuple[str, ...]) -> tuple[str, ...]:
    """``columns`` with every basin not in ``trained`` blanked (``""``),
    in the same order: no storm switches a blank column on."""
    return tuple(b if b in trained else "" for b in columns)


def resolve_basin_inputs(artifacts: object, val_metrics: MetricSet) -> object:
    """``artifacts`` (a `real_run.RunArtifacts`) with its basin input
    columns resolved against the basins it had training samples from
    (`served_columns`). PINN's candidate generator keeps its own columns,
    resolved by its own training (`real_run_pinn.run_pinn_curriculum`).

    Returned unchanged when there is nothing to resolve: no basin columns,
    or a run that recorded no per-basin counts.
    """
    columns = tuple(getattr(artifacts, "basins", ()) or ())
    trained = trained_basins(val_metrics.values)
    if not columns or trained is None:
        return artifacts
    return replace(artifacts, basins=served_columns(columns, trained))
