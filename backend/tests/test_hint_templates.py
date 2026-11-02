from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.mentor.orchestrator import HintContext, get_hint


def make_context(status: str) -> HintContext:
    return HintContext(
        problem_slug="two-sum",
        problem_description="Return the matching pair.",
        problem_constraints="Small input.",
        pattern_family="secret_pattern",
        tags=["secret_tag"],
        user_code="class Solution: pass",
        language="python",
        last_status=status,
        last_stdout="",
        last_stderr="",
        execution_trace=None,
        attempt_count=1,
        hint_count_already=0,
        time_spent_seconds=0,
        is_pro=False,
        frontier_hints_today=0,
    )


@pytest.mark.asyncio
async def test_level_one_uses_filtered_template_without_calling_provider() -> None:
    with patch("app.mentor.orchestrator.call_llm", new_callable=AsyncMock) as call_llm:
        response = await get_hint(make_context("wrong_answer"), 1)

    call_llm.assert_not_awaited()
    assert response.model_used == "template"
    assert response.tokens_used == 0
    assert "smallest input" in response.text
    assert "secret_pattern" not in response.text
