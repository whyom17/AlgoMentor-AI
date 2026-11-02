"""Deterministic differential-test generation for curated Python problems."""

from __future__ import annotations

import json
import random
import subprocess
import sys
from typing import Any

from app.problem_ingestion.python_runner import PYTHON_RUNNERS, build_python_submission


class DifferentialTestError(RuntimeError):
    """Raised when references disagree or cannot execute a generated case."""


def _generate_input(slug: str, rng: random.Random) -> str:
    if slug == "two-sum":
        while True:
            nums = rng.sample(range(-50, 51), rng.randint(2, 12))
            sums: dict[int, int] = {}
            for left in range(len(nums)):
                for right in range(left + 1, len(nums)):
                    total = nums[left] + nums[right]
                    sums[total] = sums.get(total, 0) + 1
            unique_targets = [total for total, count in sums.items() if count == 1]
            if unique_targets:
                return f"{json.dumps(nums)}\n{rng.choice(unique_targets)}"
    if slug == "valid-palindrome":
        alphabet = "abcXYZ012 ,.!?"
        return json.dumps("".join(rng.choices(alphabet, k=rng.randint(1, 30))))
    if slug == "binary-search":
        nums = sorted(rng.sample(range(-100, 101), rng.randint(1, 30)))
        return f"{json.dumps(nums)}\n{rng.randint(-110, 110)}"
    if slug == "maximum-subarray":
        nums = [rng.randint(-100, 100) for _ in range(rng.randint(1, 30))]
        return json.dumps(nums)
    if slug == "climbing-stairs":
        return str(rng.randint(1, 20))
    if slug == "reverse-linked-list":
        return json.dumps([rng.randint(-100, 100) for _ in range(rng.randint(0, 30))])
    if slug == "number-of-islands":
        rows = rng.randint(1, 8)
        columns = rng.randint(1, 8)
        grid = [[rng.choice(["0", "1"]) for _ in range(columns)] for _ in range(rows)]
        return json.dumps(grid, separators=(",", ":"))
    if slug == "merge-intervals":
        intervals = []
        for _ in range(rng.randint(1, 20)):
            start = rng.randint(0, 100)
            intervals.append([start, start + rng.randint(0, 20)])
        return json.dumps(intervals, separators=(",", ":"))
    if slug == "daily-temperatures":
        return json.dumps(
            [rng.randint(30, 100) for _ in range(rng.randint(1, 30))],
            separators=(",", ":"),
        )
    if slug == "kth-largest-element-in-array":
        nums = [rng.randint(-100, 100) for _ in range(rng.randint(1, 30))]
        return f"{json.dumps(nums)}\n{rng.randint(1, len(nums))}"
    raise DifferentialTestError(f"No fuzzer configured for problem {slug!r}")


def _run_reference(problem: dict[str, Any], reference_name: str, input_data: str) -> Any:
    slug = problem["slug"]
    runner = PYTHON_RUNNERS[slug]
    source = "\n".join(
        [
            problem["starter_code"]["python"],
            problem[reference_name],
            f"class Solution:\n    def {runner.method}(self, *args):\n        return {reference_name}(*args)",
        ]
    )
    try:
        completed = subprocess.run(
            [sys.executable, "-c", build_python_submission(slug, source)],
            input=input_data,
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
        return json.loads(completed.stdout.strip().splitlines()[-1])
    except (subprocess.SubprocessError, IndexError, json.JSONDecodeError) as error:
        raise DifferentialTestError(
            f"{reference_name} failed for {slug} with input {input_data!r}: {error}"
        ) from error


def _normalize_output(slug: str, output: Any) -> Any:
    if slug == "two-sum" and isinstance(output, list):
        return sorted(output)
    if slug == "merge-intervals" and isinstance(output, list):
        return sorted(output)
    return output


def generate_differential_tests(
    problem: dict[str, Any], case_count: int = 16
) -> list[dict[str, str]]:
    """Fuzz a problem, verify brute/optimal agreement, and return hidden cases."""
    slug = problem["slug"]
    rng = random.Random(f"algomentor-phase0:{slug}")
    generated: list[dict[str, str]] = []

    for _ in range(case_count):
        input_data = _generate_input(slug, rng)
        brute = _run_reference(problem, "brute_force", input_data)
        optimal = _run_reference(problem, "optimal", input_data)
        brute = _normalize_output(slug, brute)
        optimal = _normalize_output(slug, optimal)
        if brute != optimal:
            raise DifferentialTestError(
                f"Reference mismatch for {slug} with input {input_data!r}: "
                f"brute_force={brute!r}, optimal={optimal!r}"
            )
        generated.append(
            {
                "input": input_data,
                "expected": json.dumps(optimal, separators=(",", ":")),
                "source": "fuzz",
            }
        )

    return generated
