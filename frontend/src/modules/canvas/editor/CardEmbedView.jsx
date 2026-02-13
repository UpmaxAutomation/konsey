import { NodeViewWrapper } from '@tiptap/react';
import { useBoardActions } from '../BoardContext.js';
import './CardEmbedView.css';

const CARD_TYPE_COLORS = {
  note: '#3b82f6',
  council_response: '#10b981',
  council_synthesis: '#059669',
  research: '#8b5cf6',
  board_ref: '#f59e0b',
};

export default function CardEmbedView({ node }) {
  const { cardId, cardTitle } = node.attrs;
  const board = useBoardActions();

  const handleClick = () => {
    if (board?.focusCard && cardId) {
      board.focusCard(cardId);
    }
  };

  return (
    <NodeViewWrapper className="card-embed-wrapper">
      <div className="card-embed" onClick={handleClick} title="Click to navigate to card">
        <div className="card-embed__header">
          <span
            className="card-embed__badge"
            style={{ background: CARD_TYPE_COLORS[node.attrs.cardType] || '#94a3b8' }}
          >
            {node.attrs.cardType?.replace(/_/g, ' ') || 'card'}
          </span>
          <span className="card-embed__title">{cardTitle || 'Untitled Card'}</span>
          <svg className="card-embed__link-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" />
          </svg>
        </div>
        {node.attrs.cardContent && (
          <div className="card-embed__preview">
            {node.attrs.cardContent.split('\n').slice(0, 3).map((line, i) => (
              <div key={i} className="card-embed__preview-line">{line}</div>
            ))}
          </div>
        )}
      </div>
    </NodeViewWrapper>
  );
}
