/**
 * React Query hooks for card search and cross-board linking.
 */

import { useQuery, useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  searchCards,
  linkCard,
  cloneCard,
  unlinkCard,
  toggleLibrary,
  syncLinkedCard,
  getLinkedInstances,
} from '../cardSearch.js';
import { boardKeys } from './boardQueries.js';

export const cardSearchKeys = {
  all: ['cardSearch'],
  search: (filters) => ['cardSearch', filters],
  instances: (cardId) => ['cardSearch', 'instances', cardId],
};

const PAGE_SIZE = 20;

/**
 * Infinite query for searching cards across all boards.
 * Supports pagination via offset-based cursor.
 * @param {Object} filters - Search filters (q, card_type, tag_ids, is_library)
 * @param {Object} [options] - Additional react-query options
 * @returns {UseInfiniteQueryResult} Infinite query result with pages of cards
 */
export function useCardSearch(filters, options = {}) {
  return useInfiniteQuery({
    queryKey: cardSearchKeys.search(filters),
    queryFn: ({ pageParam = 0 }) =>
      searchCards({ ...filters, limit: PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, page) => sum + (page.cards?.length || 0), 0);
      if (loaded < (lastPage.total || 0)) {
        return loaded;
      }
      return undefined;
    },
    staleTime: 30_000,
    ...options,
  });
}

/**
 * Fetch all linked instances of a source card.
 * @param {string} cardId - Source card ID
 * @returns {UseQueryResult} Query result with linked instances
 */
export function useLinkedInstances(cardId) {
  return useQuery({
    queryKey: cardSearchKeys.instances(cardId),
    queryFn: () => getLinkedInstances(cardId),
    enabled: !!cardId,
    staleTime: 30_000,
  });
}

/**
 * Mutation to link a card onto another board.
 * Invalidates both the target board and the card search cache.
 * @returns {UseMutationResult} Mutation for linking cards
 */
export function useLinkCard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cardId, target_board_id, position_x, position_y }) =>
      linkCard(cardId, { target_board_id, position_x, position_y }),
    onSuccess: (data, { target_board_id }) => {
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(target_board_id) });
      queryClient.invalidateQueries({ queryKey: cardSearchKeys.all });
    },
  });
}

/**
 * Mutation to clone a card onto another board.
 * Invalidates both the target board and the card search cache.
 * @returns {UseMutationResult} Mutation for cloning cards
 */
export function useCloneCard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cardId, target_board_id, position_x, position_y }) =>
      cloneCard(cardId, { target_board_id, position_x, position_y }),
    onSuccess: (data, { target_board_id }) => {
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(target_board_id) });
      queryClient.invalidateQueries({ queryKey: cardSearchKeys.all });
    },
  });
}

/**
 * Mutation to unlink a linked card instance.
 * Invalidates card search and all board caches.
 * @returns {UseMutationResult} Mutation for unlinking cards
 */
export function useUnlinkCard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (cardId) => unlinkCard(cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cardSearchKeys.all });
      queryClient.invalidateQueries({ queryKey: boardKeys.all });
    },
  });
}

/**
 * Mutation to toggle a card's library status.
 * Invalidates card search cache to reflect the change.
 * @returns {UseMutationResult} Mutation for toggling library status
 */
export function useToggleLibrary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (cardId) => toggleLibrary(cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cardSearchKeys.all });
    },
  });
}

/**
 * Mutation to sync a linked card with its source.
 * Invalidates the card search and all board caches.
 * @returns {UseMutationResult} Mutation for syncing linked cards
 */
export function useSyncLinkedCard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (cardId) => syncLinkedCard(cardId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: cardSearchKeys.all });
      queryClient.invalidateQueries({ queryKey: boardKeys.all });
    },
  });
}
