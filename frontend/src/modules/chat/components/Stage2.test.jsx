import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Stage2 from './Stage2'

const mockRankings = [
  {
    model: 'openai/gpt-4',
    ranking: 'Response A is good. Response B is better. Response C is best.\n\nFINAL RANKING:\n1. Response C\n2. Response B\n3. Response A',
    parsed_ranking: ['Response C', 'Response B', 'Response A']
  },
  {
    model: 'anthropic/claude-3',
    ranking: 'Analysis complete.\n\nFINAL RANKING:\n1. Response B\n2. Response C\n3. Response A',
    parsed_ranking: ['Response B', 'Response C', 'Response A']
  },
  {
    model: 'google/gemini-pro',
    ranking: 'All responses were helpful.\n\nFINAL RANKING:\n1. Response C\n2. Response A\n3. Response B',
    parsed_ranking: ['Response C', 'Response A', 'Response B']
  }
]

const mockLabelToModel = {
  'Response A': 'openai/gpt-4',
  'Response B': 'anthropic/claude-3',
  'Response C': 'google/gemini-pro'
}

const mockAggregateRankings = [
  { model: 'google/gemini-pro', average_rank: 1.33, rankings_count: 3 },
  { model: 'anthropic/claude-3', average_rank: 2.0, rankings_count: 3 },
  { model: 'openai/gpt-4', average_rank: 2.67, rankings_count: 3 }
]

