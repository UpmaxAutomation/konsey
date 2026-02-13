/**
 * Card Search & Cross-Board Linking API module.
 */

import { API_BASE, authFetch } from './client.js';

// ── Card Search ──────────────────────────────

/**
 * Search cards across all boards with filters.
 * @param {Object} params - Search parameters
 * @param {string} [params.q] - Full-text search query
 * @param {string} [params.card_type] - Filter by card type
 * @param {string[]} [params.tag_ids] - Filter by tag IDs
 * @param {boolean} [params.is_library] - Filter library cards only
 * @param {number} [params.limit] - Page size (default 20)
 * @param {number} [params.offset] - Pagination offset
 * @returns {Promise<{cards: Array, total: number}>} Search results
 */
export async function searchCards({ q, card_type, tag_ids, is_library, limit = 20, offset = 0 }) {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (card_type) params.set('card_type', card_type);
  if (tag_ids?.length) params.set('tag_ids', tag_ids.join(','));
  if (is_library !== undefined) params.set('is_library', String(is_library));
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  const response = await authFetch(`${API_BASE}/cards/search?${params}`);
  if (!response.ok) throw new Error('Failed to search cards');
  return response.json();
}

// ── Cross-Board Card Linking ──────────────────────────────

/**
 * Link a card to another board (creates a linked_card reference).
 * @param {string} cardId - Source card ID to link from
 * @param {Object} params - Link parameters
 * @param {string} params.target_board_id - Destination board ID
 * @param {number} [params.position_x] - X position on target board
 * @param {number} [params.position_y] - Y position on target board
 * @returns {Promise<Object>} The newly created linked card
 */
export async function linkCard(cardId, { target_board_id, position_x = 100, position_y = 100 }) {
  const response = await authFetch(`${API_BASE}/cards/${cardId}/link`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_board_id, position_x, position_y }),
  });
  if (!response.ok) throw new Error('Failed to link card');
  return response.json();
}

/**
 * Clone a card to another board (creates an independent copy).
 * @param {string} cardId - Source card ID to clone
 * @param {Object} params - Clone parameters
 * @param {string} params.target_board_id - Destination board ID
 * @param {number} [params.position_x] - X position on target board
 * @param {number} [params.position_y] - Y position on target board
 * @returns {Promise<Object>} The newly created cloned card
 */
export async function cloneCard(cardId, { target_board_id, position_x = 100, position_y = 100 }) {
  const response = await authFetch(`${API_BASE}/cards/${cardId}/clone`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_board_id, position_x, position_y }),
  });
  if (!response.ok) throw new Error('Failed to clone card');
  return response.json();
}

/**
 * Unlink a linked card (removes the linked instance, not the source).
 * @param {string} cardId - The linked card instance to remove
 * @returns {Promise<Object>} Confirmation result
 */
export async function unlinkCard(cardId) {
  const response = await authFetch(`${API_BASE}/cards/${cardId}/unlink`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to unlink card');
  return response.json();
}

// ── Global Card Library ──────────────────────────────

/**
 * Toggle a card's library status (add/remove from global library).
 * @param {string} cardId - Card ID to toggle
 * @returns {Promise<Object>} Updated card with new is_library value
 */
export async function toggleLibrary(cardId) {
  const response = await authFetch(`${API_BASE}/cards/${cardId}/library`, {
    method: 'PATCH',
  });
  if (!response.ok) throw new Error('Failed to toggle library status');
  return response.json();
}

/**
 * Sync a linked card with its source (pull latest content).
 * @param {string} cardId - The linked card instance to sync
 * @returns {Promise<Object>} Updated linked card with synced content
 */
export async function syncLinkedCard(cardId) {
  const response = await authFetch(`${API_BASE}/cards/${cardId}/sync`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to sync linked card');
  return response.json();
}

/**
 * Get all linked instances of a source card across boards.
 * @param {string} cardId - Source card ID
 * @returns {Promise<{instances: Array}>} List of linked card instances
 */
export async function getLinkedInstances(cardId) {
  const response = await authFetch(`${API_BASE}/cards/${cardId}/instances`);
  if (!response.ok) throw new Error('Failed to get linked instances');
  return response.json();
}
