/**
 * Properties API module.
 */

import { API_BASE, authFetch } from './client.js';

// ── Property Definitions ──────────────────────

export async function listPropertyDefinitions(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/properties`);
  if (!response.ok) throw new Error('Failed to list property definitions');
  return response.json();
}

export async function createPropertyDefinition(boardId, data) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/properties`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create property definition');
  return response.json();
}

export async function updatePropertyDefinition(boardId, propId, updates) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/properties/${propId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error('Failed to update property definition');
  return response.json();
}

export async function deletePropertyDefinition(boardId, propId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/properties/${propId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete property definition');
  return response.json();
}

// ── Card Property Values ──────────────────────

export async function getCardProperties(boardId, cardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/${cardId}/properties`);
  if (!response.ok) throw new Error('Failed to get card properties');
  return response.json();
}

export async function bulkSetCardProperties(boardId, cardId, values) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/${cardId}/properties`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ values }),
  });
  if (!response.ok) throw new Error('Failed to set card properties');
  return response.json();
}

export async function getAllPropertyValues(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/properties/all-values`);
  if (!response.ok) throw new Error('Failed to get all property values');
  return response.json();
}
