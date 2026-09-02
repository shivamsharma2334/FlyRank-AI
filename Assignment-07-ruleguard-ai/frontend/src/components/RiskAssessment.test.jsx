import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RiskApiError, assessRisk } from '../api/riskClient'
import RiskAssessment from './RiskAssessment'

vi.mock('../api/riskClient', async () => {
  const actual = await vi.importActual('../api/riskClient')
  return { ...actual, assessRisk: vi.fn() }
})

describe('RiskAssessment', () => {
  afterEach(() => {
    vi.resetAllMocks()
  })

  it('renders the idle state with submit disabled on empty input', () => {
    render(<RiskAssessment />)

    expect(screen.getByRole('heading', { name: /ruleguard ai/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /assess risk/i })).toBeDisabled()
    expect(screen.queryByText(/result/i)).not.toBeInTheDocument()
  })

  it('does not call the API when submitting empty input', async () => {
    const user = userEvent.setup()
    render(<RiskAssessment />)

    await user.click(screen.getByRole('button', { name: /assess risk/i }))

    expect(assessRisk).not.toHaveBeenCalled()
  })

  it('enables submit once text is entered and shows a loading state while pending', async () => {
    const user = userEvent.setup()
    let resolvePromise
    assessRisk.mockReturnValue(new Promise((resolve) => { resolvePromise = resolve }))

    render(<RiskAssessment />)
    await user.type(screen.getByLabelText(/technical api request/i), 'Allow users to log in.')

    const button = screen.getByRole('button', { name: /assess risk/i })
    expect(button).toBeEnabled()
    await user.click(button)

    expect(await screen.findByRole('button', { name: /assessing/i })).toBeDisabled()

    await act(async () => {
      resolvePromise({
        risk_level: 'low',
        category: 'authentication',
        requires_review: false,
        confidence: 0.9,
        reason: 'Standard authenticated flow.',
      })
    })

    await waitFor(() => expect(screen.getByText(/risk: low/i)).toBeInTheDocument())
  })

  it('renders a full result on success, including human review status', async () => {
    const user = userEvent.setup()
    assessRisk.mockResolvedValue({
      risk_level: 'high',
      category: 'authorization',
      requires_review: true,
      confidence: 0.93,
      reason: 'Missing an ownership check.',
    })

    render(<RiskAssessment />)
    await user.type(screen.getByLabelText(/technical api request/i), 'Delete another user account.')
    await user.click(screen.getByRole('button', { name: /assess risk/i }))

    expect(await screen.findByText(/risk: high/i)).toBeInTheDocument()
    expect(screen.getByText('authorization')).toBeInTheDocument()
    expect(screen.getByText('0.93')).toBeInTheDocument()
    expect(screen.getByText('Required')).toBeInTheDocument()
    expect(screen.getByText('Missing an ownership check.')).toBeInTheDocument()
  })

  it('shows a friendly error message when the API call fails', async () => {
    const user = userEvent.setup()
    assessRisk.mockRejectedValue(new RiskApiError('raw', { status: 504, code: 'llm_timeout' }))

    render(<RiskAssessment />)
    await user.type(screen.getByLabelText(/technical api request/i), 'Allow users to log in.')
    await user.click(screen.getByRole('button', { name: /assess risk/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/took too long/i)
  })

  it('blocks submission and flags the counter when input exceeds the character limit', () => {
    render(<RiskAssessment />)
    const textarea = screen.getByLabelText(/technical api request/i)

    fireEvent.change(textarea, { target: { value: 'x'.repeat(2001) } })

    expect(screen.getByRole('button', { name: /assess risk/i })).toBeDisabled()
    expect(screen.getByText('2001 / 2000')).toHaveClass('assessment__count--over')
  })

  it('lets the user start a new assessment after a result is shown', async () => {
    const user = userEvent.setup()
    assessRisk.mockResolvedValue({ risk_level: 'low', category: 'other', requires_review: false, confidence: 0.7, reason: 'ok' })

    render(<RiskAssessment />)
    await user.type(screen.getByLabelText(/technical api request/i), 'Some request text.')
    await user.click(screen.getByRole('button', { name: /assess risk/i }))
    await screen.findByText(/risk: low/i)

    await user.click(screen.getByRole('button', { name: /new assessment/i }))

    expect(screen.queryByText(/risk: low/i)).not.toBeInTheDocument()
    expect(screen.getByLabelText(/technical api request/i)).toHaveValue('')
  })
})
