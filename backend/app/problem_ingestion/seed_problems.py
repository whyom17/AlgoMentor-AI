"""
Seed script — loads Phase 0 problems into the database.

Usage:
  cd backend
  python -m app.problem_ingestion.seed_problems

This uses the synchronous SQLAlchemy URL to keep the seed script simple.
"""

import asyncio

from sqlalchemy import select

from app.database import AsyncSessionLocal, Base, engine
from app.models import Difficulty, Problem, TestCase
from app.problem_ingestion.problems_data import PROBLEMS


async def seed() -> None:
    # Create tables if they don't exist yet
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        inserted = 0
        skipped = 0
        for data in PROBLEMS:
            existing = await db.execute(
                select(Problem).where(Problem.slug == data["slug"])
            )
            if existing.scalar_one_or_none():
                print(f"  [skip] {data['slug']} already exists")
                skipped += 1
                continue

            problem = Problem(
                slug=data["slug"],
                title=data["title"],
                difficulty=Difficulty(data["difficulty"]),
                pattern_family=data["pattern_family"],
                tags=data["tags"],
                description=data["description"],
                constraints=data["constraints"],
                examples=data["examples"],
                starter_code=data.get("starter_code", {}),
                time_limit_ms=data.get("time_limit_ms", 2000),
                memory_limit_mb=data.get("memory_limit_mb", 256),
                is_published=True,
            )
            db.add(problem)
            await db.flush()  # get problem.id

            for i, tc in enumerate(data.get("test_cases", [])):
                test_case = TestCase(
                    problem_id=problem.id,
                    input_data=tc["input"],
                    expected_output=tc["expected"],
                    is_hidden=not tc.get("is_sample", False),
                    is_sample=tc.get("is_sample", False),
                    source="manual",
                    order=i,
                )
                db.add(test_case)

            problem.hidden_test_count = sum(
                1 for tc in data.get("test_cases", []) if not tc.get("is_sample", False)
            )
            inserted += 1
            print(f"  [insert] {data['slug']}")

        await db.commit()
        print(f"\nDone. Inserted {inserted} problems, skipped {skipped}.")


if __name__ == "__main__":
    asyncio.run(seed())
