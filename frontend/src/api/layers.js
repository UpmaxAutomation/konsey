/**
 * Knowledge Layers API module.
 */

import { API_BASE, authFetch } from './client.js';

// -- Layer CRUD ──────────────────────────────

export async function createLayer(data) {
  const response = await authFetch(`${API_BASE}/layers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create layer');
  return response.json();
}

export async function listLayers(projectId) {
  const response = await authFetch(`${API_BASE}/layers/project/${projectId}`);
  if (!response.ok) throw new Error('Failed to list layers');
  return response.json();
}

export async function getLayer(layerId) {
  const response = await authFetch(`${API_BASE}/layers/${layerId}`);
  if (!response.ok) throw new Error('Failed to get layer');
  return response.json();
}

export async function updateLayer(layerId, data) {
  const response = await authFetch(`${API_BASE}/layers/${layerId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update layer');
  return response.json();
}

export async function deleteLayer(layerId) {
  const response = await authFetch(`${API_BASE}/layers/${layerId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete layer');
  return response.json();
}

// -- Layer Operations ──────────────────────────────

export async function assignDocuments(layerId, documentIds) {
  const response = await authFetch(`${API_BASE}/layers/${layerId}/assign-documents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds }),
  });
  if (!response.ok) throw new Error('Failed to assign documents to layer');
  return response.json();
}

export async function reorderLayers(projectId, layerIds) {
  const response = await authFetch(`${API_BASE}/layers/reorder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, layer_ids: layerIds }),
  });
  if (!response.ok) throw new Error('Failed to reorder layers');
  return response.json();
}
