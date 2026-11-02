"""
Submission routes — submit code, poll result.

All code execution flows through sandbox_adapter (AGENTS.md constraint #1).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import AsyncSessionLocal, get_db
from app.mastery.decay_model import (
    AttemptOutcome,
    compute_mastery_update,
    update_problem_difficulty,
)
from app.models import Attempt, MasteryScore, Problem, SubmissionStatus, TestCase, User
from app.problem_ingestion.python_runner import (
    PYTHON_RUNNERS,
    build_python_submission,
)
from app.sandbox_adapter import ExecutionRequest, submit_code, wait_for_result
from app.schemas import AttemptResultResponse, SubmitCodeRequest, SubmitCodeResponse

router = APIRouter(prefix="/submissions", tags=["submissions"])


async def _update_mastery_after_attempt(
    attempt: Attempt,
    db: AsyncSession,
) -> None:
    """Update mastery scores for all tags of the problem after a terminal attempt."""
    result = await db.execute(select(Problem).where(Problem.id == attempt.problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        return

    solved = attempt.status == SubmissionStatus.ACCEPTED
    outcome = AttemptOutcome(
        solved=solved,
        max_hint_level=attempt.max_hint_level,
        time_spent_seconds=0,
        attempt_count_before=0,
    )

    for tag in problem.tags:
        ms_result = await db.execute(
            select(MasteryScore).where(
                MasteryScore.user_id == attempt.user_id,
                MasteryScore.topic_tag == tag,
            )
        )
        ms = ms_result.scalar_one_or_none()

        if ms is None:
            ms = MasteryScore(
                user_id=attempt.user_id,
                topic_tag=tag,
            )
            db.add(ms)

        outcome.attempt_count_before = ms.attempt_count
        update = compute_mastery_update(
            current_score=ms.score,
            current_ef=ms.sm2_ef,
            current_interval=ms.sm2_interval,
            outcome=outcome,
        )
        ms.score = update.new_score
        ms.sm2_ef = update.new_sm2_ef
        ms.sm2_interval = update.new_sm2_interval
        ms.next_review_at = update.next_review_at
        ms.attempt_count += 1
        ms.last_practiced_at = datetime.now(UTC)
        if solved:
            ms.solve_count += 1
        if update.is_hint_assisted:
            ms.hint_assisted_count += 1

    await db.commit()


def _outputs_match(slug: str, actual: str, expected: str) -> bool:
    try:
        actual_value = json.loads(actual.strip().splitlines()[-1])
        expected_value = json.loads(expected)
    except (IndexError, json.JSONDecodeError):
        return False

    if slug == "two-sum" and isinstance(actual_value, list):
        actual_value = sorted(actual_value)
        expected_value = sorted(expected_value)
    return actual_value == expected_value


async def _evaluate_attempt(attempt_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        attempt = await db.get(Attempt, attempt_id)
        if attempt is None:
            return

        problem = await db.get(Problem, attempt.problem_id)
        if problem is None:
            attempt.status = SubmissionStatus.INTERNAL_ERROR
            attempt.result = {"stderr": "Problem data is unavailable."}
            attempt.completed_at = datetime.now(UTC)
            await db.commit()
            return

        cases_result = await db.execute(
            select(TestCase).where(TestCase.problem_id == problem.id).order_by(TestCase.order)
        )
        test_cases = list(cases_result.scalars().all())
        test_results: list[dict[str, int | str]] = []
        final_status = SubmissionStatus.ACCEPTED
        total_time_ms = 0.0
        max_memory_kb = 0
        stderr = ""
        compile_output = ""

        failing_trace: dict[str, object] | None = None
        for index, test_case in enumerate(test_cases, start=1):
            try:
                submitted = await submit_code(
                    ExecutionRequest(
                        source_code=build_python_submission(problem.slug, attempt.source_code),
                        language="python",
                        stdin=test_case.input_data,
                        time_limit_ms=problem.time_limit_ms,
                        memory_limit_mb=problem.memory_limit_mb,
                    )
                )
                execution = await wait_for_result(submitted.token)
            except Exception:
                final_status = SubmissionStatus.INTERNAL_ERROR
                test_results.append({"case": index, "status": "error"})
                continue

            total_time_ms += execution.time_ms or 0
            max_memory_kb = max(max_memory_kb, execution.memory_kb or 0)
            if execution.status != SubmissionStatus.ACCEPTED.value:
                try:
                    final_status = SubmissionStatus(execution.status)
                except ValueError:
                    final_status = SubmissionStatus.INTERNAL_ERROR
                stderr = execution.stderr
                compile_output = execution.compile_output
                failing_trace = {
                    "failed_input": test_case.input_data,
                    "expected_output": test_case.expected_output,
                    "actual_output": execution.stdout,
                    "error_message": execution.stderr or execution.compile_output or execution.status,
                    "case_index": index,
                }
                test_results.append({"case": index, "status": "error"})
                continue

            passed = _outputs_match(problem.slug, execution.stdout, test_case.expected_output)
            test_results.append({"case": index, "status": "passed" if passed else "failed"})
            if not passed and final_status == SubmissionStatus.ACCEPTED:
                final_status = SubmissionStatus.WRONG_ANSWER
                failing_trace = {
                    "failed_input": test_case.input_data,
                    "expected_output": test_case.expected_output,
                    "actual_output": execution.stdout,
                    "error_message": "Output mismatch",
                    "case_index": index,
                }

        if not test_cases:
            final_status = SubmissionStatus.INTERNAL_ERROR
            stderr = "This problem has no test cases configured."

        attempt.status = final_status
        attempt.execution_trace = failing_trace
        attempt.result = {
            "stderr": stderr,
            "compile_output": compile_output,
            "time_ms": total_time_ms,
            "memory_kb": max_memory_kb or None,
            "test_results": test_results,
            "execution_trace": failing_trace,
        }
        attempt.completed_at = datetime.now(UTC)
        await db.commit()

        problem.difficulty_rating = update_problem_difficulty(
            problem.difficulty_rating,
            solved=final_status == SubmissionStatus.ACCEPTED,
            max_hint_level=attempt.max_hint_level,
        )
        await db.commit()
        await _update_mastery_after_attempt(attempt, db)


@router.post("", response_model=SubmitCodeResponse, status_code=202)
async def submit(
    body: SubmitCodeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SubmitCodeResponse:
    # Find problem
    prob_result = await db.execute(
        select(Problem).where(Problem.slug == body.problem_slug, Problem.is_published == True)  # noqa: E712
    )
    problem = prob_result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found.")
    if body.language.lower() != "python" or problem.slug not in PYTHON_RUNNERS:
        raise HTTPException(
            status_code=422,
            detail="This Phase 0 problem currently supports Python submissions only.",
        )

    # Create attempt record
    attempt = Attempt(
        user_id=user.id,
        problem_id=problem.id,
        language=body.language,
        source_code=body.source_code,
        status=SubmissionStatus.PENDING,
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    attempt.status = SubmissionStatus.RUNNING
    await db.commit()
    background_tasks.add_task(_evaluate_attempt, attempt.id)

    return SubmitCodeResponse(
        attempt_id=attempt.id,
        judge0_token="",
        status="pending",
    )


@router.get("/{attempt_id}", response_model=AttemptResultResponse)
async def get_attempt_result(
    attempt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttemptResultResponse:
    result = await db.execute(
        select(Attempt).where(
            Attempt.id == attempt_id,
            Attempt.user_id == user.id,
        )
    )
    attempt = result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    res = attempt.result or {}
    return AttemptResultResponse(
        attempt_id=attempt.id,
        status=attempt.status.value,
        stdout="",
        stderr=res.get("stderr", ""),
        compile_output=res.get("compile_output", ""),
        time_ms=res.get("time_ms"),
        memory_kb=res.get("memory_kb"),
        execution_trace=attempt.execution_trace or res.get("execution_trace"),
        test_results=res.get("test_results", []),
    )
