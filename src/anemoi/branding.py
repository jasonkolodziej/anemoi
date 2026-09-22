"""Sub-brand registry: the Anemoi.

Branding Brief v1.1 §2.2. Each model architecture is personified as one of the
Greek wind gods, and that name -- not the architecture -- is the identifier the
rest of the system shows: MLflow experiment names, run tags, model-status
badges, track-line colours in the console, API endpoint documentation.

The architecture names remain the module names (``models/lstm.py``) because
that is what they are. This module is the one place that maps between the two,
so a rename on either side stays a single edit.

The three product modules (§2.3) are also recorded here: ``Anemoi-Core`` is the
fused deterministic engine, ``Anemoi-Spread`` the diffusion ensemble generator,
``Anemoi-Fusion`` the consensus weighting layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

PRODUCT = "Anemoi"
TAGLINE = "Many winds. One forecast."


class Module(str, Enum):
    """Product modules (§2.3)."""

    CORE = "Anemoi-Core"
    SPREAD = "Anemoi-Spread"
    FUSION = "Anemoi-Fusion"
    API = "Anemoi-API"
    STREAM = "Anemoi-Stream"


@dataclass(frozen=True, slots=True)
class WindGod:
    """One personified model architecture."""

    #: Lowercase identifier: MLflow experiment name, run tag, API path segment.
    slug: str
    #: Display name for UI and documentation.
    name: str
    #: Compass direction; drives position in radial/wind-rose layouts.
    direction: str
    #: Signature colour (§5.2). Track lines, status badges, MLflow run tags.
    color: str
    #: Architecture module under :mod:`anemoi.models`.
    architecture: str
    #: Which product module this god belongs to.
    module: Module
    #: One-line character note, used in docs and onboarding.
    persona: str


#: Ordered north, south, east, west, then the diagonals -- the order the logo
#: glyph assembles in, and the order status panels list.
GODS: tuple[WindGod, ...] = (
    WindGod("boreas", "Boreas", "N", "#06B6D4", "lstm", Module.CORE,
            "Fast, violent, first to arrive. The sprinter."),
    WindGod("notus", "Notus", "S", "#F59E0B", "transformer", Module.CORE,
            "Heavy, deliberate, sees the whole sky. The strategist."),
    WindGod("eurus", "Eurus", "E", "#EF4444", "gnn", Module.CORE,
            "Unpredictable, turbulent, inner-core specialist. The maverick."),
    WindGod("zephyrus", "Zephyrus", "W", "#10B981", "cnn", Module.CORE,
            "Gentle, visual, spring-like. The observer."),
    WindGod("kaikias", "Kaikias", "NE", "#8B5CF6", "pinn", Module.CORE,
            "Rigid, constrained, unyielding. The disciplinarian."),
    WindGod("skiron", "Skiron", "NW", "#EC4899", "diffusion", Module.SPREAD,
            "Generative, spreading, mist-like. The oracle."),
)

_BY_SLUG = {g.slug: g for g in GODS}
_BY_ARCHITECTURE = {g.architecture: g for g in GODS}

#: Structural winds (§5.3). Southeast and southwest carry no model: they exist
#: so the eight-point wind rose closes. Never assign these to data -- if a
#: colour appears on a track line it must map to exactly one model.
STRUCTURAL_COLORS: dict[str, str] = {
    "SE": "#FB923C",  # Euronotus -- structural only; repurposed as Training in v3
    "SW": "#A3E635",  # Lips -- structural only; repurposed as Degraded in v3
}

#: Functional colors (§5.4) used for neutral text and state semantics, not for
#: model identity. These are deliberately separate from the six-god palette.
FUNCTIONAL_COLORS: dict[str, str] = {
    "Eye": "#F8FAFC",
    "Cirrus": "#94A3B8",
    "Cumulus": "#64748B",
    "Landfall": "#F43F5E",
    "Clear": "#22D3EE",
}

#: The fusion layer is a model but not a god: it is the consensus of all six,
#: so it takes the neutral Eye colour rather than a direction.
FUSION_COLOR = FUNCTIONAL_COLORS["Eye"]

#: Status semantics (§8.2). These are not model identity colors.
STATUS_COLORS: dict[str, str] = {
    "online": FUNCTIONAL_COLORS["Clear"],
    "training": STRUCTURAL_COLORS["SE"],
    "degraded": STRUCTURAL_COLORS["SW"],
    "offline": FUNCTIONAL_COLORS["Cumulus"],
}


def god(slug_or_architecture: str) -> WindGod:
    """Resolve a god by its slug (``"boreas"``) or architecture (``"lstm"``).

    Raises :class:`KeyError` on an unknown name rather than guessing: a typo in
    an MLflow experiment name is a run that cannot be found again later, which
    is the failure the tagging convention in §7.2 exists to prevent.
    """
    key = slug_or_architecture.lower()
    if key in _BY_SLUG:
        return _BY_SLUG[key]
    if key in _BY_ARCHITECTURE:
        return _BY_ARCHITECTURE[key]
    raise KeyError(
        f"{slug_or_architecture!r} is not a wind god or a known architecture; "
        f"expected one of {sorted(_BY_SLUG)} or {sorted(_BY_ARCHITECTURE)}"
    )


def experiment_name(slug_or_architecture: str) -> str:
    """MLflow experiment name for a model. The god slug, nothing decorative.

    ``"fusion"`` is a real, deliberate special case, not an oversight:
    fusion has no ``WindGod`` entry by design (see ``FUSION_COLOR``'s own
    comment -- "a model but not a god"), so routing it through ``god()``
    always raised ``KeyError``. That exception was silently swallowed by
    `tracking.experiment_tracking.log_stage_run`'s catch-all
    ``except Exception: return None`` (deliberate -- tracking must never
    fail a training run), so a real fusion training run would complete,
    register, and upload its checkpoint successfully, just with
    ``mlflow_run_id=None`` -- no MLflow run, no logged metrics, anywhere,
    for a model that otherwise looks identical to the other six in every
    other respect. Found via a real full-schedule VM run (2026-09-18):
    ``MlflowClient.get_model_version("fusion", ...).run_id`` came back as
    the empty string while every other model's did not.
    """
    if slug_or_architecture.lower() == "fusion":
        return "fusion"
    return god(slug_or_architecture).slug


def color_for(slug_or_architecture: str) -> str:
    """Signature colour for track lines and status badges (§5.2)."""
    return god(slug_or_architecture).color


__all__ = [
    "PRODUCT",
    "TAGLINE",
    "Module",
    "WindGod",
    "GODS",
    "STRUCTURAL_COLORS",
    "FUNCTIONAL_COLORS",
    "FUSION_COLOR",
    "STATUS_COLORS",
    "god",
    "experiment_name",
    "color_for",
]
