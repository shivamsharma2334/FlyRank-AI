import { useCallback, useRef, useState } from 'react'
import { assessRisk, friendlyErrorMessage, MAX_REQUEST_LENGTH, RiskApiError } from '../api/riskClient'

export const STATUS = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error',
}

export function useRiskAssessment() {
  const [status, setStatus] = useState(STATUS.IDLE)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const abortControllerRef = useRef(null)

  const submit = useCallback(async (requestText) => {
    const trimmed = (requestText || '').trim()

    if (!trimmed) {
      return
    }

    if (trimmed.length > MAX_REQUEST_LENGTH) {
      setStatus(STATUS.ERROR)
      setResult(null)
      setError(`Request must be ${MAX_REQUEST_LENGTH} characters or fewer (currently ${trimmed.length}).`)
      return
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    setStatus(STATUS.LOADING)
    setError(null)

    try {
      const judgement = await assessRisk(trimmed, { signal: controller.signal })
      setResult(judgement)
      setStatus(STATUS.SUCCESS)
    } catch (err) {
      if (err.name === 'AbortError') {
        return
      }
      setResult(null)
      setError(err instanceof RiskApiError ? friendlyErrorMessage(err) : friendlyErrorMessage())
      setStatus(STATUS.ERROR)
    }
  }, [])

  const reset = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setStatus(STATUS.IDLE)
    setResult(null)
    setError(null)
  }, [])

  return { status, result, error, isLoading: status === STATUS.LOADING, submit, reset }
}
