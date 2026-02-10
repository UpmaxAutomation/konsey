import { useEffect, useRef } from 'react';
import '../styles/BoardSearch.css';

const CARD_TYPES = [
  { value: 'all', label: 'All Types' },
  { value: 'note', label: 'Notes' },
  { value: 'query', label: 'Queries' },
  { value: 'council_response', label: 'Responses' },
  { value: 'council_synthesis', label: 'Synthesis' },
  { value: 'file_ref', label: 'Files' },
  { value: 'link', label: 'Links' },
];

/**
 * Search bar for the board canvas with type filtering
 * and keyboard navigation (arrow keys / Enter to cycle matches).
 *
 * @param {Object} props
 * @param {string}   props.query - Current search query
 * @param {Function} props.setQuery - Update query
 * @param {string}   props.filterType - Active card-type filter
 * @param {Function} props.setFilterType - Update filter
 * @param {number}   props.matchCount - Total number of matches
 * @param {number}   props.activeIndex - Zero-based index of the active match
 * @param {Function} props.onNext - Advance to next match
 * @param {Function} props.onPrev - Go to previous match
 * @param {Function} props.onFocusActive - Pan/zoom to the active match
 * @param {Function} props.onClose - Close the search bar
 */
export default function BoardSearch({
  query, setQuery, filterType, setFilterType,
  matchCount, activeIndex, onNext, onPrev, onFocusActive, onClose,
}) {
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown' || (e.key === 'Enter' && !e.shiftKey)) {
      e.preventDefault();
      onNext();
      onFocusActive();
    } else if (e.key === 'ArrowUp' || (e.key === 'Enter' && e.shiftKey)) {
      e.preventDefault();
      onPrev();
      onFocusActive();
    }
  };

  return (
    <div className="board-search">
      <div className="board-search__inner">
        <svg className="board-search__icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
        <input
          ref={inputRef}
          className="board-search__input"
          type="text"
          placeholder="Search cards..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <select
          className="board-search__filter"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          {CARD_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        {matchCount > 0 && (
          <div className="board-search__nav">
            <span className="board-search__count">
              {activeIndex + 1} / {matchCount}
            </span>
            <button className="board-search__nav-btn" onClick={() => { onPrev(); onFocusActive(); }} title="Previous (Shift+Enter)">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 15l-6-6-6 6" /></svg>
            </button>
            <button className="board-search__nav-btn" onClick={() => { onNext(); onFocusActive(); }} title="Next (Enter)">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 9l6 6 6-6" /></svg>
            </button>
          </div>
        )}
        {query.trim() && matchCount === 0 && (
          <span className="board-search__count board-search__count--empty">No matches</span>
        )}
        <button className="board-search__close" onClick={onClose} title="Close (Esc)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
