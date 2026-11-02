"""Tests for the mastery decay model."""


from app.mastery.decay_model import (
    AttemptOutcome,
    apply_decay,
    compute_mastery_update,
    mastery_label,
    update_problem_difficulty,
)


class TestSM2MasteryModel:
    def _outcome(
        self,
        solved: bool = True,
        max_hint_level: int = 0,
        time_spent_seconds: int = 300,
        attempt_count_before: int = 5,
    ) -> AttemptOutcome:
        return AttemptOutcome(
            solved=solved,
            max_hint_level=max_hint_level,
            time_spent_seconds=time_spent_seconds,
            attempt_count_before=attempt_count_before,
        )

    def test_independent_solve_increases_score(self) -> None:
        outcome = self._outcome(solved=True, max_hint_level=0)
        update = compute_mastery_update(0.5, 2.5, 6.0, outcome)
        assert update.new_score > 0.5

    def test_failed_solve_decreases_score(self) -> None:
        outcome = self._outcome(solved=False, max_hint_level=0)
        update = compute_mastery_update(0.7, 2.5, 6.0, outcome)
        assert update.new_score < 0.7

    def test_heavily_hint_assisted_solve_penalised(self) -> None:
        clean = self._outcome(solved=True, max_hint_level=0)
        assisted = self._outcome(solved=True, max_hint_level=4)
        starting_score = 0.5
        clean_update = compute_mastery_update(starting_score, 2.5, 6.0, clean)
        assisted_update = compute_mastery_update(starting_score, 2.5, 6.0, assisted)
        assert clean_update.new_score > assisted_update.new_score

    def test_score_clamped_to_0_1(self) -> None:
        # Even many perfect solves shouldn't exceed 1.0
        score = 0.0
        ef = 2.5
        interval = 1.0
        for _ in range(20):
            outcome = self._outcome(solved=True, max_hint_level=0, attempt_count_before=_)
            update = compute_mastery_update(score, ef, interval, outcome)
            score = update.new_score
            ef = update.new_sm2_ef
            interval = update.new_sm2_interval
        assert 0.0 <= score <= 1.0

    def test_hint_assisted_flag(self) -> None:
        outcome = self._outcome(solved=True, max_hint_level=3)
        update = compute_mastery_update(0.5, 2.5, 6.0, outcome)
        assert update.is_hint_assisted is True

    def test_not_hint_assisted_below_l3(self) -> None:
        outcome = self._outcome(solved=True, max_hint_level=2)
        update = compute_mastery_update(0.5, 2.5, 6.0, outcome)
        assert update.is_hint_assisted is False


class TestDecay:
    def test_no_decay_within_interval(self) -> None:
        score = 0.8
        decayed = apply_decay(score, days_since_practice=3.0, sm2_interval=6.0)
        assert decayed == score  # no decay within window

    def test_decay_after_interval(self) -> None:
        score = 0.8
        decayed = apply_decay(score, days_since_practice=20.0, sm2_interval=6.0)
        assert decayed < score

    def test_decay_never_negative(self) -> None:
        decayed = apply_decay(0.1, days_since_practice=1000.0, sm2_interval=1.0)
        assert decayed >= 0.0


class TestMasteryLabel:
    def test_unseen_label(self) -> None:
        assert mastery_label(0.9, attempt_count=0) == "unseen"

    def test_struggling_label(self) -> None:
        assert mastery_label(0.1, attempt_count=5) == "struggling"

    def test_owned_label(self) -> None:
        assert mastery_label(0.95, attempt_count=10) == "owned"


class TestDifficultyCalibration:
    def test_independent_solve_increases_rating(self) -> None:
        updated = update_problem_difficulty(1200.0, solved=True, max_hint_level=0)
        assert updated > 1200.0

    def test_hint_heavy_solve_does_not_over_increase_rating(self) -> None:
        clean = update_problem_difficulty(1200.0, solved=True, max_hint_level=0)
        assisted = update_problem_difficulty(1200.0, solved=True, max_hint_level=4)
        assert assisted < clean

    def test_failed_submission_reduces_rating(self) -> None:
        updated = update_problem_difficulty(1200.0, solved=False, max_hint_level=0)
        assert updated < 1200.0
