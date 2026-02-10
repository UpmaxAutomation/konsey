import { API_BASE } from './client.js';

export async function listAssets(projectId, { type, search, limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams();
  if (type) params.set('asset_type', type);
  if (search) params.set('search', search);
  params.set('limit', limit);
  params.set('offset', offset);
  const res = await fetch(`${API_BASE}/projects/${projectId}/assets?${params}`, {
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to list assets');
  return res.json();
}

export async function getAsset(id) {
  const res = await fetch(`${API_BASE}/assets/${id}`, { credentials: 'include' });
  if (!res.ok) throw new Error('Failed to get asset');
  return res.json();
}

export async function updateAsset(id, data) {
  const res = await fetch(`${API_BASE}/assets/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update asset');
  return res.json();
}

export async function deleteAsset(id) {
  const res = await fetch(`${API_BASE}/assets/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to delete asset');
  return res.json();
}

export async function createCardFromImage(projectId, imageId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/assets/from-image/${imageId}`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to create card from image');
  return res.json();
}
