"""Build trusted Python drivers for the curated problem bank."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PythonRunner:
    method: str
    argument_setup: str
    result_setup: str = "_result = _solution.{method}(*_args)"


PYTHON_RUNNERS: dict[str, PythonRunner] = {
    "two-sum": PythonRunner(
        "twoSum",
        "_lines = _raw.splitlines()\n_args = [json.loads(_lines[0]), int(_lines[1])]",
    ),
    "valid-palindrome": PythonRunner("isPalindrome", "_args = [json.loads(_raw)]"),
    "binary-search": PythonRunner(
        "search",
        "_lines = _raw.splitlines()\n_args = [json.loads(_lines[0]), int(_lines[1])]",
    ),
    "maximum-subarray": PythonRunner("maxSubArray", "_args = [json.loads(_raw)]"),
    "climbing-stairs": PythonRunner("climbStairs", "_args = [int(_raw)]"),
    "reverse-linked-list": PythonRunner(
        "reverseList",
        """_values = json.loads(_raw)
_head = None
for _value in reversed(_values):
    _head = ListNode(_value, _head)
_args = [_head]""",
        """_result = _solution.{method}(*_args)
_values = []
while _result is not None:
    _values.append(_result.val)
    _result = _result.next
_result = _values""",
    ),
    "number-of-islands": PythonRunner("numIslands", "_args = [json.loads(_raw)]"),
    "merge-intervals": PythonRunner("merge", "_args = [json.loads(_raw)]"),
    "daily-temperatures": PythonRunner("dailyTemperatures", "_args = [json.loads(_raw)]"),
    "kth-largest-element-in-array": PythonRunner(
        "findKthLargest",
        "_lines = _raw.splitlines()\n_args = [json.loads(_lines[0]), int(_lines[1])]",
    ),
}


def build_python_submission(slug: str, source_code: str) -> str:
    """Append a driver that invokes the problem's Solution method once."""
    runner = PYTHON_RUNNERS.get(slug)
    if runner is None:
        raise ValueError(f"No Python runner configured for problem {slug!r}")

    result_setup = runner.result_setup.format(method=runner.method)
    return f"""{source_code}

import contextlib as _contextlib
import io as _io
import json as _json
import sys as _sys

_raw = _sys.stdin.read()
_args = []
{runner.argument_setup.replace("json.", "_json.")}
_solution = Solution()
_captured = _io.StringIO()
with _contextlib.redirect_stdout(_captured):
    {result_setup.replace("json.", "_json.")}
print(_json.dumps(_result, separators=(",", ":")))
"""
