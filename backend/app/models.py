"""
SQLAlchemy ORM models for AlgoMentor AI – Phase 0.

Tables:
  users, problems, test_cases, attempts, hint_events, mastery_scores
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ─── Enums ─────────────────────────────────────────────────────────────────


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SubmissionStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    MEMORY_LIMIT_EXCEEDED = "memory_limit_exceeded"
    RUNTIME_ERROR = "runtime_error"
    COMPILE_ERROR = "compile_error"
    INTERNAL_ERROR = "internal_error"


class HintLevel(int, enum.Enum):
    L1_CLARIFYING = 1
    L2_PATTERN_NUDGE = 2
    L3_PSEUDOCODE = 3
    L4_WALKTHROUGH = 4


class MistakeType(str, enum.Enum):
    OFF_BY_ONE = "off_by_one"
    WRONG_PATTERN = "wrong_pattern"
    WRONG_COMPLEXITY = "wrong_complexity"
    EDGE_CASE = "edge_case"
    SYNTAX = "syntax"
    UNKNOWN = "unknown"


# ─── Models ─────────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clerk_id: Mapped[str | None] = mapped_column(String(256), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_pro: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    attempts: Mapped[list["Attempt"]] = relationship(back_populates="user")
    mastery_scores: Mapped[list["MasteryScore"]] = relationship(back_populates="user")
    hint_events: Mapped[list["HintEvent"]] = relationship(back_populates="user")


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty), nullable=False, default=Difficulty.MEDIUM
    )
    # e.g. ["arrays", "two_pointers", "sliding_window"]
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    # Pattern family for isomorphic variant grouping
    pattern_family: Mapped[str] = mapped_column(String(128), nullable=False)
    # Starter code per language: {"python": "def ...", "java": "class ..."}
    starter_code: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Constraints text shown to the user
    constraints: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Examples shown publicly
    examples: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    # Hidden test cases count (actual cases stored in test_cases table)
    hidden_test_count: Mapped[int] = mapped_column(Integer, default=0)
    # Time / memory limits
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=256)
    # ELO-style calibration used in Phase 1 to estimate difficulty from real outcomes.
    difficulty_rating: Mapped[float] = mapped_column(Float, default=1200.0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="problem")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="problem")


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=True)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)
    # Source: "manual" | "brute_vs_optimal" | "fuzz"
    source: Mapped[str] = mapped_column(String(32), default="manual")
    order: Mapped[int] = mapped_column(Integer, default=0)

    problem: Mapped["Problem"] = relationship(back_populates="test_cases")


class Attempt(Base):
    """One run / submission by a user on a problem."""

    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus), default=SubmissionStatus.PENDING
    )
    # Judge0 token for async polling
    judge0_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Execution result details (stdout, stderr, time, memory)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Execution trace if captured
    execution_trace: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Mistake classification (populated post-submission if WA)
    mistake_type: Mapped[MistakeType | None] = mapped_column(
        Enum(MistakeType), nullable=True
    )
    # Total hints used in this attempt
    hint_count: Mapped[int] = mapped_column(Integer, default=0)
    # max hint level reached
    max_hint_level: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="attempts")
    problem: Mapped["Problem"] = relationship(back_populates="attempts")
    hint_events: Mapped[list["HintEvent"]] = relationship(back_populates="attempt")


class HintEvent(Base):
    """One hint request/response within an attempt."""

    __tablename__ = "hint_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False
    )
    hint_level: Mapped[HintLevel] = mapped_column(Enum(HintLevel), nullable=False)
    # Snapshot of code at time of request
    code_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Execution trace context passed to the LLM
    trace_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Raw LLM response (after output filter)
    response_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Which model served this hint
    model_used: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="hint_events")
    attempt: Mapped["Attempt"] = relationship(back_populates="hint_events")


class MasteryScore(Base):
    """Per-user, per-topic mastery score with decay."""

    __tablename__ = "mastery_scores"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_tag", name="uq_user_topic"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    topic_tag: Mapped[str] = mapped_column(String(128), nullable=False)
    # Raw mastery score [0, 1]
    score: Mapped[float] = mapped_column(Float, default=0.0)
    # Number of attempts contributing to the score
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    # Number of successful (accepted) solves
    solve_count: Mapped[int] = mapped_column(Integer, default=0)
    # Whether the user solved with heavy hint use (seen, not owned)
    hint_assisted_count: Mapped[int] = mapped_column(Integer, default=0)
    # SM-2 interval (days) for next scheduled review
    sm2_interval: Mapped[float] = mapped_column(Float, default=1.0)
    # SM-2 ease factor
    sm2_ef: Mapped[float] = mapped_column(Float, default=2.5)
    # When was the score last decayed
    last_practiced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_review_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="mastery_scores")
