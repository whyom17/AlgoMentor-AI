"""
Mastery model — SM-2-adapted decay-based per-topic scoring.

Key design decisions (from PRD Section 9):
  - Score in [0, 1], recency-weighted.
  - Decay modelled on SM-2 spaced repetition.
  - Hint-adjusted: heavy hint use marks a topic 'seen' not 'owned'.
  - Confidence band based on sample size.
  - Cold-start: tag-frequency recommendations until ~15-20 attempts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class AttemptOutcome:
    """Single attempt signal fed into the mastery updater."""
    solved: bool
    # 0 = no hints; 1 = L1 only; 2 = L2; 3 = L3; 4 = L4 (fully assisted)
    max_hint_level: int
    # Duration in seconds
    time_spent_seconds: int
    attempt_count_before: int


@dataclass
class MasteryUpdate:
    """Values to persist for a MasteryScore row."""
    new_score: float
    new_sm2_interval: float
    new_sm2_ef: float
    next_review_at: datetime
    is_hint_assisted: bool  # true if solved with L3/L4 hints


# ─── SM-2 algorithm ──────────────────────────────────────────────────────────

_MIN_EF = 1.3
_BASE_EF = 2.5


def _sm2_grade(outcome: AttemptOutcome) -> int:
    """
    Map an attempt outcome to an SM-2 grade [0-5].
    5 = perfect recall, 0 = complete blackout.
    """
    if not outcome.solved:
        # Failed — check if they were close
        if outcome.max_hint_level == 0 and outcome.attempt_count_before < 2:
            return 1  # didn't know, first real try
        return 0  # repeated failure

    if outcome.max_hint_level == 0:
        return 5  # solved independently, perfect
    elif outcome.max_hint_level <= 1:
        return 4  # minor hint
    elif outcome.max_hint_level == 2:
        return 3  # pattern nudge needed
    elif outcome.max_hint_level == 3:
        return 2  # needed pseudocode
    else:
        return 1  # fully walked through (L4) — barely counts


_MAX_INTERVAL_DAYS = 365  # prevent timedelta overflow on long streaks


def _sm2_update(
    ef: float, interval: float, grade: int
) -> tuple[float, float]:
    """
    Run one SM-2 iteration.
    Returns (new_ef, new_interval_days), capped at _MAX_INTERVAL_DAYS.
    """
    new_ef = max(_MIN_EF, ef + 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02))

    if grade < 3:
        # Failed — reset interval
        new_interval = 1.0
    elif interval < 1:
        new_interval = 1.0
    elif interval < 6:
        new_interval = 6.0
    else:
        new_interval = interval * new_ef

    return new_ef, min(new_interval, _MAX_INTERVAL_DAYS)


# ─── Score calculation ────────────────────────────────────────────────────────


def _raw_score(outcome: AttemptOutcome) -> float:
    """
    Compute a raw [0, 1] mastery increment for this attempt.
    Heavily penalised for hint-assisted solves.
    """
    if not outcome.solved:
        return 0.0

    base = 1.0
    # Hint penalty: L1 = -0.05, L2 = -0.15, L3 = -0.35, L4 = -0.55
    hint_penalties = {0: 0.0, 1: 0.05, 2: 0.15, 3: 0.35, 4: 0.55}
    penalty = hint_penalties.get(outcome.max_hint_level, 0.55)
    return max(0.0, base - penalty)


def compute_mastery_update(
    current_score: float,
    current_ef: float,
    current_interval: float,
    outcome: AttemptOutcome,
    now: datetime | None = None,
) -> MasteryUpdate:
    """
    Compute the new mastery state after one attempt.

    Uses an EMA-style score update weighted by the SM-2 grade quality,
    combined with SM-2 interval scheduling.
    """
    if now is None:
        now = datetime.now(UTC)

    grade = _sm2_grade(outcome)
    new_ef, new_interval = _sm2_update(current_ef, current_interval, grade)

    raw = _raw_score(outcome)

    # Exponential moving average — new score weighted toward recent performance
    # Weight for new evidence: decays with existing sample size
    alpha = 0.3 if outcome.attempt_count_before >= 5 else 0.5
    new_score = current_score * (1 - alpha) + raw * alpha

    # Confidence band: clamp score based on small sample uncertainty
    confidence = min(1.0, (outcome.attempt_count_before + 1) / 10)
    # For very early attempts, pull score toward 0.5 (uncertainty)
    if confidence < 0.5:
        new_score = new_score * confidence + 0.5 * (1 - confidence)

    new_score = max(0.0, min(1.0, new_score))

    next_review_at = now + timedelta(days=new_interval)

    return MasteryUpdate(
        new_score=round(new_score, 4),
        new_sm2_interval=round(new_interval, 2),
        new_sm2_ef=round(new_ef, 4),
        next_review_at=next_review_at,
        is_hint_assisted=outcome.max_hint_level >= 3,
    )


# ─── Decay ───────────────────────────────────────────────────────────────────


def apply_decay(
    score: float,
    days_since_practice: float,
    sm2_interval: float,
) -> float:
    """
    Apply time-based decay to a mastery score.

    Uses an exponential decay with a half-life equal to the SM-2 interval.
    If the user hasn't practiced within their scheduled interval, the score decays.
    """
    if days_since_practice <= sm2_interval:
        return score  # Within review window — no decay yet

    excess_days = days_since_practice - sm2_interval
    half_life = max(sm2_interval, 7.0)  # minimum 7-day half-life
    decay = math.exp(-0.693 * excess_days / half_life)

    return round(max(0.0, score * decay), 4)


# ─── Mastery label ────────────────────────────────────────────────────────────


def mastery_label(score: float, attempt_count: int) -> str:
    """Human-readable mastery label for display in the dashboard."""
    if attempt_count < 2:
        return "unseen"
    if score < 0.2:
        return "struggling"
    if score < 0.45:
        return "seen"
    if score < 0.7:
        return "practicing"
    if score < 0.88:
        return "proficient"
    return "owned"
