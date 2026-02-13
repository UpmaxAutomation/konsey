import { useQuery } from '@tanstack/react-query';
import { listCards } from '../../../api/boards.js';

const TYPE_DOTS = {
  note: '#6366f1',
  knowledge: '#8b5cf6',
  query: '#f59e0b',
  council_response: '#06b6d4',
  council_synthesis: '#10b981',
  board_ref: '#a855f7',
};

export default function BoardRefPreview({ boardId, title }) {
  const { data: cards, isLoading } = useQuery({
    queryKey: ['board-preview', boardId],
    queryFn: () => listCards(boardId),
    enabled: !!boardId,
    staleTime: 60000,
  });

  const cardList = Array.isArray(cards) ? cards : cards?.cards || [];

  return (
    <div className="canvas-card__board-ref">
      <div className="canvas-card__board-ref-top">
        <span className="canvas-card__board-ref-icon">{'\uD83D\uDCC1'}</span>
        <span className="canvas-card__board-ref-name">{title || 'Sub-board'}</span>
      </div>
      {isLoading ? (
        <div className="canvas-card__board-ref-loading">Loading...</div>
      ) : cardList.length > 0 ? (
        <div className="canvas-card__board-ref-preview">
          <span className="canvas-card__board-ref-count">{cardList.length} card{cardList.length !== 1 ? 's' : ''}</span>
          <div className="canvas-card__board-ref-cards">
            {cardList.slice(0, 4).map((c) => (
              <div key={c.id} className="canvas-card__board-ref-card-row">
                <span
                  className="canvas-card__board-ref-dot"
                  style={{ background: TYPE_DOTS[c.card_type] || '#94a3b8' }}
                />
                <span className="canvas-card__board-ref-card-title">
                  {c.title || 'Untitled'}
                </span>
              </div>
            ))}
            {cardList.length > 4 && (
              <span className="canvas-card__board-ref-more">+{cardList.length - 4} more</span>
            )}
          </div>
        </div>
      ) : (
        <span className="canvas-card__board-ref-empty">Empty board</span>
      )}
      <span className="canvas-card__board-ref-hint">Double-click to open</span>
    </div>
  );
}
