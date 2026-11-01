"""
Submission routes — submit code, poll result.

All code execution flows through sandbox_adapter (AGENTS.md constraint #1).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.mastery.decay_model import AttemptOutcome, compute_mastery_update
from app.models import Attempt, MasteryScore, Problem, SubmissionStatus, User
from app.sandbox_adapter import ExecutionRequest, submit_code, wait_for_result
from app.schemas import AttemptResultResponse, SubmitCodeRequest, SubmitCodeResponse

router = APIRouter(prefix="/submissions", tags=["submissions"])


async def _update_mastery_after_attempt(
    attempt: Attempt,
    db: AsyncSession,
) -> None:
    """Update mastery scores for all tags of the problem after a terminal attempt."""
    result = await db.execute(
        select(Problem).where(Problem.id == attempt.problem_id)
    )
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

    # Submit to Judge0 via sandbox adapter
    exec_request = ExecutionRequest(
        source_code=body.source_code,
        language=body.language,
        stdin="",
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
    )
    try:
        exec_result = await submit_code(exec_request)
    except Exception as e:
        attempt.status = SubmissionStatus.INTERNAL_ERROR
        await db.commit()
        raise HTTPException(status_code=502, detail=f"Sandbox error: {e}") from e

    attempt.judge0_token = exec_result.token
    attempt.status = SubmissionStatus.RUNNING
    await db.commit()

    return SubmitCodeResponse(
        attempt_id=attempt.id,
        judge0_token=exec_result.token,
        status="running",
    )


@router.get("/{attempt_id}", response_model=AttemptResultResponse)
async def get_attempt_result(
    attempt_id: uuid.UUID,
    background_tasks: BackgroundTasks,
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

    # If still running, poll Judge0
    if attempt.status in (SubmissionStatus.PENDING, SubmissionStatus.RUNNING):
        if attempt.judge0_token:
            exec_result = await wait_for_result(
                attempt.judge0_token, max_wait_ms=10000
            )
            if exec_result.is_terminal:
                attempt.status = SubmissionStatus(exec_result.status)
                attempt.result = {
                    "stdout": exec_result.stdout,
                    "stderr": exec_result.stderr,
                    "compile_output": exec_result.compile_output,
                    "time_ms": exec_result.time_ms,
                    "memory_kb": exec_result.memory_kb,
                }
                attempt.completed_at = datetime.now(UTC)
                await db.commit()

                # Update mastery in background
                background_tasks.add_task(_update_mastery_after_attempt, attempt, db)

    res = attempt.result or {}
    return AttemptResultResponse(
        attempt_id=attempt.id,
        status=attempt.status.value,
        stdout=res.get("stdout", ""),
        stderr=res.get("stderr", ""),
        compile_output=res.get("compile_output", ""),
        time_ms=res.get("time_ms"),
        memory_kb=res.get("memory_kb"),
    )
