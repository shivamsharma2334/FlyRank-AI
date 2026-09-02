class LLMDisabledError(Exception):
    """LLM_ENABLED=false. Maps to HTTP 503."""


class LLMTimeoutError(Exception):
    """Gemini didn't respond within timeout after retries. Maps to HTTP 504."""


class LLMValidationError(Exception):
    """Output still invalid after one repair attempt. Maps to HTTP 422."""


class LLMProviderError(Exception):
    """Non-recoverable provider failure (auth/4xx, or exhausted 5xx retries). Maps to HTTP 502."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code
