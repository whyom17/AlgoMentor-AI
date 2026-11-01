"""Problem routes — list and detail."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_optional
from app.database import get_db
from app.models import Problem, User
from app.schemas import ProblemDetail, ProblemListItem

router = APIRouter(prefix="/problems", tags=["problems"])


@router.get("", response_model=list[ProblemListItem])
async def list_problems(
    difficulty: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_current_user_optional),
) -> list[Problem]:
    q = select(Problem).where(Problem.is_published == True)  # noqa: E712
    if difficulty:
        q = q.where(Problem.difficulty == difficulty)
    if tag:
        q = q.where(Problem.tags.contains([tag]))
    q = q.order_by(Problem.created_at)
    result = await db.execute(q)
    return list(result.scalars().all())


@router.get("/{slug}", response_model=ProblemDetail)
async def get_problem(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _user: User | None = Depends(get_current_user_optional),
) -> Problem:
    result = await db.execute(
        select(Problem).where(Problem.slug == slug, Problem.is_published == True)  # noqa: E712
    )
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found.")
    return problem
