import { useState, useEffect, useRef, useCallback } from 'react';
import './SearchModal.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';

export default function SearchModal({ isOpen, onClose, onSelectConversation }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [totalResults, setTotalResults] = useState(0);
  const inputRef = useRef(null);
  const resultsRef = useRef(null);

  // Debounced search
  useEffect(() => {
    if (!isOpen) return;

    const timer = setTimeout(() => {
      if (query.trim().length >= 2) {
        performSearch(query);
      } else {
        setResults([]);
        setTotalResults(0);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query, isOpen]);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setQuery('');
      setResults([]);
      setSelectedIndex(0);
      setTotalResults(0);
    }
  }, [isOpen]);

  const performSearch = async (searchQuery) => {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/search?q=${encodeURIComponent(searchQuery)}&limit=20`
      );
      const data = await response.json();
      setResults(data.results || []);
      setTotalResults(data.total || 0);
      setSelectedIndex(0);
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
      setTotalResults(0);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && results.length > 0) {
      e.preventDefault();
      handleSelectResult(results[selectedIndex]);
    }
  };

  const handleSelectResult = (result) => {
    onSelectConversation(result.conversation_id);
    onClose();
  };

  // Scroll selected item into view
  useEffect(() => {
    if (resultsRef.current && results.length > 0) {
      const selectedElement = resultsRef.current.querySelector(
        `.search-result-item:nth-child(${selectedIndex + 1})`
      );
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [selectedIndex, results]);

  const highlightMatch = (text) => {
    if (!text) return '';

    // Replace [[HIGHLIGHT]] and [[/HIGHLIGHT]] markers with HTML
    return text
      .replace(/\[\[HIGHLIGHT\]\]/g, '<mark>')
      .replace(/\[\[\/HIGHLIGHT\]\]/g, '</mark>');
  };

  if (!isOpen) return null;

  return (
    <div className="search-modal-overlay" onClick={onClose}>
      <div className="search-modal" onClick={(e) => e.stopPropagation()}>
        <div className="search-modal-header">
          <div className="search-input-container">
            <svg
              className="search-icon"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
            <input
              ref={inputRef}
              type="text"
              className="search-input"
              placeholder="Search conversations..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            {loading && <div className="search-loading-spinner"></div>}
          </div>
          <button className="search-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="search-results" ref={resultsRef}>
          {query.trim().length < 2 ? (
            <div className="search-empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
              <p>Type at least 2 characters to search</p>
              <div className="search-shortcuts">
                <kbd>↑</kbd> <kbd>↓</kbd> to navigate
                <span className="search-shortcuts-sep">•</span>
                <kbd>↵</kbd> to select
                <span className="search-shortcuts-sep">•</span>
                <kbd>Esc</kbd> to close
              </div>
            </div>
          ) : results.length === 0 && !loading ? (
            <div className="search-empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
              </svg>
              <p>No results found for "{query}"</p>
            </div>
          ) : (
            <>
              {totalResults > 0 && (
                <div className="search-results-count">
                  Found {totalResults} conversation{totalResults !== 1 ? 's' : ''}
                </div>
              )}
              {results.map((result, index) => (
                <div
                  key={result.conversation_id}
                  className={`search-result-item ${index === selectedIndex ? 'selected' : ''}`}
                  onClick={() => handleSelectResult(result)}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <div className="search-result-header">
                    <div className="search-result-title">{result.title}</div>
                    <div className="search-result-meta">
                      {result.match_count} match{result.match_count !== 1 ? 'es' : ''}
                    </div>
                  </div>
                  <div className="search-result-matches">
                    {result.matches.slice(0, 3).map((match, idx) => (
                      <div key={idx} className="search-result-match">
                        <div className="search-result-context">{match.context}</div>
                        <div
                          className="search-result-snippet"
                          dangerouslySetInnerHTML={{ __html: highlightMatch(match.snippet) }}
                        />
                      </div>
                    ))}
                    {result.matches.length > 3 && (
                      <div className="search-result-more">
                        +{result.matches.length - 3} more match{result.matches.length - 3 !== 1 ? 'es' : ''}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
