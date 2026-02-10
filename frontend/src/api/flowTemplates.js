import { API_BASE, authFetch } from './client.js';

export async function listUserTemplates(projectId = null) {
  const params = projectId ? `?project_id=${projectId}` : '';
  const res = await authFetch(`${API_BASE}/flow-templates${params}`);
  if (!res.ok) throw new Error('Failed to list user templates');
  return res.json();
}

export async function createFlowTemplate(data) {
  const res = await authFetch(`${API_BASE}/flow-templates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create template');
  return res.json();
}

export async function getFlowTemplate(templateId) {
  const res = await authFetch(`${API_BASE}/flow-templates/${templateId}`);
  if (!res.ok) throw new Error('Failed to get template');
  return res.json();
}

export async function updateFlowTemplate(templateId, data) {
  const res = await authFetch(`${API_BASE}/flow-templates/${templateId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update template');
  return res.json();
}

export async function deleteFlowTemplate(templateId) {
  const res = await authFetch(`${API_BASE}/flow-templates/${templateId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete template');
  return res.json();
}

export async function createWorkflowFromUserTemplate(boardId, templateId) {
  const res = await authFetch(`${API_BASE}/flow-templates/from-user-template/${templateId}/boards/${boardId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to create workflow from template');
  return res.json();
}

export async function listWorkflowRuns(boardId, workflowId) {
  const res = await authFetch(`${API_BASE}/boards/${boardId}/workflows/${workflowId}/runs`);
  if (!res.ok) throw new Error('Failed to list workflow runs');
  return res.json();
}
