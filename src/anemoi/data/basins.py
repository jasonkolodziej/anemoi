"""Which basins training reads (docs/multi_basin.md).

One model per architecture is trained on every basin in
``curriculum.yaml``'s ``data.basins``, rather than one model per basin: the
physics of motion and intensity is shared, and each basin on its own is a
thin slice of an already small archive. What differs by basin is scored and
gated per basin instead (`training.basin_metrics`, `training.promotion`).

A basin is its two-letter ATCF code, the first two characters of every
storm id (`data.atcf.storm_basin`).
"""

from __future__ import annotations

from collections.abc import Iterable

from .. import config
from .atcf import storm_basin
from .besttrack import Track

#: Every ATCF basin a storm id can carry: Atlantic, Eastern and Central
#: Pacific (NHC/CPHC), Western Pacific, North Indian Ocean and the Southern
#: Hemisphere (JTWC). The order is fixed: it is the order of the basin
#: columns a model takes as input, so changing it would change what a
#: trained checkpoint's inputs mean.
BASIN_VOCABULARY: tuple[str, ...] = ("AL", "EP", "CP", "WP", "IO", "SH")


def _training_basins() -> tuple[str, ...]:
    basins = tuple(config.get_list("curriculum", "data.basins", str))
    unknown = [b for b in basins if b not in BASIN_VOCABULARY]
    if not basins or unknown or len(set(basins)) != len(basins):
        raise config.ConfigError(
            "curriculum.yaml: data.basins must be a non-empty list of distinct ATCF "
            f"basins from {list(BASIN_VOCABULARY)}, got {list(basins)}"
        )
    return basins


#: The basins training reads, from ``curriculum.yaml`` ``data.basins``.
TRAINING_BASINS: tuple[str, ...] = _training_basins()


def basins_of(tracks: Iterable[Track]) -> tuple[str, ...]:
    """The basins ``tracks`` come from, sorted."""
    return tuple(sorted({storm_basin(t.storm_id) for t in tracks}))


def select_basins(
    tracks: Iterable[Track], basins: Iterable[str] = TRAINING_BASINS,
) -> list[Track]:
    """``tracks`` from ``basins`` only, in their original order. An archive
    file can hold more than was asked for: NHC's Northeast Pacific HURDAT2
    carries Eastern and Central Pacific storms together."""
    wanted = frozenset(basins)
    return [t for t in tracks if storm_basin(t.storm_id) in wanted]