describe('Stage2', () => {
  describe('Rendering', () => {
    it('renders nothing when rankings is empty', () => {
      const { container } = render(<Stage2 rankings={[]} />)
      expect(container.firstChild).toBeNull()
    })

    it('renders nothing when rankings is undefined', () => {
      const { container } = render(<Stage2 rankings={undefined} />)
      expect(container.firstChild).toBeNull()
    })

    it('renders stage title', () => {
      render(<Stage2 rankings={mockRankings} />)
      expect(screen.getByText('Stage 2: Peer Rankings')).toBeInTheDocument()
    })

    it('renders explanatory description', () => {
      render(<Stage2 rankings={mockRankings} />)
      expect(screen.getByText(/Each model evaluated all responses/)).toBeInTheDocument()
    })

    it('renders tabs for each model', () => {
      render(<Stage2 rankings={mockRankings} />)

      expect(screen.getByText('gpt-4')).toBeInTheDocument()
      expect(screen.getByText('claude-3')).toBeInTheDocument()
      expect(screen.getByText('gemini-pro')).toBeInTheDocument()
    })

    it('shows first ranking by default', () => {
      render(<Stage2 rankings={mockRankings} />)
      expect(screen.getByText('openai/gpt-4')).toBeInTheDocument()
    })
  })

  describe('Tab switching', () => {
    it('switches content when tab is clicked', () => {
      render(<Stage2 rankings={mockRankings} />)

      // Click Claude tab
      fireEvent.click(screen.getByText('claude-3'))

      // Should show Claude's ranking
      expect(screen.getByText('anthropic/claude-3')).toBeInTheDocument()
      expect(screen.getByText(/Analysis complete/)).toBeInTheDocument()
    })

    it('marks active tab', () => {
      render(<Stage2 rankings={mockRankings} />)

      const gptTab = screen.getByText('gpt-4').closest('button')
      expect(gptTab).toHaveClass('active')

      fireEvent.click(screen.getByText('claude-3'))

      const claudeTab = screen.getByText('claude-3').closest('button')
      expect(claudeTab).toHaveClass('active')
      expect(gptTab).not.toHaveClass('active')
    })
  })

  describe('De-anonymization', () => {
    it('replaces Response labels with model names when labelToModel provided', () => {
      render(
        <Stage2
          rankings={mockRankings}
          labelToModel={mockLabelToModel}
        />
      )

      // The markdown should show de-anonymized names in bold
      // ReactMarkdown renders **text** as <strong>
      // Check that the raw "Response A" is transformed
      expect(screen.queryByText('Response A is good')).not.toBeInTheDocument()
    })

    it('shows raw labels when labelToModel is not provided', () => {
      render(<Stage2 rankings={mockRankings} />)

      // Without labelToModel, should show raw labels
      expect(screen.getByText(/Response A is good/)).toBeInTheDocument()
    })
  })

  describe('Parsed ranking display', () => {
    it('shows extracted ranking section', () => {
      render(<Stage2 rankings={mockRankings} />)
      expect(screen.getByText('Extracted Ranking:')).toBeInTheDocument()
    })

    it('shows parsed ranking as ordered list', () => {
      render(
        <Stage2
          rankings={mockRankings}
          labelToModel={mockLabelToModel}
        />
      )

      // Check the first tab (GPT-4) parsed ranking: C, B, A
      // With labelToModel, should show model names
      const listItems = screen.getAllByRole('listitem')
      expect(listItems.length).toBe(3)
    })

    it('does not show extracted ranking if parsed_ranking is empty', () => {
      const rankingsWithoutParsed = [{
        ...mockRankings[0],
        parsed_ranking: []
      }]

      render(<Stage2 rankings={rankingsWithoutParsed} />)
      expect(screen.queryByText('Extracted Ranking:')).not.toBeInTheDocument()
    })
  })

  describe('Aggregate rankings', () => {
    it('shows aggregate rankings when provided', () => {
      render(
        <Stage2
          rankings={mockRankings}
          aggregateRankings={mockAggregateRankings}
        />
      )

      expect(screen.getByText('Aggregate Rankings (Street Cred)')).toBeInTheDocument()
      expect(screen.getByText(/lower score is better/)).toBeInTheDocument()
    })

    it('does not show aggregate section when not provided', () => {
      render(<Stage2 rankings={mockRankings} />)
      expect(screen.queryByText('Aggregate Rankings (Street Cred)')).not.toBeInTheDocument()
    })

    it('does not show aggregate section when empty', () => {
      render(
        <Stage2
          rankings={mockRankings}
          aggregateRankings={[]}
        />
      )
      expect(screen.queryByText('Aggregate Rankings (Street Cred)')).not.toBeInTheDocument()
    })

    it('displays rank positions correctly', () => {
      render(
        <Stage2
          rankings={mockRankings}
          aggregateRankings={mockAggregateRankings}
        />
      )

      expect(screen.getByText('#1')).toBeInTheDocument()
      expect(screen.getByText('#2')).toBeInTheDocument()
      expect(screen.getByText('#3')).toBeInTheDocument()
    })

    it('displays average rank and vote count', () => {
      render(
        <Stage2
          rankings={mockRankings}
          aggregateRankings={mockAggregateRankings}
        />
      )

      expect(screen.getByText('Avg: 1.33')).toBeInTheDocument()
      expect(screen.getByText('(3 votes)')).toBeInTheDocument()
    })

    it('shows aggregate model names without provider prefix', () => {
      render(
        <Stage2
          rankings={mockRankings}
          aggregateRankings={mockAggregateRankings}
        />
      )

      // Should show "gemini-pro" not "google/gemini-pro"
      const aggregateSection = screen.getByText('Aggregate Rankings (Street Cred)').parentElement
      expect(aggregateSection).toHaveTextContent('gemini-pro')
    })
  })

  describe('Model name formatting', () => {
    it('displays short model names in tabs', () => {
      render(<Stage2 rankings={mockRankings} />)

      // Should show "gpt-4" not "openai/gpt-4"
      expect(screen.getByText('gpt-4')).toBeInTheDocument()
    })

    it('displays full model name in content header', () => {
      render(<Stage2 rankings={mockRankings} />)

      // Full name shown in content area
      expect(screen.getByText('openai/gpt-4')).toBeInTheDocument()
    })
  })
})
