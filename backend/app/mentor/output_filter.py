"""
Output filter for hint responses.

AGENTS.md constraint #3: ALL hint responses at levels 1-2 MUST pass through
this filter before being returned to the client. No code path bypasses this.

The filter scans for solution-adjacent content (complete algorithms, fully
working code blocks, direct answers) and redacts or refuses them.
"""

from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# Patterns that suggest a complete solution is being leaked
_SOLUTION_PATTERNS: list[re.Pattern[str]] = [
    # Multi-line code blocks with substantial content
    re.compile(r"```[\w]*\n(?:(?!```).){200,}```", re.DOTALL),
    # Direct "the answer is" phrasing
    re.compile(
        r"\b(the (?:answer|solution|correct solution|full solution) is[:\s])",
        re.IGNORECASE,
    ),
    # Returning a complete function / class definition
    re.compile(
        r"(def\s+\w+\([^)]*\)[\s\S]{100,}return|"
        r"class\s+\w+[\s\S]{150,}def\s+\w+)",
        re.DOTALL,
    ),
    # Time complexity reveal that also names the exact algorithm
    re.compile(
        r"use\s+(?:a\s+)?(?:two[\s-]pointer|sliding\s+window|monotonic\s+stack|"
        r"union[\s-]find|topological\s+sort|dijkstra|bellman[\s-]ford|"
        r"floyd[\s-]warshall)\s+algorithm",
        re.IGNORECASE,
    ),
]

# Shorter code blocks that are acceptable in low-level hints
_SHORT_CODE_OK = re.compile(r"```[\w]*\n(?:(?!```).){1,150}```", re.DOTALL)

_REDACTION_NOTICE = (
    "[Hint filtered: the response contained content that is only appropriate "
    "at a higher hint level. Please try a more specific approach hint request "
    "or unlock Level 3 for deeper guidance.]"
)


def filter_hint_response(text: str, hint_level: int) -> tuple[str, bool]:
    """
    Filter a raw LLM hint response.

    Args:
        text: Raw LLM output text.
        hint_level: The hint level this response is for (1-4).

    Returns:
        (filtered_text, was_modified) tuple.
        filtered_text: Safe text to return to the user.
        was_modified: True if the filter changed anything.
    """
    if hint_level >= 3:
        # Levels 3-4 are allowed to contain pseudocode and walkthroughs
        return text, False

    # For levels 1-2: check for solution-adjacent content
    triggered: list[str] = []
    for pattern in _SOLUTION_PATTERNS:
        if pattern.search(text):
            # Check if it's just a short code snippet (acceptable)
            if _SHORT_CODE_OK.search(text) and not pattern.search(
                re.sub(_SHORT_CODE_OK.pattern, "", text, flags=re.DOTALL)
            ):
                continue
            triggered.append(pattern.pattern[:40])

    if triggered:
        logger.warning(
            "output_filter.triggered",
            hint_level=hint_level,
            patterns=triggered,
            text_preview=text[:120],
        )
        return _REDACTION_NOTICE, True

    return text, False
