"""
Sandbox Adapter — Judge0 implementation.

All code execution MUST go through this module (AGENTS.md constraint #1).
Never call the execution provider directly from route handlers or other services.

Public interface:
  - submit_code(request: ExecutionRequest) -> ExecutionResult
  - get_result(token: str) -> ExecutionResult
  - list_languages() -> list[Language]
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import IntEnum

import aiohttp
import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


# ─── Judge0 language IDs (subset for Phase 0) ────────────────────────────────


class Judge0Language(IntEnum):
    PYTHON3 = 71
    JAVA = 62
    CPP17 = 54
    JAVASCRIPT = 63
    C = 50
    GO = 60
    RUST = 73


LANGUAGE_ID_MAP: dict[str, int] = {
    "python": Judge0Language.PYTHON3,
    "python3": Judge0Language.PYTHON3,
    "java": Judge0Language.JAVA,
    "cpp": Judge0Language.CPP17,
    "c++": Judge0Language.CPP17,
    "javascript": Judge0Language.JAVASCRIPT,
    "js": Judge0Language.JAVASCRIPT,
    "c": Judge0Language.C,
    "go": Judge0Language.GO,
    "golang": Judge0Language.GO,
    "rust": Judge0Language.RUST,
}


class Judge0Status(IntEnum):
    IN_QUEUE = 1
    PROCESSING = 2
    ACCEPTED = 3
    WRONG_ANSWER = 4
    TIME_LIMIT_EXCEEDED = 5
    COMPILATION_ERROR = 6
    RUNTIME_ERROR_SIGSEGV = 7
    RUNTIME_ERROR_SIGXFSZ = 8
    RUNTIME_ERROR_SIGFPE = 9
    RUNTIME_ERROR_SIGABRT = 10
    RUNTIME_ERROR_NZEC = 11
    RUNTIME_ERROR_OTHER = 12
    INTERNAL_ERROR = 13
    EXEC_FORMAT_ERROR = 14


JUDGE0_STATUS_TO_SUBMISSION_STATUS: dict[int, str] = {
    Judge0Status.IN_QUEUE: "pending",
    Judge0Status.PROCESSING: "running",
    Judge0Status.ACCEPTED: "accepted",
    Judge0Status.WRONG_ANSWER: "wrong_answer",
    Judge0Status.TIME_LIMIT_EXCEEDED: "time_limit_exceeded",
    Judge0Status.COMPILATION_ERROR: "compile_error",
    Judge0Status.RUNTIME_ERROR_SIGSEGV: "runtime_error",
    Judge0Status.RUNTIME_ERROR_SIGXFSZ: "runtime_error",
    Judge0Status.RUNTIME_ERROR_SIGFPE: "runtime_error",
    Judge0Status.RUNTIME_ERROR_SIGABRT: "runtime_error",
    Judge0Status.RUNTIME_ERROR_NZEC: "runtime_error",
    Judge0Status.RUNTIME_ERROR_OTHER: "runtime_error",
    Judge0Status.INTERNAL_ERROR: "internal_error",
    Judge0Status.EXEC_FORMAT_ERROR: "internal_error",
}


# ─── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class ExecutionRequest:
    source_code: str
    language: str  # human-readable, e.g. "python3"
    stdin: str = ""
    expected_output: str = ""
    time_limit_ms: int = 2000
    memory_limit_mb: int = 256
    # If True, Judge0 runs and returns immediately (async polling)
    wait: bool = False


@dataclass
class ExecutionResult:
    token: str = ""
    status: str = "pending"
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    time_ms: float | None = None
    memory_kb: int | None = None
    exit_code: int | None = None
    # Raw Judge0 response for debugging
    raw: dict = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status not in ("pending", "running")

    @property
    def accepted(self) -> bool:
        return self.status == "accepted"


@dataclass
class Language:
    id: int
    name: str
    key: str


# ─── Judge0 client ────────────────────────────────────────────────────────────


class Judge0Client:
    """
    Thin async HTTP client wrapping the Judge0 REST API.
    Do NOT import this directly — use the module-level functions below.
    """

    def __init__(self) -> None:
        self._base_url = settings.judge0_url.rstrip("/")
        self._auth_token = settings.judge0_auth_token
        self._session: aiohttp.ClientSession | None = None

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._auth_token:
            h["X-Auth-Token"] = self._auth_token
        return h

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self._headers())
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    def _resolve_language_id(self, language: str) -> int:
        lang_id = LANGUAGE_ID_MAP.get(language.lower())
        if lang_id is None:
            raise ValueError(f"Unsupported language: {language!r}")
        return lang_id

    async def submit(self, req: ExecutionRequest) -> ExecutionResult:
        """Submit code to Judge0. Returns immediately with token (async mode)."""
        import base64

        lang_id = self._resolve_language_id(req.language)
        payload = {
            "language_id": lang_id,
            "source_code": base64.b64encode(req.source_code.encode()).decode(),
            "stdin": base64.b64encode(req.stdin.encode()).decode() if req.stdin else "",
            "expected_output": (
                base64.b64encode(req.expected_output.encode()).decode()
                if req.expected_output
                else ""
            ),
            "cpu_time_limit": req.time_limit_ms / 1000,
            "memory_limit": req.memory_limit_mb * 1024,
            "enable_per_process_and_thread_time_limit": False,
            "encode_output": True,
        }

        session = await self._get_session()
        url = f"{self._base_url}/submissions?base64_encoded=true&wait=false"

        async with session.post(url, json=payload) as resp:
            resp.raise_for_status()
            data = await resp.json()
            token = data.get("token", "")
            logger.info("judge0.submitted", token=token, language=req.language)
            return ExecutionResult(token=token, status="pending", raw=data)

    async def get_result(self, token: str) -> ExecutionResult:
        """Poll Judge0 for a submission result."""
        import base64

        session = await self._get_session()
        url = f"{self._base_url}/submissions/{token}?base64_encoded=true"

        async with session.get(url) as resp:
            resp.raise_for_status()
            data = await resp.json()

        status_id = data.get("status", {}).get("id", 13)
        status = JUDGE0_STATUS_TO_SUBMISSION_STATUS.get(status_id, "internal_error")

        def _decode(val: str | None) -> str:
            if not val:
                return ""
            try:
                return base64.b64decode(val).decode("utf-8", errors="replace")
            except Exception:
                return val

        time_str = data.get("time")
        time_ms = float(time_str) * 1000 if time_str else None

        return ExecutionResult(
            token=token,
            status=status,
            stdout=_decode(data.get("stdout")),
            stderr=_decode(data.get("stderr")),
            compile_output=_decode(data.get("compile_output")),
            time_ms=time_ms,
            memory_kb=data.get("memory"),
            exit_code=data.get("exit_code"),
            raw=data,
        )

    async def wait_for_result(
        self,
        token: str,
        poll_interval_ms: int = 300,
        max_wait_ms: int = 15000,
    ) -> ExecutionResult:
        """Poll until terminal status or timeout."""
        elapsed = 0
        while elapsed < max_wait_ms:
            result = await self.get_result(token)
            if result.is_terminal:
                return result
            await asyncio.sleep(poll_interval_ms / 1000)
            elapsed += poll_interval_ms

        logger.warning("judge0.timeout", token=token)
        return ExecutionResult(token=token, status="internal_error")

    async def list_languages(self) -> list[Language]:
        session = await self._get_session()
        async with session.get(f"{self._base_url}/languages") as resp:
            resp.raise_for_status()
            data = await resp.json()
        return [Language(id=l["id"], name=l["name"], key="") for l in data]


# ─── Module-level singleton + public interface ────────────────────────────────

_client = Judge0Client()


async def submit_code(request: ExecutionRequest) -> ExecutionResult:
    """Submit code for execution. Returns a token for polling."""
    return await _client.submit(request)


async def get_result(token: str) -> ExecutionResult:
    """Get the current execution result for a token."""
    return await _client.get_result(token)


async def wait_for_result(token: str, max_wait_ms: int = 15000) -> ExecutionResult:
    """Block (async) until the execution completes or times out."""
    return await _client.wait_for_result(token, max_wait_ms=max_wait_ms)


async def list_languages() -> list[Language]:
    return await _client.list_languages()


async def close() -> None:
    await _client.close()
