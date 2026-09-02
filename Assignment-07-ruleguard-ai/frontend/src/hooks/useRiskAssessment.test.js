import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RiskApiError, assessRisk } from '../api/riskClient'
import { STATUS, useRiskAssessment } from './useRiskAssessment'

vi.mock('../api/riskClient', async () => {
  const actual = await vi.importActual('../api/riskClient')
  return { ...actual, assessRisk: vi.fn() }
})

describe('useRiskAssessment', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('starts idle', () => {
    const { result } = renderHook(() => useRiskAssessment())
    expect(result.current.status).toBe(STATUS.IDLE)
    expect(result.current.result).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it('does nothing for an empty or whitespace-only request', async () => {
    const { result } = renderHook(() => useRiskAssessment())

    await act(async () => {
      await result.current.submit('   ')
    })

    expect(assessRisk).not.toHaveBeenCalled()
    expect(result.current.status).toBe(STATUS.IDLE)
  })

  it('rejects a request over the character limit without calling the API', async () => {
    const { result } = renderHook(() => useRiskAssessment())

    await act(async () => {
      await result.current.submit('x'.repeat(2001))
    })

    expect(assessRisk).not.toHaveBeenCalled()
    expect(result.current.status).toBe(STATUS.ERROR)
    expect(result.current.error).toMatch(/2000 characters or fewer/)
  })

  it('goes idle -> loading -> success on a valid request', async () => {
    const judgement = { risk_level: 'low', category: 'other', requires_review: false, confidence: 0.8, reason: 'ok' }
    let resolvePromise
    assessRisk.mockReturnValue(new Promise((resolve) => { resolvePromise = resolve }))

    const { result } = renderHook(() => useRiskAssessment())

    act(() => {
      result.current.submit('Allow users to log in.')
    })

    await waitFor(() => expect(result.current.status).toBe(STATUS.LOADING))

    await act(async () => {
      resolvePromise(judgement)
    })

    await waitFor(() => expect(result.current.status).toBe(STATUS.SUCCESS))
    expect(result.current.result).toEqual(judgement)
    expect(result.current.error).toBeNull()
  })

  it('goes to an error state with a friendly message when the API call fails', async () => {
    assessRisk.mockRejectedValue(new RiskApiError('raw provider message', { status: 503, code: 'llm_disabled' }))

    const { result } = renderHook(() => useRiskAssessment())

    await act(async () => {
      await result.current.submit('Allow users to log in.')
    })

    expect(result.current.status).toBe(STATUS.ERROR)
    expect(result.current.result).toBeNull()
    expect(result.current.error).toMatch(/temporarily disabled/i)
  })

  it('reset clears result, error and status back to idle', async () => {
    assessRisk.mockRejectedValue(new RiskApiError('x', { status: 500, code: 'unknown_error' }))
    const { result } = renderHook(() => useRiskAssessment())

    await act(async () => {
      await result.current.submit('Allow users to log in.')
    })
    expect(result.current.status).toBe(STATUS.ERROR)

    act(() => {
      result.current.reset()
    })

    expect(result.current.status).toBe(STATUS.IDLE)
    expect(result.current.result).toBeNull()
    expect(result.current.error).toBeNull()
  })
})
