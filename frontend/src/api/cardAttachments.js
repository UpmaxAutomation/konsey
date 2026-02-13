/**
 * Card Attachments API module.
 */

import { API_BASE, authFetch } from './client.js';

export async function uploadAttachment(cardId, file) {
  const formData = new FormData();
  formData.append('file', file);
  const response = await authFetch(`${API_BASE}/cards/${cardId}/attachments/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Failed to upload attachment');
  return response.json();
}

export async function addEmbed(cardId, url, title) {
  const response = await authFetch(`${API_BASE}/cards/${cardId}/attachments/embed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, title }),
  });
  if (!response.ok) throw new Error('Failed to add embed');
  return response.json();
}

export async function listAttachments(cardId) {
  const response = await authFetch(`${API_BASE}/cards/${cardId}/attachments`);
  if (!response.ok) throw new Error('Failed to list attachments');
  return response.json();
}

export async function deleteAttachment(id) {
  const response = await authFetch(`${API_BASE}/attachments/${id}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete attachment');
  return { ok: true };
}
