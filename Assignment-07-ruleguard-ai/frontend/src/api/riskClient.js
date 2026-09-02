export const MAX_REQUEST_LENGTH = 2000

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const JUDGE_ENDPOINT = `${API_BASE_URL}/api/v1/risk/judge`

export class RiskApiError extends Error {
  constructor(message, { status, code, retryable = false } = {}) {
    super(message)
    this.name = 'RiskApiError'
    this.status = status
    this.code = code
    this.retryable = retryable
  }
}

const FRIENDLY_MESSAGES = {
  validation_error: 'That request could not be validated. Check the input and try again.',
  llm_disabled: 'AI risk assessment is temporarily disabled by the service operator.',
  llm_timeout: 'The AI service took too long to respond. Please try again.',
  invalid_llm_output: 'The AI could not produce a reliable judgement for this request. Please try again or rephrase it.',
  provider_error: 'The AI provider returned an error. Please try again shortly.',
  internal_error: 'Something went wrong on the server. Please try again.',
  network_error: 'Could not reach the RuleGuard AI backend. Is the server running?',
  http_error: 'Something went wrong talking to the server.',
  unknown_error: 'An unexpected error occurred.',
}

export function friendlyErrorMessage(error) {
  if (error instanceof RiskApiError) {
    return FRIENDLY_MESSAGES[error.code] || error.message || FRIENDLY_MESSAGES.unknown_error
  }
  return FRIENDLY_MESSAGES.unknown_error
}

export async function assessRisk(requestText, { signal } = {}) {
  let response

  try {
    response = await fetch(JUDGE_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ request: requestText }),
      signal,
    })
  } catch (networkError) {
    if (networkError.name === 'AbortError') throw networkError
    throw new RiskApiError(FRIENDLY_MESSAGES.network_error, {
      status: 0,
      code: 'network_error',
      retryable: true,
    })
  }

  let body = null
  try {
    body = await response.json()
  } catch {
    body = null
  }

  if (!response.ok) {
    const code = body?.error || 'unknown_error'
    const message = body?.message || `Request failed with status ${response.status}`
    throw new RiskApiError(message, {
      status: response.status,
      code,
      retryable: response.status === 504 || response.status === 502,
    })
  }

  return body
}
