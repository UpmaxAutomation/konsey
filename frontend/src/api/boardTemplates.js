/**
 * Board template and marketplace API module.
 */

import { API_BASE, authFetch } from './client.js';

export async function saveBoardAsTemplate(templateData) {
  const res = await authFetch(`${API_BASE}/board-templates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(templateData),
  });
  if (!res.ok) throw new Error('Failed to save template');
  return res.json();
}

export async function listBoardTemplates({ search, category, publicOnly, limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (category) params.set('category', category);
  if (publicOnly) params.set('public_only', 'true');
  params.set('limit', limit);
  params.set('offset', offset);
  const res = await authFetch(`${API_BASE}/board-templates?${params}`);
  if (!res.ok) throw new Error('Failed to list templates');
  return res.json();
}

export async function getBoardTemplate(id) {
  const res = await authFetch(`${API_BASE}/board-templates/${id}`);
  if (!res.ok) throw new Error('Failed to get template');
  return res.json();
}

export async function applyBoardTemplate(templateId, boardId) {
  const res = await authFetch(`${API_BASE}/board-templates/${templateId}/apply/${boardId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to apply template');
  return res.json();
}

export async function deleteBoardTemplate(id) {
  const res = await authFetch(`${API_BASE}/board-templates/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete template');
  return res.json();
}

export async function rateTemplate(type, id, rating, review) {
  const res = await authFetch(`${API_BASE}/templates/${type}/${id}/rate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rating, review }),
  });
  if (!res.ok) throw new Error('Failed to rate template');
  return res.json();
}

export async function getTemplateRatings(type, id) {
  const res = await authFetch(`${API_BASE}/templates/${type}/${id}/ratings`);
  if (!res.ok) throw new Error('Failed to get ratings');
  return res.json();
}

export async function getMarketplace({ search, category, type, limit = 20, offset = 0 } = {}) {
  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (category) params.set('category', category);
  if (type) params.set('template_type', type);
  params.set('limit', limit);
  params.set('offset', offset);
  const res = await authFetch(`${API_BASE}/marketplace?${params}`);
  if (!res.ok) throw new Error('Failed to get marketplace');
  return res.json();
}
