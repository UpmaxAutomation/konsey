import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { listBoards, listCards } from '../../api/boards.js';
import './styles/CommandPalette.css';

const RECENT_KEY = 'llm-council-cmd-recent';
const MAX_RECENT = 10;

const ACTIONS = [
  { id: 'new-board', label: 'Create New Board', category: 'Actions', icon: '\u2795', action: 'create-board' },
  { id: 'open-boards', label: 'Open Boards', category: 'Actions', icon: '\uD83D\uDCCB', action: 'navigate', path: '/boards' },
  { id: 'open-chat', label: 'Open Chat', category: 'Actions', icon: '\uD83D\uDCAC', action: 'navigate', path: '/' },
  { id: 'open-journal', label: 'Open Journal', category: 'Actions', icon: '\uD83D\uDCD3', action: 'dispatch', event: 'openJournal' },
  { id: 'open-inbox', label: 'Open Inbox', category: 'Actions', icon: '\uD83D\uDCE5', action: 'dispatch', event: 'openInbox' },
  { id: 'run-council', label: 'Run Council', category: 'Actions', icon: '\uD83E\uDDD1\u200D\u2696\uFE0F', action: 'navigate', path: '/' },
];

/** Score a candidate string against a query. Higher = better match. Returns 0 for no match. */
function fuzzyScore(text, query) {
  if (!query) return 1;
  const t = text.toLowerCase();
  const q = query.toLowerCase();

  // Exact match
  if (t === q) return 100;

  // Starts with query
  if (t.startsWith(q)) return 80;

  // Word-boundary match (e.g. "nb" matches "New Board")
  const words = t.split(/[\s\-_]+/);
  const initials = words.map((w) => w[0]).join('');
  if (initials.includes(q)) return 60;

  // Any word starts with query
  if (words.some((w) => w.startsWith(q))) return 50;

  // Substring match
  if (t.includes(q)) return 30;

  // Character-by-character fuzzy
  let qi = 0;
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) qi++;
  }
  if (qi === q.length) return 10;

  return 0;
}

function getRecentItems() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
  } catch { return []; }
}

function addRecentItem(item) {
  const recent = getRecentItems().filter((r) => r.id !== item.id);
  recent.unshift({ id: item.id, label: item.label, type: item.type, icon: item.icon, path: item.path, boardName: item.boardName });
  localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, MAX_RECENT)));
}

