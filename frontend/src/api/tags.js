/**
 * Tags API module.
 */

import { API_BASE, authFetch } from './client.js';

// ── Tag CRUD ──────────────────────────────

export async function listTags() {
  const response = await authFetch(`${API_BASE}/tags`);
  if (!response.ok) throw new Error('Failed to list tags');
  return response.json();
}

export async function createTag(data) {
  const response = await authFetch(`${API_BASE}/tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create tag');
  return response.json();
}

export async function updateTag(tagId, updates) {
  const response = await authFetch(`${API_BASE}/tags/${tagId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error('Failed to update tag');
  return response.json();
}

export async function deleteTag(tagId) {
  const response = await authFetch(`${API_BASE}/tags/${tagId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete tag');
  return response.json();
}

// ── Card-Tag ──────────────────────────────

export async function getCardTags(boardId, cardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/${cardId}/tags`);
  if (!response.ok) throw new Error('Failed to get card tags');
  return response.json();
}

export async function addCardTag(boardId, cardId, tagId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/${cardId}/tags`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tag_id: tagId }),
  });
  if (!response.ok) throw new Error('Failed to add tag to card');
  return response.json();
}

export async function removeCardTag(boardId, cardId, tagId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/${cardId}/tags/${tagId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to remove tag from card');
  return response.json();
}
