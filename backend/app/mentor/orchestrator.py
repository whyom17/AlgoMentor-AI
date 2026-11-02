"""
Hint orchestration layer.

AGENTS.md constraints enforced here:
  #2 — Never pass a full reference solution to LLM context at levels 1-2.
  #3 — All responses at levels 1-2 pass through output_filter.py.
  #4 — No route to hint endpoint from contest/interview mode (enforced at API layer too).
  #7 — All LLM calls go through model_router.py.

Hint levels:
  1 — Clarifying question, informed by failure trace, zero problem-specific logic.
  2 — Pattern nudge: names the technique family.
  3 — Structural hint / pseudocode skeleton.
  4 — Full walkthrough, gated by attempt threshold.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import structlog

from app.mentor.model_router import call_llm, get_tier_for_hint_level
from app.mentor.output_filter import filter_hint_response

logger = structlog.get_logger(__name__)

# Minimum attempts before Level 4 is unlocked (enforce in route layer too)
L4_ATTEMPT_THRESHOLD = 3
# Minimum time spent (seconds) before L4 is unlocked
L4_TIME_THRESHOLD_SECONDS = 600  # 10 minutes


@dataclass
class HintContext:
    problem_slug: str
    problem_description: str
    problem_constraints: str
    pattern_family: str  # e.g. "sliding_window"
    tags: list[str]
    # User's current code
    user_code: str
    language: str
    # Execution result from Judge0
    last_status: str  # "wrong_answer", "runtime_error", etc.
    last_stdout: str
    last_stderr: str
    # Failure trace (variable states at failure point — Phase 1 enrichment)
    execution_trace: dict | None
    # How many previous attempts/hints
    attempt_count: int
    hint_count_already: int
    # Time spent on this problem (seconds)
    time_spent_seconds: int
    # Pro user?
    is_pro: bool
    # L3/L4 daily count (for rate-limiting free tier)
    frontier_hints_today: int


@dataclass
class HintResponse:
    text: str
    hint_level: int
    model_used: str
    tokens_used: int
    latency_ms: int
    was_filtered: bool


def _build_level1_messages(ctx: HintContext) -> list[dict[str, str]]:
    """
    Level 1: Clarifying question only.
    CONSTRAINT: No reference solution, no pattern name in context.
    """
    system = (
        "You are AlgoMentor, a Socratic coding tutor. "
        "Your ONLY job right now is to ask ONE clarifying question that helps the student "
        "re-examine their own assumptions about the problem. "
        "DO NOT: name any algorithm, data structure, or technique. "
        "DO NOT: provide any code or pseudocode. "
        "DO NOT: hint at the correct approach. "
        "Ask a question about the problem constraints, examples, or what the code "
        "currently does versus what it should do."
    )
    user_msg = (
        f"Problem: {ctx.problem_description}\n\n"
        f"Constraints:\n{ctx.problem_constraints}\n\n"
        f"Student's code ({ctx.language}):\n```\n{ctx.user_code}\n```\n\n"
        f"Last run result: {ctx.last_status}\n"
        f"Stdout: {ctx.last_stdout[:300] if ctx.last_stdout else 'none'}\n"
        f"Stderr: {ctx.last_stderr[:200] if ctx.last_stderr else 'none'}\n\n"
        "Ask ONE Socratic clarifying question only."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user_msg}]


def _build_level2_messages(ctx: HintContext) -> list[dict[str, str]]:
    """
    Level 2: Pattern nudge — names the technique family but not the algorithm.
    CONSTRAINT: No reference solution in context.
    """
    system = (
        "You are AlgoMentor, a Socratic coding tutor. "
        "Your job is to nudge the student toward the correct algorithmic pattern family "
        "without giving away the implementation. "
        "You MAY mention the general technique family (e.g., 'two-pointer', 'sliding window') "
        "but must NOT provide pseudocode, code, or step-by-step algorithm. "
        "End with a guiding question."
    )
    user_msg = (
        f"Problem: {ctx.problem_description}\n\n"
        f"Constraints:\n{ctx.problem_constraints}\n\n"
        f"Student's code ({ctx.language}):\n```\n{ctx.user_code[:800]}\n```\n\n"
        f"Last run result: {ctx.last_status}\n"
    )
    if ctx.execution_trace:
        user_msg += f"Execution trace context:\n{str(ctx.execution_trace)[:400]}\n\n"
    user_msg += (
        f"Pattern family hint: {ctx.pattern_family}\n\n"
        "Give a pattern nudge — name the technique family and ask one guiding question. "
        "No pseudocode or code."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user_msg}]


def _build_level3_messages(ctx: HintContext) -> list[dict[str, str]]:
    """
    Level 3: Pseudocode skeleton.
    Full context allowed (including pattern), still no complete solution.
    """
    system = (
        "You are AlgoMentor, a coding mentor providing a structural hint. "
        "Give a pseudocode skeleton that outlines the algorithm approach WITHOUT "
        "giving a complete, runnable solution. Use natural language + partial pseudocode. "
        "Highlight the key invariant the student needs to maintain."
    )
    user_msg = (
        f"Problem: {ctx.problem_description}\n\n"
        f"Constraints:\n{ctx.problem_constraints}\n\n"
        f"Pattern: {ctx.pattern_family} | Tags: {', '.join(ctx.tags)}\n\n"
        f"Student's code ({ctx.language}):\n```\n{ctx.user_code[:1200]}\n```\n\n"
        f"Status: {ctx.last_status} | Attempts: {ctx.attempt_count}\n"
    )
    if ctx.execution_trace:
        user_msg += f"Trace: {str(ctx.execution_trace)[:600]}\n\n"
    user_msg += "Provide a pseudocode skeleton and explain the key invariant."
    return [{"role": "system", "content": system}, {"role": "user", "content": user_msg}]


def _build_level4_messages(ctx: HintContext) -> list[dict[str, str]]:
    """
    Level 4: Full walkthrough.
    Frontier model, complete context, detailed explanation.
    Logged as 'assisted' — this fact is stored in HintEvent.
    """
    system = (
        "You are AlgoMentor, providing a full walkthrough for a student who has "
        "genuinely struggled (multiple attempts, significant time). "
        "Walk through the complete algorithm, explain every step, and after the "
        "walkthrough ask the student to explain it back in their own words. "
        "You may include a complete, working code example."
    )
    user_msg = (
        f"Problem: {ctx.problem_description}\n\n"
        f"Constraints:\n{ctx.problem_constraints}\n\n"
        f"Pattern: {ctx.pattern_family} | Tags: {', '.join(ctx.tags)}\n\n"
        f"Student's code ({ctx.language}):\n```\n{ctx.user_code}\n```\n\n"
        f"Status: {ctx.last_status} | Attempts: {ctx.attempt_count} | "
        f"Time spent: {ctx.time_spent_seconds // 60} minutes\n"
    )
    if ctx.execution_trace:
        user_msg += f"Execution trace:\n{str(ctx.execution_trace)[:800]}\n\n"
    user_msg += (
        "Provide the full walkthrough with a working solution. "
        "End with: 'Now explain back to me what this solution does and why it works.'"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user_msg}]


def _level1_template(ctx: HintContext) -> str:
    if ctx.last_status == "wrong_answer":
        return "What is the smallest input where your output differs from the expected result, and which assumption does that example challenge?"
    if ctx.last_status in ("runtime_error", "compile_error"):
        return "Which line does the error point to, and what value or type does that line receive?"
    return "Can you trace one example by hand and compare what each step of your code does with what the problem asks for?"


_MESSAGE_BUILDERS = {
    1: _build_level1_messages,
    2: _build_level2_messages,
    3: _build_level3_messages,
    4: _build_level4_messages,
}


async def get_hint(ctx: HintContext, requested_level: int) -> HintResponse:
    """
    Orchestrate a hint response for the given level.

    This function enforces all AGENTS.md constraints on hint gating.
    """
    # Clamp level to [1, 4]
    level = max(1, min(4, requested_level))

    # Gate Level 4 behind attempt/time threshold
    if level == 4:
        if (
            ctx.attempt_count < L4_ATTEMPT_THRESHOLD
            and ctx.time_spent_seconds < L4_TIME_THRESHOLD_SECONDS
        ):
            logger.info(
                "hint_orchestrator.l4_gated",
                attempt_count=ctx.attempt_count,
                time_spent=ctx.time_spent_seconds,
            )
            level = 3  # Downgrade to L3 silently

    # Rate-limit frontier hints for free users
    if level >= 3 and not ctx.is_pro:
        FREE_TIER_FRONTIER_DAILY_LIMIT = 3
        if ctx.frontier_hints_today >= FREE_TIER_FRONTIER_DAILY_LIMIT:
            return HintResponse(
                text=(
                    "You've reached your daily limit for deep hints on the free tier. "
                    "Upgrade to Pro for unlimited hints, or try solving with Level 1-2 hints."
                ),
                hint_level=level,
                model_used="rate_limited",
                tokens_used=0,
                latency_ms=0,
                was_filtered=False,
            )

    # Build messages (CONSTRAINT #2: reference solution NEVER in context at L1/L2)
    builder = _MESSAGE_BUILDERS.get(level, _build_level1_messages)
    messages = builder(ctx)

    t0 = time.monotonic()
    if level == 1:
        raw_text = _level1_template(ctx)
        model_used = "template"
        tokens = 0
    else:
        tier = get_tier_for_hint_level(level)
        raw_text, model_used, tokens = await call_llm(messages, tier, hint_level=level)

    latency_ms = int((time.monotonic() - t0) * 1000)

    # CONSTRAINT #3: Output filter for levels 1-2
    filtered_text, was_filtered = filter_hint_response(raw_text, hint_level=level)

    logger.info(
        "hint_orchestrator.served",
        level=level,
        model=model_used,
        tokens=tokens,
        latency_ms=latency_ms,
        was_filtered=was_filtered,
    )

    return HintResponse(
        text=filtered_text,
        hint_level=level,
        model_used=model_used,
        tokens_used=tokens,
        latency_ms=latency_ms,
        was_filtered=was_filtered,
    )
