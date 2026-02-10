/**
 * React Query hooks for card mentions and backlinks.
 *
 * @module api/queries/mentionQueries
 */
import { useQuery } from '@tanstack/react-query';
import { getBacklinks, getMentionGraph } from '../mentions.js';

/**
 * Fetch backlinks (cards that mention a specific card via [[ links).
 * @param {string} boardId
 * @param {string} cardId
 * @returns {import('@tanstack/react-query').UseQueryResult}
 */
export function useBacklinks(boardId, cardId) {
  return useQuery({
    queryKey: ['backlinks', boardId, cardId],
    queryFn: () => getBacklinks(boardId, cardId),
    enabled: !!boardId && !!cardId,
    staleTime: 30_000,
  });
}

/**
 * Fetch the full mention graph for a board.
 * @param {string} boardId
 * @returns {import('@tanstack/react-query').UseQueryResult}
 */
export function useMentionGraph(boardId) {
  return useQuery({
    queryKey: ['mention-graph', boardId],
    queryFn: () => getMentionGraph(boardId),
    enabled: !!boardId,
    staleTime: 60_000,
  });
}
