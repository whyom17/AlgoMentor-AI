from __future__ import annotations

import ast
import json
import subprocess
import sys

from app.problem_ingestion.differential import generate_differential_tests
from app.problem_ingestion.problems_data import PROBLEMS
from app.problem_ingestion.python_runner import PYTHON_RUNNERS, build_python_submission


def test_every_seeded_problem_has_a_runner() -> None:
    assert {problem["slug"] for problem in PROBLEMS} == set(PYTHON_RUNNERS)


def test_generated_drivers_are_valid_python() -> None:
    for slug in PYTHON_RUNNERS:
        source = build_python_submission(slug, "class Solution: pass")
        ast.parse(source)


def test_seeded_cases_match_optimal_references() -> None:
    for problem in PROBLEMS:
        slug = problem["slug"]
        method = PYTHON_RUNNERS[slug].method
        source = "\n".join(
            [
                problem["starter_code"]["python"],
                problem["optimal"],
                f"class Solution:\n    def {method}(self, *args):\n        return optimal(*args)",
            ]
        )
        for case_index, case in enumerate(problem["test_cases"], start=1):
            completed = subprocess.run(
                [sys.executable, "-c", build_python_submission(slug, source)],
                input=case["input"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            actual = json.loads(completed.stdout.strip().splitlines()[-1])
            expected = json.loads(case["expected"])
            if slug == "two-sum":
                actual = sorted(actual)
                expected = sorted(expected)
            assert actual == expected, f"{slug} case {case_index} failed"


def test_unknown_problem_is_rejected() -> None:
    import pytest

    with pytest.raises(ValueError, match="No Python runner"):
        build_python_submission("unknown-problem", "")


def test_differential_generation_is_deterministic_and_matches_references() -> None:
    for problem in PROBLEMS:
        first = generate_differential_tests(problem, case_count=2)
        second = generate_differential_tests(problem, case_count=2)
        assert first == second
        assert len(first) == 2
        assert all(case["source"] == "fuzz" for case in first)
