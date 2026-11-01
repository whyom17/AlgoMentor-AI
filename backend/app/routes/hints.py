"""
Hints routes.

AGENTS.md constraint #4: Interview/Contest mode must NOT have any code path
to this endpoint. That is enforced at the API layer — this router is not
included in contest-mode routes (handled in main.py routing).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.mentor.orchestrator import HintContext, get_hint
from app.models import Attempt, HintEvent, HintLevel, Problem, User
from app.schemas import HintRequest, HintResponse

router = APIRouter(prefix="/hints", tags=["hints"])


@router.post("", response_model=HintResponse)
async def request_hint(
    body: HintRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HintResponse:
    # Load attempt (user must own it)
    attempt_result = await db.execute(
        select(Attempt).where(
            Attempt.id == body.attempt_id,
            Attempt.user_id == user.id,
        )
    )
    attempt = attempt_result.scalar_one_or_none()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found.")

    # Load the problem
    prob_result = await db.execute(
        select(Problem).where(Problem.id == attempt.problem_id)
    )
    problem = prob_result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found.")

    # Count frontier hints used today (for rate limiting free tier)
    today_start = datetime.now(UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    frontier_count_result = await db.execute(
        select(func.count(HintEvent.id)).where(
            HintEvent.user_id == user.id,
            HintEvent.hint_level.in_([HintLevel.L3_PSEUDOCODE, HintLevel.L4_WALKTHROUGH]),
            HintEvent.created_at >= today_start,
        )
    )
    frontier_hints_today = frontier_count_result.scalar() or 0

    # Calculate time spent (rough: seconds since attempt created)
    time_spent = int(
        (datetime.now(UTC) - attempt.created_at.replace(tzinfo=UTC)).total_seconds()
    )

    # Build hint context
    ctx = HintContext(
        problem_slug=problem.slug,
        problem_description=problem.description,
        problem_constraints=problem.constraints,
        pattern_family=problem.pattern_family,
        tags=problem.tags,
        user_code=attempt.source_code,
        language=attempt.language,
        last_status=attempt.status.value,
        last_stdout=attempt.result.get("stdout", "") if attempt.result else "",
        last_stderr=attempt.result.get("stderr", "") if attempt.result else "",
        execution_trace=attempt.execution_trace,
        attempt_count=attempt.hint_count,
        hint_count_already=attempt.hint_count,
        time_spent_seconds=time_spent,
        is_pro=user.is_pro,
        frontier_hints_today=frontier_hints_today,
    )

    # Get hint from orchestrator (enforces all constraints)
    hint = await get_hint(ctx, body.hint_level)

    # Persist hint event
    hint_event = HintEvent(
        user_id=user.id,
        attempt_id=attempt.id,
        hint_level=HintLevel(hint.hint_level),
        code_snapshot=attempt.source_code,
        trace_context=attempt.execution_trace,
        response_text=hint.text,
        model_used=hint.model_used,
        tokens_used=hint.tokens_used,
        latency_ms=hint.latency_ms,
    )
    db.add(hint_event)

    # Update attempt hint counters
    attempt.hint_count += 1
    attempt.max_hint_level = max(attempt.max_hint_level, hint.hint_level)
    await db.commit()

    return HintResponse(
        hint_level=hint.hint_level,
        text=hint.text,
        model_used=hint.model_used,
        was_filtered=hint.was_filtered,
        latency_ms=hint.latency_ms,
    )
