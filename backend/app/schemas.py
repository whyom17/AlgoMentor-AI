"""
Pydantic schemas for all API request/response bodies.
Kept separate from SQLAlchemy models for clean separation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

# ─── Auth ─────────────────────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    is_pro: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Problems ─────────────────────────────────────────────────────────────────


class ProblemListItem(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    difficulty: str
    difficulty_rating: float = 1200.0
    tags: list[str]
    pattern_family: str

    model_config = {"from_attributes": True}


class ProblemDetail(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    description: str
    difficulty: str
    difficulty_rating: float = 1200.0
    tags: list[str]
    pattern_family: str
    starter_code: dict[str, str]
    constraints: str
    examples: list[dict[str, Any]]
    time_limit_ms: int
    memory_limit_mb: int

    model_config = {"from_attributes": True}


# ─── Submissions ──────────────────────────────────────────────────────────────


class SubmitCodeRequest(BaseModel):
    problem_slug: str
    language: str
    source_code: str


class SubmitCodeResponse(BaseModel):
    attempt_id: uuid.UUID
    judge0_token: str = ""
    status: str


class AttemptResultResponse(BaseModel):
    attempt_id: uuid.UUID
    status: str
    stdout: str
    stderr: str
    compile_output: str
    time_ms: float | None
    memory_kb: int | None
    execution_trace: dict[str, Any] | None = None
    # Per-test-case results (if available)
    test_results: list[dict[str, Any]] = Field(default_factory=list)


# ─── Hints ────────────────────────────────────────────────────────────────────


class HintRequest(BaseModel):
    attempt_id: uuid.UUID
    hint_level: int = Field(ge=1, le=4)


class HintResponse(BaseModel):
    hint_level: int
    text: str
    model_used: str
    was_filtered: bool
    latency_ms: int


# ─── Mastery ──────────────────────────────────────────────────────────────────


class TopicMastery(BaseModel):
    topic_tag: str
    score: float
    label: str
    attempt_count: int
    solve_count: int
    next_review_at: datetime | None


class MasteryDashboard(BaseModel):
    user_id: uuid.UUID
    total_solved: int
    total_attempts: int
    topics: list[TopicMastery]


# ─── Recommendations ──────────────────────────────────────────────────────────


class RecommendedProblem(BaseModel):
    slug: str
    title: str
    difficulty: str
    reason: str  # e.g. "Due for review: sliding_window"
    pattern_family: str
