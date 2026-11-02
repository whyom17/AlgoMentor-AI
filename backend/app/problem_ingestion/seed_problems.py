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
from app.problem_ingestion.differential import generate_differential_tests
from app.problem_ingestion.problems_data import PROBLEMS


async def seed() -> None:
    # Create tables if they don't exist yet
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        inserted = 0
        skipped = 0
        updated = 0
        for data in PROBLEMS:
            existing = await db.execute(select(Problem).where(Problem.slug == data["slug"]))
            existing_problem = existing.scalar_one_or_none()
            if existing_problem:
                existing_cases_result = await db.execute(
                    select(TestCase).where(TestCase.problem_id == existing_problem.id)
                )
                existing_cases = list(existing_cases_result.scalars().all())
                existing_fuzz_inputs = {
                    test_case.input_data
                    for test_case in existing_cases
                    if test_case.source == "fuzz"
                }
                if len(existing_fuzz_inputs) >= 16:
                    print(f"  [skip] {data['slug']} already has fuzz tests")
                    skipped += 1
                    continue

                fuzz_cases = generate_differential_tests(data)
                next_order = max((test_case.order for test_case in existing_cases), default=-1) + 1
                added_fuzz_count = 0
                for fuzz_case in fuzz_cases:
                    if fuzz_case["input"] in existing_fuzz_inputs:
                        continue
                    db.add(
                        TestCase(
                            problem_id=existing_problem.id,
                            input_data=fuzz_case["input"],
                            expected_output=fuzz_case["expected"],
                            is_hidden=True,
                            is_sample=False,
                            source="fuzz",
                            order=next_order,
                        )
                    )
                    next_order += 1
                    added_fuzz_count += 1
                    existing_fuzz_inputs.add(fuzz_case["input"])

                existing_problem.hidden_test_count = (
                    sum(
                        1
                        for test_case in existing_cases
                        if test_case.is_hidden or not test_case.is_sample
                    )
                    + added_fuzz_count
                )
                updated += 1
                print(f"  [update] {data['slug']} with differential tests")
                continue

            fuzz_cases = generate_differential_tests(data)
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

            all_test_cases = data.get("test_cases", []) + fuzz_cases
            for i, tc in enumerate(all_test_cases):
                test_case = TestCase(
                    problem_id=problem.id,
                    input_data=tc["input"],
                    expected_output=tc["expected"],
                    is_hidden=not tc.get("is_sample", False),
                    is_sample=tc.get("is_sample", False),
                    source=tc.get("source", "manual"),
                    order=i,
                )
                db.add(test_case)

            problem.hidden_test_count = sum(
                1 for tc in all_test_cases if not tc.get("is_sample", False)
            )
            inserted += 1
            print(f"  [insert] {data['slug']}")

        await db.commit()
        print(f"\nDone. Inserted {inserted} problems, updated {updated}, skipped {skipped}.")


if __name__ == "__main__":
    asyncio.run(seed())
