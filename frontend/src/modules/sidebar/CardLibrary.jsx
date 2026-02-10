import { useState, useEffect, useMemo } from 'react';
import { listBoards, listCards } from '../../api/boards.js';
import './styles/CardLibrary.css';

const CARD_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'note', label: 'Notes' },
  { value: 'knowledge', label: 'Knowledge' },
  { value: 'query', label: 'Queries' },
  { value: 'council_response', label: 'Responses' },
  { value: 'council_synthesis', label: 'Syntheses' },
  { value: 'link', label: 'Links' },
  { value: 'file_ref', label: 'Files' },
  { value: 'board_ref', label: 'Boards' },
];

export default function CardLibrary({ onNavigateToCard }) {
  const [cards, setCards] = useState([]);
  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('');

  useEffect(() => {
    async function loadAll() {
      try {
        const boardsData = await listBoards();
        const allBoards = boardsData.boards || [];
        setBoards(allBoards);

        // Load cards from each board (in parallel, max 10)
        const allCards = [];
        const batches = [];
        for (let i = 0; i < Math.min(allBoards.length, 10); i++) {
          batches.push(
            listCards(allBoards[i].id)
              .then((data) => {
                (data.cards || []).forEach((c) => {
                  allCards.push({ ...c, boardName: allBoards[i].name });
                });
              })
              .catch(() => {})
          );
        }
        await Promise.all(batches);
        setCards(allCards);
      } catch (err) {
        console.error('Failed to load cards:', err);
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, []);

  const boardMap = useMemo(() => {
    const m = new Map();
    boards.forEach((b) => m.set(b.id, b));
    return m;
  }, [boards]);

  const filtered = useMemo(() => {
    let result = cards;
    if (filterType) {
      result = result.filter((c) => c.card_type === filterType);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (c) =>
          c.title?.toLowerCase().includes(q) ||
          c.content?.toLowerCase().includes(q)
      );
    }
    return result.slice(0, 100);
  }, [cards, filterType, search]);

  if (loading) {
    return <div className="card-library__loading">Loading cards...</div>;
  }

  return (
    <div className="card-library">
      <div className="card-library__controls">
        <input
          type="text"
          className="card-library__search"
          placeholder="Search cards..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="card-library__filter"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          {CARD_TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div className="card-library__count">{filtered.length} card{filtered.length !== 1 ? 's' : ''}</div>

      <div className="card-library__list">
        {filtered.map((card) => (
          <button
            key={card.id}
            className="card-library__item"
            onClick={() => onNavigateToCard?.(card.board_id, card.id)}
          >
            <span className="card-library__item-type">{card.card_type}</span>
            <span className="card-library__item-title">{card.title || card.content?.slice(0, 60) || 'Untitled'}</span>
            <span className="card-library__item-board">{card.boardName || 'Unknown'}</span>
          </button>
        ))}
        {filtered.length === 0 && (
          <div className="card-library__empty">No cards found</div>
        )}
      </div>
    </div>
  );
}
