import { afterEach, describe, expect, it, vi } from 'vitest'
import { assessRisk, friendlyErrorMessage, RiskApiError } from './riskClient'

function mockFetchOnce(body, { ok = true, status = 200 } = {}) {
  global.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(body),
  })
}

describe('assessRisk', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts the request text to the judge endpoint and returns the parsed judgement', async () => {
    const judgement = {
      risk_level: 'low',
      category: 'authentication',
      requires_review: false,
      confidence: 0.9,
      reason: 'Looks fine.',
    }
    mockFetchOnce(judgement)

    const result = await assessRisk('Allow users to log in.')

    expect(global.fetch).toHaveBeenCalledTimes(1)
    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain('/api/v1/risk/judge')
    expect(options.method).toBe('POST')
    expect(options.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(options.body)).toEqual({ request: 'Allow users to log in.' })
    expect(result).toEqual(judgement)
  })

  it('throws a RiskApiError built from the error envelope on a non-OK response', async () => {
    mockFetchOnce(
      { error: 'invalid_llm_output', message: 'The model response could not be validated after one repair attempt.' },
      { ok: false, status: 422 }
    )

    await expect(assessRisk('some request')).rejects.toMatchObject({
      name: 'RiskApiError',
      code: 'invalid_llm_output',
      status: 422,
    })
  })

  it('marks 502 and 504 responses as retryable', async () => {
    mockFetchOnce({ error: 'llm_timeout', message: 'timed out' }, { ok: false, status: 504 })

    try {
      await assessRisk('some request')
      throw new Error('expected assessRisk to throw')
    } catch (err) {
      expect(err.retryable).toBe(true)
    }
  })

  it('wraps a network failure in a retryable RiskApiError', async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(assessRisk('some request')).rejects.toMatchObject({
      name: 'RiskApiError',
      code: 'network_error',
      retryable: true,
    })
  })

  it('re-throws AbortError without wrapping it', async () => {
    const abortError = new DOMException('aborted', 'AbortError')
    global.fetch = vi.fn().mockRejectedValue(abortError)

    await expect(assessRisk('some request')).rejects.toBe(abortError)
  })
})

describe('friendlyErrorMessage', () => {
  it('maps known error codes to a friendly message', () => {
    const error = new RiskApiError('raw', { status: 503, code: 'llm_disabled' })
    expect(friendlyErrorMessage(error)).toMatch(/temporarily disabled/i)
  })

  it('falls back to a generic message when code and message are both unrecognized', () => {
    const error = new RiskApiError('', { status: 500, code: 'something_new' })
    expect(friendlyErrorMessage(error)).toBe('An unexpected error occurred.')
  })

  it('returns the generic message for non-RiskApiError values', () => {
    expect(friendlyErrorMessage(new Error('boom'))).toBe('An unexpected error occurred.')
  })
})
