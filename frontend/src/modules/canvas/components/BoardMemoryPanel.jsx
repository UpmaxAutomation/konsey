import { useState, useRef, useEffect } from 'react';
import '../styles/BoardMemoryPanel.css';

export default function BoardMemoryPanel({ memory, onAddFact, onDeleteFact, onClear, onClose }) {
  const [newFact, setNewFact] = useState('');
  const [activeTab, setActiveTab] = useState('facts');
  const inputRef = useRef(null);

  useEffect(() => {
    if (inputRef.current) inputRef.current.focus();
  }, []);

  const facts = memory?.facts || [];
  const decisions = memory?.decisions || [];

  const handleAddFact = () => {
    const text = newFact.trim();
    if (!text) return;
    onAddFact(text);
    setNewFact('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAddFact();
    }
    if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <div className="board-memory-panel">
      <div className="board-memory-panel__header">
        <h3 className="board-memory-panel__title">Board Memory</h3>
        <button className="board-memory-panel__close" onClick={onClose} title="Close">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="board-memory-panel__tabs">
        <button
          className={`board-memory-panel__tab ${activeTab === 'facts' ? 'board-memory-panel__tab--active' : ''}`}
          onClick={() => setActiveTab('facts')}
        >
          Facts ({facts.length})
        </button>
        <button
          className={`board-memory-panel__tab ${activeTab === 'decisions' ? 'board-memory-panel__tab--active' : ''}`}
          onClick={() => setActiveTab('decisions')}
        >
          Decisions ({decisions.length})
        </button>
      </div>

      <div className="board-memory-panel__content">
        {activeTab === 'facts' && (
          <>
            <div className="board-memory-panel__input-row">
              <input
                ref={inputRef}
                className="board-memory-panel__input"
                value={newFact}
                onChange={(e) => setNewFact(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Add a fact or note..."
              />
              <button
                className="board-memory-panel__add-btn"
                onClick={handleAddFact}
                disabled={!newFact.trim()}
              >
                Add
              </button>
            </div>
            {facts.length === 0 ? (
              <div className="board-memory-panel__empty">
                No facts yet. Add context that AI actions should know about.
              </div>
            ) : (
              <ul className="board-memory-panel__list">
                {facts.map((fact, idx) => (
                  <li key={idx} className="board-memory-panel__item">
                    <span className="board-memory-panel__item-text">{fact.content || fact}</span>
                    <button
                      className="board-memory-panel__item-delete"
                      onClick={() => onDeleteFact(idx)}
                      title="Delete fact"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12" />
                      </svg>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}

        {activeTab === 'decisions' && (
          <>
            {decisions.length === 0 ? (
              <div className="board-memory-panel__empty">
                No decisions yet. Council results are saved here automatically.
              </div>
            ) : (
              <ul className="board-memory-panel__list">
                {decisions.map((dec, idx) => (
                  <li key={idx} className="board-memory-panel__item board-memory-panel__item--decision">
                    {dec.context && (
                      <div className="board-memory-panel__decision-context">Q: {dec.context}</div>
                    )}
                    <span className="board-memory-panel__item-text">{dec.content || dec}</span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>

      <div className="board-memory-panel__footer">
        <button
          className="board-memory-panel__clear-btn"
          onClick={onClear}
          disabled={facts.length === 0 && decisions.length === 0}
        >
          Clear All Memory
        </button>
      </div>
    </div>
  );
}