export default function CommandPalette({ isOpen, onClose }) {
  const [query, setQuery] = useState('');
  const [boards, setBoards] = useState([]);
  const [cards, setCards] = useState([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const navigate = useNavigate();

  // Load boards + cards when opened
  useEffect(() => {
    if (!isOpen) return;
    setQuery('');
    setActiveIndex(0);

    listBoards()
      .then(async (data) => {
        const boardList = data.boards || [];
        setBoards(boardList);

        // Fetch cards from all boards in parallel (max 20 boards)
        const cardPromises = boardList.slice(0, 20).map((b) =>
          listCards(b.id)
            .then((d) => (d.cards || []).map((c) => ({ ...c, boardName: b.name, boardId: b.id })))
            .catch(() => [])
        );
        const allCards = (await Promise.all(cardPromises)).flat();
        setCards(allCards);
      })
      .catch(() => { setBoards([]); setCards([]); });

    requestAnimationFrame(() => inputRef.current?.focus());
  }, [isOpen]);

  // Build search results
  const results = useMemo(() => {
    const q = query.trim();

    // If no query, show recent items then actions
    if (!q) {
      const recent = getRecentItems();
      const items = [];
      if (recent.length > 0) {
        recent.forEach((r) => items.push({ ...r, category: 'Recent' }));
      }
      ACTIONS.forEach((a) => items.push({ type: 'action', ...a }));
      boards.slice(0, 8).forEach((b) =>
        items.push({
          type: 'board',
          id: b.id,
          label: b.name,
          category: 'Boards',
          icon: b.icon || '\uD83D\uDCCB',
          path: `/boards/${b.id}`,
        })
      );
      return items;
    }

    // Score and collect all items
    const scored = [];

    ACTIONS.forEach((a) => {
      const s = fuzzyScore(a.label, q);
      if (s > 0) scored.push({ type: 'action', ...a, category: 'Actions', _score: s });
    });

    boards.forEach((b) => {
      const s = fuzzyScore(b.name, q);
      if (s > 0) scored.push({
        type: 'board',
        id: b.id,
        label: b.name,
        category: 'Boards',
        icon: b.icon || '\uD83D\uDCCB',
        path: `/boards/${b.id}`,
        _score: s,
      });
    });

    cards.forEach((c) => {
      const titleScore = fuzzyScore(c.title || '', q);
      const contentScore = fuzzyScore((c.content || '').slice(0, 200), q) * 0.5;
      const s = Math.max(titleScore, contentScore);
      if (s > 0) scored.push({
        type: 'card',
        id: c.id,
        label: c.title || 'Untitled card',
        category: 'Cards',
        icon: '\uD83D\uDCC4',
        path: `/boards/${c.boardId}`,
        boardName: c.boardName,
        _score: s,
      });
    });

    // Sort by score descending, limit to 20
    scored.sort((a, b) => b._score - a._score);
    return scored.slice(0, 20);
  }, [query, boards, cards]);

  // Keep activeIndex in bounds
  useEffect(() => {
    if (activeIndex >= results.length) setActiveIndex(Math.max(0, results.length - 1));
  }, [results.length, activeIndex]);

  // Handle selection
  const handleSelect = useCallback(
    (item) => {
      // Track in recent items
      addRecentItem(item);
      onClose();

      if (item.action === 'create-board') {
        navigate('/boards');
        return;
      }
      if (item.action === 'dispatch' && item.event) {
        window.dispatchEvent(new CustomEvent(item.event));
        return;
      }
      if (item.path) {
        navigate(item.path);
      }
    },
    [navigate, onClose]
  );

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && results[activeIndex]) {
        e.preventDefault();
        handleSelect(results[activeIndex]);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    },
    [results, activeIndex, handleSelect, onClose]
  );

  // Scroll active item into view
  useEffect(() => {
    const el = listRef.current?.children[activeIndex];
    el?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  if (!isOpen) return null;

  // Group results by category
  let lastCategory = '';

  return (
    <>
      <div className="command-palette__overlay" onClick={onClose} />
      <div className="command-palette" role="dialog" aria-label="Command palette">
        <div className="command-palette__header">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            ref={inputRef}
            className="command-palette__input"
            type="text"
            placeholder="Search boards, cards, actions..."
            value={query}
            onChange={(e) => { setQuery(e.target.value); setActiveIndex(0); }}
            onKeyDown={handleKeyDown}
            aria-label="Search"
          />
          <kbd className="command-palette__kbd">ESC</kbd>
        </div>

        <div className="command-palette__results" ref={listRef}>
          {results.length === 0 && (
            <div className="command-palette__empty">No results found</div>
          )}
          {results.map((item, i) => {
            const showCategory = item.category !== lastCategory;
            lastCategory = item.category;
            return (
              <div key={`${item.type}-${item.id}`}>
                {showCategory && (
                  <div className="command-palette__category">{item.category}</div>
                )}
                <button
                  className={`command-palette__item ${i === activeIndex ? 'command-palette__item--active' : ''}`}
                  onClick={() => handleSelect(item)}
                  onMouseEnter={() => setActiveIndex(i)}
                >
                  <span className="command-palette__item-icon">{item.icon}</span>
                  <span className="command-palette__item-label">{item.label}</span>
                  {item.boardName && (
                    <span className="command-palette__item-badge">{item.boardName}</span>
                  )}
                  {item.type === 'board' && !item.boardName && (
                    <span className="command-palette__item-hint">Board</span>
                  )}
                  {item.type === 'card' && !item.boardName && (
                    <span className="command-palette__item-hint">Card</span>
                  )}
                </button>
              </div>
            );
          })}
        </div>

        <div className="command-palette__footer">
          <span><kbd>&uarr;&darr;</kbd> Navigate</span>
          <span><kbd>&crarr;</kbd> Select</span>
          <span><kbd>esc</kbd> Close</span>
        </div>
      </div>
    </>
  );
}
