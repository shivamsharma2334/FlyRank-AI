"""Reliability engineering: retry, repair, quarantine, timeout, error classification.
The LLM call is mocked at _call_gemini_once — no network, no API key needed.
"""
import asyncio
from unittest.mock import AsyncMock

from app.core.exceptions import LLMProviderError, LLMTimeoutError, LLMValidationError
from app.services import gemini_service

# Named to match what _classify_error looks for, so retry logic is testable without
# importing the real Google SDK exception classes.
ResourceExhausted = type("ResourceExhausted", (Exception,), {})
Unauthenticated = type("Unauthenticated", (Exception,), {})

VALID_JSON = '{"risk_level": "low", "category": "other", "requires_review": false, "confidence": 0.6, "reason": "ok"}'


async def test_repair_success(monkeypatch):
    mock = AsyncMock(side_effect=[
        ('{"risk": "not-a-schema-field"}', {"input_tokens": 10, "output_tokens": 5}),
        (VALID_JSON, {"input_tokens": 15, "output_tokens": 8}),
    ])
    monkeypatch.setattr(gemini_service, "_call_gemini_once", mock)

    result = await gemini_service.judge("some request", "some context")

    assert result.category.value == "other"
    assert mock.call_count == 2


async def test_repair_failure_quarantines(monkeypatch):
    mock = AsyncMock(return_value=('{"bad": "shape"}', {"input_tokens": 1, "output_tokens": 1}))
    monkeypatch.setattr(gemini_service, "_call_gemini_once", mock)

    try:
        await gemini_service.judge("some request", "some context")
        assert False, "expected LLMValidationError"
    except LLMValidationError:
        pass

    assert mock.call_count == 2  # original attempt + exactly one repair


async def test_invalid_model_schema_triggers_repair_path(monkeypatch):
    # Syntactically valid JSON, but violates the closed-enum schema.
    mock = AsyncMock(side_effect=[
        ('{"risk_level": "critical", "category": "other", "requires_review": false, "confidence": 0.5, "reason": "x"}',
         {"input_tokens": 1, "output_tokens": 1}),
        (VALID_JSON, {"input_tokens": 1, "output_tokens": 1}),
    ])
    monkeypatch.setattr(gemini_service, "_call_gemini_once", mock)

    result = await gemini_service.judge("some request", "some context")

    assert result.risk_level.value == "low"
    assert mock.call_count == 2


async def test_429_is_retried(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    mock = AsyncMock(side_effect=[ResourceExhausted("rate limited"), (VALID_JSON, {"input_tokens": 1, "output_tokens": 1})])
    monkeypatch.setattr(gemini_service, "_call_gemini_once", mock)
    monkeypatch.setattr(gemini_service.settings, "llm_max_retries", 2)

    result = await gemini_service.judge("some request", "some context")

    assert result is not None
    assert mock.call_count == 2


async def test_401_is_not_retried(monkeypatch):
    mock = AsyncMock(side_effect=Unauthenticated("bad api key"))
    monkeypatch.setattr(gemini_service, "_call_gemini_once", mock)

    try:
        await gemini_service.judge("some request", "some context")
        assert False, "expected LLMProviderError"
    except LLMProviderError:
        pass

    assert mock.call_count == 1  # never retried


async def test_timeout_stops_after_retry_limit(monkeypatch):
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    mock = AsyncMock(side_effect=asyncio.TimeoutError())
    monkeypatch.setattr(gemini_service, "_call_gemini_once", mock)
    monkeypatch.setattr(gemini_service.settings, "llm_max_retries", 1)

    try:
        await gemini_service.judge("some request", "some context")
        assert False, "expected LLMTimeoutError"
    except LLMTimeoutError:
        pass

    assert mock.call_count == 2  # initial + 1 retry, then stop


async def test_client_error_code_429_is_retried_new_sdk_shape(monkeypatch):
    # google-genai's ClientError carries an int `.code`, not a special class name.
    ClientError = type("ClientError", (Exception,), {})
    err = ClientError("rate limited")
    err.code = 429
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    mock = AsyncMock(side_effect=[err, (VALID_JSON, {"input_tokens": 1, "output_tokens": 1})])
    monkeypatch.setattr(gemini_service, "_call_gemini_once", mock)
    monkeypatch.setattr(gemini_service.settings, "llm_max_retries", 2)

    result = await gemini_service.judge("some request", "some context")

    assert result is not None
    assert mock.call_count == 2


async def test_extract_json_strips_surrounding_code_fence():
    fenced = '```json\n{"risk_level": "low", "category": "other", "requires_review": false, "confidence": 0.6, "reason": "ok"}\n```'
    data = gemini_service._extract_json(fenced)
    assert data["risk_level"] == "low"
