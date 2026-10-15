"""The two-stage training curriculum.

Scope v2.1 §4.6.1.

* **Stage A (pretrain)** -- ERA5, 1980-present, final best-track as labels.
  Buys representation quality from four decades of homogeneous reanalysis.
* **Stage B (fine-tune)** -- GDAS/GFS analyses 2021-present (the real archive's
  verified start -- see ``data.sources``'s ``gdas_gfs`` entry), working-quality
  track as *input*, final best-track still as labels. Buys the thing that
  actually matters: weights adapted to the distribution the model is served.

The invariant this module enforces is that Stage B is never optional. A run
that stops after Stage A produces a model that is excellent on data it will
never see, and :func:`assert_deployable` is what stops it reaching the registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .. import config
from ..data.sources import Flavor, Role, get as get_source


class CurriculumError(RuntimeError):
    """The curriculum was configured or executed in a non-deployable way."""


@dataclass(frozen=True, slots=True)
class StageSpec:
    """Configuration for one curriculum stage."""

    name: str
    flavor: Flavor
    #: Source keys read to build this stage's inputs.
    input_sources: tuple[str, ...]
    #: Source key supplying supervision targets.
    label_source: str
    season_range: tuple[int, int]
    epochs: int
    learning_rate: float
    #: Stage B typically freezes early layers; recorded for reproducibility.
    frozen_modules: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.epochs <= 0:
            raise ValueError("epochs must be positive")
        if not 0.0 < self.learning_rate < 1.0:
            raise ValueError("learning_rate out of range")
        lo, hi = self.season_range
        if lo > hi:
            raise ValueError("season_range start exceeds end")
        if not self.input_sources:
            raise ValueError("a stage needs at least one input source")

        label = get_source(self.label_source)
        if label.role is not Role.LABELS_ONLY:
            raise CurriculumError(
                f"label source {self.label_source!r} has role {label.role.value!r}; "
                "supervision must come from a labels-only source (§4.1)"
            )
        for key in self.input_sources:
            src = get_source(key)
            if src.role is Role.LABELS_ONLY:
                raise CurriculumError(
                    f"{key!r} is labels-only and cannot be a model input (§4.6.2): "
                    "final best-track leaks post-season reanalysis into the inputs"
                )
            if self.flavor is Flavor.GDAS_FINETUNE and src.role is not Role.OPERATIONAL:
                raise CurriculumError(
                    f"Stage B input {key!r} has role {src.role.value!r}; the "
                    "fine-tune stage must read only operational sources (§4.6.1)"
                )

    @property
    def is_operational_flavor(self) -> bool:
        return self.flavor is Flavor.GDAS_FINETUNE


def _stage_config(key: str, name: str, flavor: Flavor) -> dict:
    """curriculum.yaml ``<key>``: the stage's name and flavor are fixed (they
    are what assert_deployable and the registry check), the rest tunable --
    StageSpec still validates every source's role on construction."""
    config.fixed("curriculum", f"{key}.name", name, "stage names are recorded in every run's tags")
    config.fixed(
        "curriculum", f"{key}.flavor", flavor.value,
        "Stage A is the ERA5 pretrain and Stage B the operational fine-tune (§4.6.1)",
    )
    season = config.get_list("curriculum", f"{key}.season_range", int)
    if len(season) != 2:
        raise config.ConfigError(f"curriculum.yaml: {key}.season_range must be [first, last]")
    return {
        "input_sources": tuple(config.get_list("curriculum", f"{key}.input_sources", str)),
        "label_source": config.get("curriculum", f"{key}.label_source", str),
        "season_range": (season[0], season[1]),
        "epochs": config.get("curriculum", f"{key}.epochs", int),
        "learning_rate": config.get("curriculum", f"{key}.learning_rate", float),
    }


_STAGE_A = _stage_config("stage_a", "A", Flavor.ERA5_PRETRAIN)
_STAGE_B = _stage_config("stage_b", "B", Flavor.GDAS_FINETUNE)
_STAGE_B_FROZEN = tuple(config.get_list("curriculum", "stage_b.frozen_modules", str))


def stage_a(
    *,
    epochs: int = _STAGE_A["epochs"],
    learning_rate: float = _STAGE_A["learning_rate"],
    season_range: tuple[int, int] = _STAGE_A["season_range"],
) -> StageSpec:
    """Canonical Stage A: ERA5 pretraining (curriculum.yaml ``stage_a``)."""
    return StageSpec(
        name="A",
        flavor=Flavor.ERA5_PRETRAIN,
        input_sources=_STAGE_A["input_sources"],
        label_source=_STAGE_A["label_source"],
        season_range=season_range,
        epochs=epochs,
        learning_rate=learning_rate,
    )


