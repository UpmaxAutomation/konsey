import { useState, useMemo, useCallback } from 'react';

/**
 * Encapsulates board search logic: query filtering, type filtering,
 * and match navigation (next/prev with wraparound).
 *
 * @param {Array} nodes - ReactFlow nodes to search through
 * @returns {Object} Search state and controls
 */
export default function useBoardSearch(nodes) {
  const [query, setQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [activeIndex, setActiveIndex] = useState(0);

  const matches = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.toLowerCase();
    return nodes.filter((n) => {
      const matchesQuery =
        (n.data.title || '').toLowerCase().includes(q) ||
        (n.data.content || '').toLowerCase().includes(q);
      const matchesType = filterType === 'all' || n.data.card_type === filterType;
      return matchesQuery && matchesType;
    });
  }, [query, filterType, nodes]);

  const matchIds = useMemo(() => matches.map((n) => n.id), [matches]);

  const activeMatchId = matches[activeIndex]?.id || null;

  const goNext = useCallback(() => {
    setActiveIndex((i) => (matches.length > 0 ? (i + 1) % matches.length : 0));
  }, [matches.length]);

  const goPrev = useCallback(() => {
    setActiveIndex((i) => (matches.length > 0 ? (i - 1 + matches.length) % matches.length : 0));
  }, [matches.length]);

  const reset = useCallback(() => {
    setQuery('');
    setFilterType('all');
    setActiveIndex(0);
  }, []);

  return {
    query, setQuery,
    filterType, setFilterType,
    matches, matchIds,
    activeIndex, activeMatchId,
    goNext, goPrev, reset,
  };
}
