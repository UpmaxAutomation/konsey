/**
 * Tools API - Web search, code execution, memory.
 */

import { API_BASE, authFetch } from './client.js';

// ============ CODE INTERPRETER ============

/**
 * Execute Python code in sandboxed environment.
 * @param {string} code - Python code to execute
 * @param {number} timeout - Timeout in seconds
 */
export async function executeCode(code, timeout = 30) {
  const response = await authFetch(`${API_BASE}/interpreter/execute`, {
    method: 'POST',
    body: JSON.stringify({ code, timeout }),
  });
  if (!response.ok) {
    throw new Error('Failed to execute code');
  }
  return response.json();
}

// ============ MEMORY API ============

/**
 * Get memory context.
 */
export async function getMemoryContext() {
  const response = await fetch(`${API_BASE}/tools/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'get_context' }),
  });
  if (!response.ok) {
    throw new Error('Failed to get memory');
  }
  return response.json();
}

/**
 * Get memory statistics.
 */
export async function getMemoryStats() {
  const response = await fetch(`${API_BASE}/tools/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'stats' }),
  });
  if (!response.ok) {
    throw new Error('Failed to get memory stats');
  }
  return response.json();
}

/**
 * Clear all memory.
 */
export async function clearMemory() {
  const response = await fetch(`${API_BASE}/tools/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'clear' }),
  });
  if (!response.ok) {
    throw new Error('Failed to clear memory');
  }
  return response.json();
}

/**
 * Remember a fact.
 * @param {string} content - The fact to remember
 * @param {string} category - Category for organization
 */
export async function rememberFact(content, category = 'general') {
  const response = await fetch(`${API_BASE}/tools/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'remember_fact', content, category }),
  });
  if (!response.ok) {
    throw new Error('Failed to remember fact');
  }
  return response.json();
}

/**
 * Set a user preference.
 * @param {string} key - Preference key
 * @param {any} value - Preference value
 */
export async function setPreference(key, value) {
  const response = await fetch(`${API_BASE}/tools/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'set_preference', key, value }),
  });
  if (!response.ok) {
    throw new Error('Failed to set preference');
  }
  return response.json();
}

// ============ SEARCH API ============

/**
 * Search across all conversations.
 * @param {Object} params - Search parameters
 * @param {string} params.query - Search query string
 * @param {string} params.folder - Filter by folder/project ID (optional)
 * @param {Array<string>} params.tags - Filter by tags (optional)
 * @param {string} params.from_date - Filter conversations created after this date (ISO format, optional)
 * @param {string} params.to_date - Filter conversations created before this date (ISO format, optional)
 * @param {number} params.limit - Maximum number of results (default: 50)
 * @param {number} params.offset - Pagination offset (default: 0)
 * @returns {Promise<Object>} Search results with matches and metadata
 */
export async function searchConversations({ query, folder, tags, from_date, to_date, limit = 50, offset = 0 }) {
  const params = new URLSearchParams();
  params.append('q', query);

  if (folder) params.append('folder', folder);
  if (tags && tags.length > 0) params.append('tags', tags.join(','));
  if (from_date) params.append('from_date', from_date);
  if (to_date) params.append('to_date', to_date);
  if (limit) params.append('limit', limit.toString());
  if (offset) params.append('offset', offset.toString());

  const response = await fetch(`${API_BASE}/search?${params.toString()}`);
  if (!response.ok) {
    throw new Error('Failed to search conversations');
  }
  return response.json();
}

/**
 * Get search suggestions based on query prefix.
 * @param {string} query - Partial search query
 * @param {number} limit - Maximum number of suggestions (default: 5)
 * @returns {Promise<Object>} List of suggested search terms
 */
export async function getSearchSuggestions(query, limit = 5) {
  const params = new URLSearchParams();
  params.append('q', query);
  params.append('limit', limit.toString());

  const response = await fetch(`${API_BASE}/search/suggestions?${params.toString()}`);
  if (!response.ok) {
    throw new Error('Failed to get search suggestions');
  }
  return response.json();
}
