import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Stage3 from './Stage3'

// Mock CopyButton
vi.mock('../../../shared/components/CopyButton', () => ({
  default: ({ text }) => <button data-testid="copy-button">Copy</button>
}))

const mockFinalResponse = {
  model: 'google/gemini-pro',
  response: 'This is the **synthesized** final answer from the council chairman.\n\n- Point 1\n- Point 2\n- Point 3'
}

describe('Stage3', () => {
  describe('Rendering', () => {
    it('renders nothing when finalResponse is undefined', () => {
      const { container } = render(<Stage3 finalResponse={undefined} />)
      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when finalResponse is null', () => {
      const { container } = render(<Stage3 finalResponse={null} />)
      expect(container.firstChild).toBeNull()
    })

    it('renders stage title', () => {
      render(<Stage3 finalResponse={mockFinalResponse} />)
      expect(screen.getByText('Stage 3: Final Council Answer')).toBeInTheDocument()
    })

    it('renders chairman label with model name', () => {
      render(<Stage3 finalResponse={mockFinalResponse} />)
      expect(screen.getByText('Chairman: gemini-pro')).toBeInTheDocument()
    })

    it('renders response text', () => {
      render(<Stage3 finalResponse={mockFinalResponse} />)
      // Check for text content (ReactMarkdown renders markdown)
      expect(screen.getByText(/synthesized/)).toBeInTheDocument()
    })

    it('renders copy button', () => {
      render(<Stage3 finalResponse={mockFinalResponse} />)
      expect(screen.getByTestId('copy-button')).toBeInTheDocument()
    })
  })

  describe('Markdown rendering', () => {
    it('renders markdown formatting', () => {
      render(<Stage3 finalResponse={mockFinalResponse} />)

      // Check that markdown is rendered (bold text becomes <strong>)
      const finalText = screen.getByText(/synthesized/)
      expect(finalText.closest('strong')).toBeInTheDocument()
    })

    it('renders markdown lists', () => {
      render(<Stage3 finalResponse={mockFinalResponse} />)

      // Check for list items
      expect(screen.getByText('Point 1')).toBeInTheDocument()
      expect(screen.getByText('Point 2')).toBeInTheDocument()
      expect(screen.getByText('Point 3')).toBeInTheDocument()
    })
  })

  describe('Model name formatting', () => {
    it('displays short model name without provider', () => {
      render(<Stage3 finalResponse={mockFinalResponse} />)

      // Should show "gemini-pro" not "google/gemini-pro"
      expect(screen.getByText('Chairman: gemini-pro')).toBeInTheDocument()
    })

    it('handles models without provider prefix', () => {
      const responseWithSimpleName = {
        model: 'custom-model',
        response: 'Simple response'
      }

      render(<Stage3 finalResponse={responseWithSimpleName} />)
      expect(screen.getByText('Chairman: custom-model')).toBeInTheDocument()
    })
  })

  describe('CSS classes', () => {
    it('has correct stage class', () => {
      render(<Stage3 finalResponse={mockFinalResponse} />)

      const stageDiv = screen.getByText('Stage 3: Final Council Answer').closest('.stage')
      expect(stageDiv).toHaveClass('stage3')
    })

    it('has markdown-content class on response', () => {
      render(<Stage3 finalResponse={mockFinalResponse} />)

      const markdownDiv = screen.getByText(/synthesized/).closest('.markdown-content')
      expect(markdownDiv).toBeInTheDocument()
    })
  })

  describe('Long response handling', () => {
    it('renders long responses with line breaks', () => {
      const longResponse = {
        model: 'openai/gpt-4',
        response: `# Summary

This is a comprehensive answer.

## Section 1
Content for section 1.

## Section 2
Content for section 2.

### Subsection
More details here.`
      }

      render(<Stage3 finalResponse={longResponse} />)

      expect(screen.getByText('Summary')).toBeInTheDocument()
      expect(screen.getByText('Section 1')).toBeInTheDocument()
      expect(screen.getByText('Section 2')).toBeInTheDocument()
    })

    it('handles code blocks in response', () => {
      const responseWithCode = {
        model: 'openai/gpt-4',
        response: 'Here is some code:\n\n```python\nprint("Hello")\n```'
      }

      render(<Stage3 finalResponse={responseWithCode} />)

      expect(screen.getByText('Here is some code:')).toBeInTheDocument()
    })
  })
})
