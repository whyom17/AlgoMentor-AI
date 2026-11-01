"""Mastery module public interface."""

from app.mastery.decay_model import (
    AttemptOutcome,
    MasteryUpdate,
    apply_decay,
    compute_mastery_update,
    mastery_label,
)
from app.mastery.variants import (
    VARIANT_MAP,
    get_next_variant,
    get_variants_for_pattern,
)

__all__ = [
    "AttemptOutcome",
    "MasteryUpdate",
    "compute_mastery_update",
    "apply_decay",
    "mastery_label",
    "VARIANT_MAP",
    "get_variants_for_pattern",
    "get_next_variant",
]
