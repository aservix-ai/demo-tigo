"""ChatNVIDIA with exponential-backoff retries on transient upstream errors.

NVIDIA's hosted endpoints answer 503 with
``ResourceExhausted: Worker local total request limit reached (N/N)`` when the
shared worker pool for a model is saturated, and 429 on rate limits. The stock
``langchain_nvidia_ai_endpoints`` client (v1.4.3) has no retry — ``_try_raise``
re-raises immediately — so a single transient blip aborts the whole report
mid-run. That is unacceptable in front of a customer.

We retry the individual LLM call (not the whole agent run) so any tool progress
already made in the agent loop is preserved. Streaming calls only retry *before*
the first token is emitted: the saturation 503 happens at admission, and once
tokens start flowing they can't be un-yielded.
"""

import asyncio
import random
import time
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_nvidia_ai_endpoints import ChatNVIDIA

# Retryable-condition fingerprints found in the exception text NVIDIA raises.
# Detection is by message content because the client raises a bare Exception
# whose str() is the formatted upstream error (e.g. it contains
# "ResourceExhausted: Worker local total request limit reached (32/32)").
_TRANSIENT_MARKERS = (
    "resourceexhausted",
    "worker local total request",
    "too many requests",
    "rate limit",
    "service unavailable",
    "temporarily unavailable",
    "bad gateway",
    "gateway timeout",
    "timed out",
    "timeout",
    "connection reset",
    "connection aborted",
    "connection error",
    "remotedisconnected",
)
# HTTP statuses that are safe to retry, matched against the several shapes the
# status appears in NVIDIA's error string ("[503] ...", "'code': 503", etc.).
_TRANSIENT_STATUS = ("429", "500", "502", "503", "504")

_MAX_RETRIES = 4  # up to 5 attempts total
_BASE_DELAY = 1.0  # seconds; grows 1 -> 2 -> 4 -> 8 (capped), with jitter
_MAX_DELAY = 8.0


def _is_transient(exc: BaseException) -> bool:
    msg = str(exc).lower()
    if any(marker in msg for marker in _TRANSIENT_MARKERS):
        return True
    return any(
        f"[{code}]" in msg or f"'code': {code}" in msg or f'"code": {code}' in msg
        for code in _TRANSIENT_STATUS
    )


def friendly_error(exc: BaseException) -> str:
    """User-facing message for an exception that survived all retries.

    Transient upstream saturation gets a clean Spanish message (the demo runs in
    front of a customer); anything else falls back to the raw text so real bugs
    stay debuggable.
    """
    if _is_transient(exc):
        return (
            "El modelo de NVIDIA está temporalmente saturado o no disponible "
            "(límite de solicitudes concurrentes). Reintenta en unos segundos."
        )
    return str(exc)


def _backoff_delay(attempt: int) -> float:
    """Exponential backoff (attempt is 0-indexed) with 50-100% jitter."""
    delay = min(_MAX_DELAY, _BASE_DELAY * (2**attempt))
    return delay * (0.5 + random.random() * 0.5)


def _log_retry(attempt: int, delay: float, exc: BaseException) -> None:
    print(
        f"[retry] NVIDIA transient error (attempt {attempt + 1}/{_MAX_RETRIES + 1}), "
        f"backing off {delay:.1f}s: {str(exc).splitlines()[0][:160]}",
        flush=True,
    )


class RetryingChatNVIDIA(ChatNVIDIA):
    """ChatNVIDIA that retries transient 429/5xx upstream errors with backoff."""

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return super()._generate(messages, stop, run_manager, **kwargs)
            except Exception as exc:
                if attempt >= _MAX_RETRIES or not _is_transient(exc):
                    raise
                delay = _backoff_delay(attempt)
                _log_retry(attempt, delay, exc)
                time.sleep(delay)
        raise RuntimeError("unreachable")  # pragma: no cover

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return await super()._agenerate(messages, stop, run_manager, **kwargs)
            except Exception as exc:
                if attempt >= _MAX_RETRIES or not _is_transient(exc):
                    raise
                delay = _backoff_delay(attempt)
                _log_retry(attempt, delay, exc)
                await asyncio.sleep(delay)
        raise RuntimeError("unreachable")  # pragma: no cover

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: Sequence[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        # Retry only until the first chunk arrives; the saturation 503 fires at
        # connection admission, so a fresh stream is a clean retry. Once a token
        # has been yielded downstream we must not restart.
        for attempt in range(_MAX_RETRIES + 1):
            stream = super()._stream(messages, stop, run_manager, **kwargs)
            try:
                first = next(stream)
            except StopIteration:
                return
            except Exception as exc:
                if attempt >= _MAX_RETRIES or not _is_transient(exc):
                    raise
                delay = _backoff_delay(attempt)
                _log_retry(attempt, delay, exc)
                time.sleep(delay)
                continue
            yield first
            yield from stream
            return

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: Sequence[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        for attempt in range(_MAX_RETRIES + 1):
            stream = super()._astream(messages, stop, run_manager, **kwargs)
            try:
                first = await stream.__anext__()
            except StopAsyncIteration:
                return
            except Exception as exc:
                if attempt >= _MAX_RETRIES or not _is_transient(exc):
                    raise
                delay = _backoff_delay(attempt)
                _log_retry(attempt, delay, exc)
                await asyncio.sleep(delay)
                continue
            yield first
            async for chunk in stream:
                yield chunk
            return
