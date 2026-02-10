/**
 * Mentions API -- Card backlinks and mention graph endpoints.
 *
 * @module api/mentions
 */
import { authFetch, API_BASE, handleResponse } from './client.js';

/**
 * Get cards that mention a specific card via [[ links.
 * @param {string} boardId
 * @param {string} cardId
 * @returns {Promise<Array>} Array of backlink objects
 */
export async function getBacklinks(boardId, cardId) {
  return handleResponse(await authFetch(`${API_BASE}/boards/${boardId}/cards/${cardId}/backlinks`));
}

/**
 * Get the full mention graph for a board (all card-to-card links).
 * @param {string} boardId
 * @returns {Promise<Object>} Graph object with nodes and edges
 */
export async function getMentionGraph(boardId) {
  return handleResponse(await authFetch(`${API_BASE}/boards/${boardId}/mention-graph`));
}
