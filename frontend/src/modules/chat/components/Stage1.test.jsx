import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Stage1 from './Stage1'

// Mock child components
vi.mock('./CompareView', () => ({
  default: ({ isOpen, onClose }) => isOpen ? (
    <div data-testid="compare-view">
      <button onClick={onClose}>Close</button>
    </div>
  ) : null
}))

vi.mock('../../../shared/components/CopyButton', () => ({
  default: ({ text }) => <button data-testid="copy-button">Copy</button>
}))

const mockResponses = [
  {
    model: 'openai/gpt-4',
    response: 'This is the GPT-4 response about Python.',
    thinking: null
  },
  {
    model: 'anthropic/claude-3',
    response: 'This is the Claude response about Python.',
    thinking: 'Let me think step by step about this question...'
  },
  {
    model: 'google/gemini-pro',
    response: 'This is the Gemini response about Python.',
    thinking: null
  }
]

describe('Stage1', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })

  describe('Rendering', () => {
    it('renders nothing when responses is empty', () => {
      const { container } = render(<Stage1 responses={[]} />)
      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when responses is undefined', () => {
      const { container } = render(<Stage1 responses={undefined} />)
      expect(container.firstChild).toBeNull()
    })

    it('renders stage title', () => {
      render(<Stage1 responses={mockResponses} />)
      expect(screen.getByText('Stage 1: Individual Responses')).toBeInTheDocument()
    })

    it('renders tabs for each model', () => {
      render(<Stage1 responses={mockResponses} />)

      expect(screen.getByText('gpt-4')).toBeInTheDocument()
      expect(screen.getByText('claude-3')).toBeInTheDocument()
      expect(screen.getByText('gemini-pro')).toBeInTheDocument()
    })

    it('shows first response by default', () => {
      render(<Stage1 responses={mockResponses} />)

      expect(screen.getByText('This is the GPT-4 response about Python.')).toBeInTheDocument()
      expect(screen.getByText('openai/gpt-4')).toBeInTheDocument()
    })

    it('shows brain emoji for models with thinking', () => {
      render(<Stage1 responses={mockResponses} />)

      // Claude-3 tab should have thinking indicator
      const thinkingIndicators = screen.getAllByTitle('Has reasoning tokens')
      expect(thinkingIndicators.length).toBe(1)
    })

    it('renders compare button when multiple responses', () => {
      render(<Stage1 responses={mockResponses} />)
      expect(screen.getByText('⚖️ Compare')).toBeInTheDocument()
    })

    it('does not render compare button for single response', () => {
      render(<Stage1 responses={[mockResponses[0]]} />)
      expect(screen.queryByText('⚖️ Compare')).not.toBeInTheDocument()
    })
  })

  describe('Tab switching', () => {
    it('switches content when tab is clicked', () => {
      render(<Stage1 responses={mockResponses} />)

      // Initially shows GPT-4 response
      expect(screen.getByText('This is the GPT-4 response about Python.')).toBeInTheDocument()

      // Click Claude tab
      fireEvent.click(screen.getByText('claude-3'))

      // Should now show Claude response
      expect(screen.getByText('This is the Claude response about Python.')).toBeInTheDocument()
    })

    it('marks active tab', () => {
      render(<Stage1 responses={mockResponses} />)

      const gptTab = screen.getByText('gpt-4').closest('button')
      expect(gptTab).toHaveClass('active')

      fireEvent.click(screen.getByText('claude-3'))

      const claudeTab = screen.getByText('claude-3').closest('button')
      expect(claudeTab).toHaveClass('active')
      expect(gptTab).not.toHaveClass('active')
    })
  })

  describe('Thinking/reasoning display', () => {
    it('shows toggle button for models with thinking', () => {
      render(<Stage1 responses={mockResponses} />)

      // Switch to Claude tab (has thinking)
      fireEvent.click(screen.getByText('claude-3'))

      expect(screen.getByText('▶ Show Reasoning')).toBeInTheDocument()
    })

    it('does not show toggle button for models without thinking', () => {
      render(<Stage1 responses={mockResponses} />)

      // GPT-4 tab (no thinking)
      expect(screen.queryByText('▶ Show Reasoning')).not.toBeInTheDocument()
    })

    it('toggles thinking visibility when button is clicked', () => {
      render(<Stage1 responses={mockResponses} />)

      // Switch to Claude tab
      fireEvent.click(screen.getByText('claude-3'))

      // Click show reasoning
      fireEvent.click(screen.getByText('▶ Show Reasoning'))

      // Should show thinking content
      expect(screen.getByText('Reasoning Process:')).toBeInTheDocument()
      expect(screen.getByText('Let me think step by step about this question...')).toBeInTheDocument()
      expect(screen.getByText('▼ Hide Reasoning')).toBeInTheDocument()

      // Click hide reasoning
      fireEvent.click(screen.getByText('▼ Hide Reasoning'))

      // Should hide thinking content
      expect(screen.queryByText('Reasoning Process:')).not.toBeInTheDocument()
    })
  })

  describe('Compare view', () => {
    it('opens compare view when button is clicked', () => {
      render(<Stage1 responses={mockResponses} />)

      fireEvent.click(screen.getByText('⚖️ Compare'))

      expect(screen.getByTestId('compare-view')).toBeInTheDocument()
    })

    it('closes compare view when close is triggered', () => {
      render(<Stage1 responses={mockResponses} />)

      fireEvent.click(screen.getByText('⚖️ Compare'))
      expect(screen.getByTestId('compare-view')).toBeInTheDocument()

      fireEvent.click(screen.getByText('Close'))
      expect(screen.queryByTestId('compare-view')).not.toBeInTheDocument()
    })
  })

  describe('Rating system', () => {
    const propsWithContext = {
      responses: mockResponses,
      conversationId: 'conv-123',
      messageIndex: 0
    }

    it('shows rating section when context is provided', () => {
      render(<Stage1 {...propsWithContext} />)
      expect(screen.getByText('Rate this response:')).toBeInTheDocument()
    })

    it('does not show rating section without conversationId', () => {
      render(<Stage1 responses={mockResponses} messageIndex={0} />)
      expect(screen.queryByText('Rate this response:')).not.toBeInTheDocument()
    })

    it('does not show rating section without messageIndex', () => {
      render(<Stage1 responses={mockResponses} conversationId="conv-123" />)
      expect(screen.queryByText('Rate this response:')).not.toBeInTheDocument()
    })

    it('renders 5 star buttons', () => {
      render(<Stage1 {...propsWithContext} />)
      const stars = screen.getAllByTitle(/star/)
      expect(stars.length).toBe(5)
    })

    it('shows feedback toggle button', () => {
      render(<Stage1 {...propsWithContext} />)
      expect(screen.getByText('▶ Add Feedback')).toBeInTheDocument()
    })

    it('shows feedback textarea when toggle is clicked', () => {
      render(<Stage1 {...propsWithContext} />)

      fireEvent.click(screen.getByText('▶ Add Feedback'))

      expect(screen.getByPlaceholderText(/Share your thoughts/)).toBeInTheDocument()
      expect(screen.getByText('Save Feedback')).toBeInTheDocument()
    })

    it('submits rating when star is clicked', async () => {
      global.fetch = vi.fn().mockResolvedValue({ ok: true })

      render(<Stage1 {...propsWithContext} />)

      const stars = screen.getAllByTitle(/star/)
      fireEvent.click(stars[3]) // 4 stars

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          expect.stringContaining('/api/ratings'),
          expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('"rating":4')
          })
        )
      })
    })

    it('loads existing ratings on mount', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({
          has_rating: true,
          rating: { rating: 5, feedback_text: 'Great response!' }
        })
      })

      render(<Stage1 {...propsWithContext} />)

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalled()
      })
    })
  })

  describe('Copy button', () => {
    it('renders copy button for current response', () => {
      render(<Stage1 responses={mockResponses} />)
      expect(screen.getByTestId('copy-button')).toBeInTheDocument()
    })
  })
})
