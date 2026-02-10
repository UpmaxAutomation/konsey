import { authFetch, API_BASE } from './client.js';

export async function listSnapshots(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/snapshots`);
  if (!response.ok) throw new Error('Failed to list snapshots');
  return response.json();
}

export async function createSnapshot(boardId, data = {}) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/snapshots`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create snapshot');
  return response.json();
}

export async function getSnapshot(boardId, snapshotId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/snapshots/${snapshotId}`);
  if (!response.ok) throw new Error('Failed to get snapshot');
  return response.json();
}

export async function restoreSnapshot(boardId, snapshotId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/snapshots/${snapshotId}/restore`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to restore snapshot');
  return response.json();
}

export async function deleteSnapshot(boardId, snapshotId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/snapshots/${snapshotId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete snapshot');
  return response.json();
}
