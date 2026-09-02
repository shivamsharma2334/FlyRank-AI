import { useState } from 'react'
import { useRiskAssessment, STATUS } from '../hooks/useRiskAssessment'
import { MAX_REQUEST_LENGTH } from '../api/riskClient'

const PLACEHOLDER =
  'Describe the technical API request or change you want assessed...\n\n' +
  'Example: Allow users to change their email address after confirming their current password.'

const RISK_LABELS = { low: 'LOW', medium: 'MEDIUM', high: 'HIGH' }

function ResultPanel({ result }) {
  return (
    <section className="assessment__result" aria-live="polite">
      <h2>Result</h2>

      <div className={`assessment__risk assessment__risk--${result.risk_level}`}>
        Risk: {RISK_LABELS[result.risk_level] || result.risk_level.toUpperCase()}
      </div>

      <dl className="assessment__fields">
        <dt>Category</dt>
        <dd>{result.category}</dd>

        <dt>Confidence</dt>
        <dd>{result.confidence.toFixed(2)}</dd>

        <dt>Human Review</dt>
        <dd className={result.requires_review ? 'assessment__review--required' : ''}>
          {result.requires_review ? 'Required' : 'Not required'}
        </dd>

        <dt>Reason</dt>
        <dd>{result.reason}</dd>
      </dl>
    </section>
  )
}

export default function RiskAssessment() {
  const [requestText, setRequestText] = useState('')
  const { status, result, error, isLoading, submit, reset } = useRiskAssessment()

  const trimmedLength = requestText.trim().length
  const isEmpty = trimmedLength === 0
  const isOverLimit = trimmedLength > MAX_REQUEST_LENGTH

  const handleSubmit = (event) => {
    event.preventDefault()
    if (isEmpty || isOverLimit || isLoading) return
    submit(requestText)
  }

  const handleReset = () => {
    setRequestText('')
    reset()
  }

  return (
    <div className="assessment">
      <header className="assessment__header">
        <h1>RuleGuard AI</h1>
        <p>API Request Risk Assessment</p>
      </header>

      <form className="assessment__form" onSubmit={handleSubmit}>
        <label htmlFor="request-input" className="assessment__label">
          Technical API request
        </label>
        <textarea
          id="request-input"
          className="assessment__textarea"
          placeholder={PLACEHOLDER}
          value={requestText}
          onChange={(event) => setRequestText(event.target.value)}
          rows={6}
          disabled={isLoading}
        />
        <div className="assessment__meta">
          <span className={isOverLimit ? 'assessment__count assessment__count--over' : 'assessment__count'}>
            {trimmedLength} / {MAX_REQUEST_LENGTH}
          </span>
        </div>

        <div className="assessment__actions">
          <button type="submit" className="assessment__submit" disabled={isEmpty || isOverLimit || isLoading}>
            {isLoading ? 'Assessing…' : 'Assess Risk'}
          </button>
          {(result || error) && (
            <button type="button" className="assessment__reset" onClick={handleReset}>
              New Assessment
            </button>
          )}
        </div>
      </form>

      {status === STATUS.ERROR && error && (
        <div className="assessment__error" role="alert">
          <strong>Error:</strong> {error}
        </div>
      )}

      {status === STATUS.SUCCESS && result && <ResultPanel result={result} />}
    </div>
  )
}
