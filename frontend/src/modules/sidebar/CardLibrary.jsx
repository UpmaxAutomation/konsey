import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { useCardSearch, useToggleLibrary } from '../../api/queries/cardSearchQueries.js';
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
  { value: 'linked_card', label: 'Linked' },
];

/**
 * Global Card Library sidebar panel.
 * Provides full-text search, type/library filtering, infinite scroll,
 * drag-to-board linking, and per-card action buttons.
 */
export default function CardLibrary({ onNavigateToCard }) {
  const [searchText, setSearchText] = useState('');
  const [filterType, setFilterType] = useState('');
  const [libraryOnly, setLibraryOnly] = useState(false);
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const sentinelRef = useRef(null);
  const listRef = useRef(null);

  // Debounce search input to avoid excessive API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchText.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [searchText]);

  // Build filter object for the query
  const filters = useMemo(() => {
    const f = {};
    if (debouncedSearch) f.q = debouncedSearch;
    if (filterType) f.card_type = filterType;
    if (libraryOnly) f.is_library = true;
    return f;
  }, [debouncedSearch, filterType, libraryOnly]);

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    isError,
  } = useCardSearch(filters);

  const toggleLibraryMutation = useToggleLibrary();

  // Flatten pages into a single card list
  const cards = useMemo(() => {
    if (!data?.pages) return [];
    return data.pages.flatMap((page) => page.cards || []);
  }, [data]);

  const totalCount = data?.pages?.[0]?.total ?? 0;

  // IntersectionObserver for infinite scroll sentinel
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { root: listRef.current, rootMargin: '100px', threshold: 0 }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Drag start handler: encode card data for cross-board linking
  const handleDragStart = useCallback((e, card) => {
    const payload = JSON.stringify({
      sourceCardId: card.id,
      action: 'link',
      title: card.title || '',
      card_type: card.card_type || 'note',
    });
    e.dataTransfer.setData('application/x-council-card', payload);
    e.dataTransfer.setData('text/plain', card.title || card.content?.slice(0, 80) || 'Card');
    e.dataTransfer.effectAllowed = 'copyLink';
  }, []);

  const handleToggleLibrary = useCallback(
    (e, cardId) => {
      e.stopPropagation();
      toggleLibraryMutation.mutate(cardId);
    },
    [toggleLibraryMutation]
  );

  const handleSearchKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      setSearchText('');
    }
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="card-library">
        <div className="card-library__loading" role="status" aria-live="polite">
          <div className="card-library__spinner" aria-hidden="true" />
          Loading cards...
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="card-library">
        <div className="card-library__error" role="alert">
          Failed to load cards. The search endpoint may not be available yet.
        </div>
      </div>
    );
  }

  return (
    <div className="card-library">
      {/* Search input */}
      <div className="card-library__controls">
        <div className="card-library__search-wrapper">
          <svg
            className="card-library__search-icon"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="card-library__search"
            placeholder="Search all cards..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            aria-label="Search cards"
          />
          {searchText && (
            <button
              className="card-library__search-clear"
              onClick={() => setSearchText('')}
              aria-label="Clear search"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>

        {/* Filter row */}
        <div className="card-library__filters">
          <select
            className="card-library__filter"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            aria-label="Filter by card type"
          >
            {CARD_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <button
            className={`card-library__library-toggle${libraryOnly ? ' card-library__library-toggle--active' : ''}`}
            onClick={() => setLibraryOnly((prev) => !prev)}
            title={libraryOnly ? 'Showing library cards only' : 'Show all cards'}
            aria-label={libraryOnly ? 'Showing library cards only, click to show all' : 'Click to show library cards only'}
            aria-pressed={libraryOnly}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill={libraryOnly ? 'currentColor' : 'none'}
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            Library
          </button>
        </div>
      </div>

      {/* Result count */}
      <div className="card-library__count" aria-live="polite">
        {totalCount} card{totalCount !== 1 ? 's' : ''}
        {debouncedSearch && ` matching "${debouncedSearch}"`}
        {libraryOnly && ' in library'}
      </div>

      {/* Card list with infinite scroll */}
      <div className="card-library__list" ref={listRef} role="list" aria-label="Card search results">
        {cards.map((card) => (
          <div
            key={card.id}
            className="card-library__item"
            role="listitem"
            draggable
            onDragStart={(e) => handleDragStart(e, card)}
            onClick={() => onNavigateToCard?.(card.board_id, card.id)}
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onNavigateToCard?.(card.board_id, card.id);
              }
            }}
          >
            <div className="card-library__item-header">
              <span className="card-library__item-type" data-type={card.card_type}>
                {card.card_type?.replace(/_/g, ' ') || 'note'}
              </span>
              <button
                className={`card-library__item-star${card.is_library ? ' card-library__item-star--active' : ''}`}
                onClick={(e) => handleToggleLibrary(e, card.id)}
                title={card.is_library ? 'Remove from library' : 'Add to library'}
                aria-label={card.is_library ? 'Remove from library' : 'Add to library'}
                aria-pressed={!!card.is_library}
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill={card.is_library ? 'currentColor' : 'none'}
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
              </button>
            </div>

            <span className="card-library__item-title">
              {card.title || card.content?.slice(0, 60) || 'Untitled'}
            </span>

            {card.board_name && (
              <span className="card-library__item-board">
                <svg
                  width="10"
                  height="10"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <rect x="3" y="3" width="7" height="7" />
                  <rect x="14" y="3" width="7" height="7" />
                  <rect x="3" y="14" width="7" height="7" />
                  <rect x="14" y="14" width="7" height="7" />
                </svg>
                {card.board_name}
              </span>
            )}

            <div className="card-library__item-actions">
              <button
                className="card-library__item-action"
                onClick={(e) => {
                  e.stopPropagation();
                  onNavigateToCard?.(card.board_id, card.id);
                }}
                title="Go to card on its board"
                aria-label={`Navigate to card: ${card.title || 'Untitled'}`}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                Open
              </button>
            </div>
          </div>
        ))}

        {/* Infinite scroll sentinel */}
        <div ref={sentinelRef} className="card-library__sentinel" aria-hidden="true" />

        {/* Loading more indicator */}
        {isFetchingNextPage && (
          <div className="card-library__loading-more" role="status" aria-live="polite">
            <div className="card-library__spinner card-library__spinner--small" aria-hidden="true" />
            Loading more...
          </div>
        )}

        {/* Empty state */}
        {!isLoading && cards.length === 0 && (
          <div className="card-library__empty" role="status">
            <svg
              className="card-library__empty-icon"
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <span className="card-library__empty-text">
              {debouncedSearch
                ? `No cards found for "${debouncedSearch}"`
                : libraryOnly
                  ? 'No library cards yet. Star cards to add them.'
                  : 'No cards found'}
            </span>
            {(debouncedSearch || filterType || libraryOnly) && (
              <button
                className="card-library__empty-reset"
                onClick={() => {
                  setSearchText('');
                  setFilterType('');
                  setLibraryOnly(false);
                }}
              >
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
