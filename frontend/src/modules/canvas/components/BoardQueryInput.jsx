import { useState, useRef, useEffect } from 'react';
import '../styles/BoardQueryInput.css';

export default function BoardQueryInput({ selectedCards, onRun, onClose, isRunning }) {
  const [query, setQuery] = useState('');
  const [webSearch, setWebSearch] = useState(false);
  const [fastMode, setFastMode] = useState(false);
  const textareaRef = useRef(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = () => {
    if (!query.trim() || isRunning) return;
    onRun({ query: query.trim(), webSearch, fastMode });
  };

  return (
    <div className="board-query-overlay" onClick={onClose}>
      <div className="board-query-modal" onClick={(e) => e.stopPropagation()}>
        <div className="board-query-header">
          <h3>Run Council on Board</h3>
          <button className="board-query-close" onClick={onClose}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {selectedCards.length > 0 && (
          <div className="board-query-context">
            <span className="board-query-context-label">Context cards:</span>
            <div className="board-query-chips">
              {selectedCards.map((card) => (
                <span key={card.id} className={`board-query-chip chip--${card.card_type}`}>
                  {card.title || card.card_type}
                </span>
              ))}
            </div>
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="board-query-textarea"
          placeholder="What would you like the council to deliberate on?"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit();
            if (e.key === 'Escape') onClose();
          }}
          rows={4}
          disabled={isRunning}
        />

        <div className="board-query-options">
          <label className="board-query-toggle">
            <input
              type="checkbox"
              checked={webSearch}
              onChange={(e) => setWebSearch(e.target.checked)}
              disabled={isRunning}
            />
            <span>Web Search</span>
          </label>
          <label className="board-query-toggle">
            <input
              type="checkbox"
              checked={fastMode}
              onChange={(e) => setFastMode(e.target.checked)}
              disabled={isRunning}
            />
            <span>Fast Mode</span>
          </label>
        </div>

        <div className="board-query-footer">
          <span className="board-query-hint">Cmd+Enter to run</span>
          <button
            className="board-query-run"
            onClick={handleSubmit}
            disabled={!query.trim() || isRunning}
          >
            {isRunning ? (
              <>
                <svg className="spinning" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                </svg>
                Running...
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Run Council
              </>
            )}
          </button>
        </div>

        {isRunning && (
          <div className="board-query-progress">
            <div className="board-query-progress-bar" />
          </div>
        )}
      </div>
    </div>
  );
}