def stage_b(
    *,
    epochs: int = _STAGE_B["epochs"],
    learning_rate: float = _STAGE_B["learning_rate"],
    season_range: tuple[int, int] = _STAGE_B["season_range"],
    frozen_modules: tuple[str, ...] = _STAGE_B_FROZEN,
) -> StageSpec:
    """Canonical Stage B: GDAS fine-tuning on operational-quality inputs
    (curriculum.yaml ``stage_b``).

    The learning rate is an order of magnitude below Stage A's: the aim is to
    re-seat the model on the operational distribution, not to relearn the
    representation on a decade of data.

    ``season_range`` is (2021, 2023): 2021 is GDAS's verified real archive
    start in ``noaa-gfs-bdp-pds`` (no data exists before it, see
    ``data.sources``'s ``gdas_gfs`` entry); 2023 is the latest season this
    project's HURDAT2 archive (``hurdat2-atl-1851-2023-042624.txt``) has
    final best-track labels for -- Stage B needs both a real GDAS input and a
    real final-best-track label for every season it trains on.
    """
    return StageSpec(
        name="B",
        flavor=Flavor.GDAS_FINETUNE,
        input_sources=_STAGE_B["input_sources"],
        label_source=_STAGE_B["label_source"],
        season_range=season_range,
        epochs=epochs,
        learning_rate=learning_rate,
        frozen_modules=frozen_modules,
    )


@dataclass(frozen=True, slots=True)
class Curriculum:
    """An ordered curriculum for one model."""

    model_name: str
    stages: tuple[StageSpec, ...]

    def __post_init__(self) -> None:
        if not self.stages:
            raise CurriculumError("a curriculum needs at least one stage")
        names = [s.name for s in self.stages]
        if len(set(names)) != len(names):
            raise CurriculumError(f"duplicate stage names: {names}")
        if self.stages[-1].flavor is not Flavor.GDAS_FINETUNE:
            raise CurriculumError(
                f"{self.model_name}: the final stage must be the operational "
                f"({Flavor.GDAS_FINETUNE.value}) flavor -- a curriculum ending on "
                "ERA5 produces a model that has never seen its serving distribution"
            )

    @property
    def deployable_stage(self) -> StageSpec:
        """The stage whose weights are eligible for promotion."""
        return self.stages[-1]

    @classmethod
    def standard(cls, model_name: str, **kwargs) -> Curriculum:
        return cls(model_name=model_name, stages=(stage_a(**kwargs.get("a", {})), stage_b(**kwargs.get("b", {}))))


@dataclass(slots=True)
class StageResult:
    """Outcome of running one stage."""

    stage_name: str
    flavor: Flavor
    epochs_completed: int
    final_train_loss: float
    final_val_loss: float
    checkpoint_uri: str
    completed_at: datetime | None = None

    @property
    def is_operational_flavor(self) -> bool:
        return self.flavor is Flavor.GDAS_FINETUNE


@dataclass(slots=True)
class CurriculumRun:
    """Accumulated results across a curriculum."""

    curriculum: Curriculum
    results: list[StageResult] = field(default_factory=list)

    def record(self, result: StageResult) -> None:
        expected = self.curriculum.stages[len(self.results)]
        if result.stage_name != expected.name:
            raise CurriculumError(
                f"stage out of order: expected {expected.name!r}, got {result.stage_name!r}"
            )
        if result.flavor is not expected.flavor:
            raise CurriculumError(
                f"stage {result.stage_name}: expected flavor {expected.flavor.value}, "
                f"got {result.flavor.value}"
            )
        self.results.append(result)

    @property
    def complete(self) -> bool:
        return len(self.results) == len(self.curriculum.stages)

    @property
    def final_result(self) -> StageResult:
        if not self.results:
            raise CurriculumError("no stages have run")
        return self.results[-1]

    def result(self, stage_name: str) -> StageResult:
        for r in self.results:
            if r.stage_name == stage_name:
                return r
        raise KeyError(stage_name)


def assert_deployable(run: CurriculumRun) -> None:
    """Gate: refuse to promote weights that never saw the operational flavor.

    This is the counterpart to the §5.3 Stage 6 change -- promotion metrics are
    computed on Stage B, and Stage B must have actually run.
    """
    if not run.complete:
        done = [r.stage_name for r in run.results]
        raise CurriculumError(
            f"{run.curriculum.model_name}: curriculum incomplete (ran {done}); "
            "Stage B fine-tuning on operational inputs is mandatory before promotion"
        )
    if not run.final_result.is_operational_flavor:
        raise CurriculumError(
            f"{run.curriculum.model_name}: final stage flavor is "
            f"{run.final_result.flavor.value}, expected {Flavor.GDAS_FINETUNE.value}"
        )
