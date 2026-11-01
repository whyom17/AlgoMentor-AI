"""Mastery dashboard and recommendations routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.mastery.decay_model import apply_decay, mastery_label
from app.mastery.variants import get_next_variant
from app.models import Attempt, MasteryScore, Problem, SubmissionStatus, User
from app.schemas import MasteryDashboard, RecommendedProblem, TopicMastery

router = APIRouter(prefix="/mastery", tags=["mastery"])


@router.get("/dashboard", response_model=MasteryDashboard)
async def mastery_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MasteryDashboard:
    # Total attempt / solve counts
    counts_result = await db.execute(
        select(
            func.count(Attempt.id).label("total"),
            func.count(Attempt.id).filter(
                Attempt.status == SubmissionStatus.ACCEPTED
            ).label("solved"),
        ).where(Attempt.user_id == user.id)
    )
    row = counts_result.one()

    # All mastery scores, with decay applied
    ms_result = await db.execute(
        select(MasteryScore).where(MasteryScore.user_id == user.id)
    )
    now = datetime.now(UTC)
    topics: list[TopicMastery] = []
    for ms in ms_result.scalars().all():
        days_since = 0.0
        if ms.last_practiced_at:
            lp = ms.last_practiced_at
            if lp.tzinfo is None:
                lp = lp.replace(tzinfo=UTC)
            days_since = (now - lp).total_seconds() / 86400

        decayed_score = apply_decay(ms.score, days_since, ms.sm2_interval)
        topics.append(
            TopicMastery(
                topic_tag=ms.topic_tag,
                score=decayed_score,
                label=mastery_label(decayed_score, ms.attempt_count),
                attempt_count=ms.attempt_count,
                solve_count=ms.solve_count,
                next_review_at=ms.next_review_at,
            )
        )

    topics.sort(key=lambda t: t.score)

    return MasteryDashboard(
        user_id=user.id,
        total_solved=row.solved or 0,
        total_attempts=row.total or 0,
        topics=topics,
    )


@router.get("/recommendations", response_model=list[RecommendedProblem])
async def get_recommendations(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RecommendedProblem]:
    now = datetime.now(UTC)

    ms_result = await db.execute(
        select(MasteryScore).where(MasteryScore.user_id == user.id)
    )
    mastery_items = list(ms_result.scalars().all())

    # Get slugs the user has solved
    solved_result = await db.execute(
        select(Attempt.problem_id).where(
            Attempt.user_id == user.id,
            Attempt.status == SubmissionStatus.ACCEPTED,
        )
    )
    solved_problem_ids = {row[0] for row in solved_result.all()}

    # Map problem_id -> slug
    if solved_problem_ids:
        slug_result = await db.execute(
            select(Problem.id, Problem.slug).where(
                Problem.id.in_(solved_problem_ids)
            )
        )
        solved_slugs: set[str] = {row[1] for row in slug_result.all()}
    else:
        solved_slugs = set()

    recommendations: list[RecommendedProblem] = []

    # Priority 1: topics due for spaced repetition review
    due_topics = [
        ms for ms in mastery_items
        if ms.next_review_at and ms.next_review_at.replace(tzinfo=UTC) <= now
    ]
    due_topics.sort(key=lambda ms: ms.next_review_at or now)

    for ms in due_topics:
        next_slug = get_next_variant(ms.topic_tag, solved_slugs)
        if next_slug:
            prob_result = await db.execute(
                select(Problem).where(
                    Problem.slug == next_slug, Problem.is_published == True  # noqa: E712
                )
            )
            problem = prob_result.scalar_one_or_none()
            if problem:
                recommendations.append(
                    RecommendedProblem(
                        slug=problem.slug,
                        title=problem.title,
                        difficulty=problem.difficulty.value,
                        reason=f"Due for review: {ms.topic_tag}",
                        pattern_family=problem.pattern_family,
                    )
                )

    # Priority 2: weakest topics not yet started
    if len(recommendations) < limit:
        # Find published problems the user hasn't attempted at all
        attempted_result = await db.execute(
            select(Attempt.problem_id).where(Attempt.user_id == user.id)
        )
        attempted_ids = {row[0] for row in attempted_result.all()}

        unseen_result = await db.execute(
            select(Problem).where(
                Problem.is_published == True,  # noqa: E712
                ~Problem.id.in_(attempted_ids) if attempted_ids else True,
            ).limit(limit * 2)
        )
        for problem in unseen_result.scalars().all():
            if len(recommendations) >= limit:
                break
            if not any(r.slug == problem.slug for r in recommendations):
                recommendations.append(
                    RecommendedProblem(
                        slug=problem.slug,
                        title=problem.title,
                        difficulty=problem.difficulty.value,
                        reason="New problem in your curriculum",
                        pattern_family=problem.pattern_family,
                    )
                )

    return recommendations[:limit]
