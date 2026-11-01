"""Tests for the sandbox adapter (Judge0) — mocked HTTP."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.sandbox_adapter.judge0 import (
    ExecutionRequest,
    ExecutionResult,
    Judge0Client,
)


class TestLanguageResolution:
    def test_python_resolves(self) -> None:
        client = Judge0Client()
        assert client._resolve_language_id("python") == 71
        assert client._resolve_language_id("python3") == 71

    def test_java_resolves(self) -> None:
        client = Judge0Client()
        assert client._resolve_language_id("java") == 62

    def test_cpp_resolves(self) -> None:
        client = Judge0Client()
        assert client._resolve_language_id("cpp") == 54
        assert client._resolve_language_id("c++") == 54

    def test_unsupported_language_raises(self) -> None:
        client = Judge0Client()
        with pytest.raises(ValueError, match="Unsupported language"):
            client._resolve_language_id("brainfuck")


class TestExecutionResult:
    def test_terminal_status(self) -> None:
        result = ExecutionResult(status="accepted")
        assert result.is_terminal is True
        assert result.accepted is True

    def test_pending_not_terminal(self) -> None:
        result = ExecutionResult(status="pending")
        assert result.is_terminal is False
        assert result.accepted is False

    def test_wrong_answer_terminal(self) -> None:
        result = ExecutionResult(status="wrong_answer")
        assert result.is_terminal is True
        assert result.accepted is False


class TestJudge0Submit:
    @pytest.mark.asyncio
    async def test_submit_returns_token(self) -> None:
        client = Judge0Client()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"token": "abc123"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.closed = False

        client._session = mock_session

        req = ExecutionRequest(
            source_code="print('hello')",
            language="python",
            stdin="",
        )
        result = await client.submit(req)
        assert result.token == "abc123"
        assert result.status == "pending"
