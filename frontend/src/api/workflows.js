/**
 * Workflow API module.
 */

import { API_BASE, authFetch } from './client.js';

// ── Workflow CRUD ──────────────────────────────

export async function listWorkflows(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/workflows`);
  if (!response.ok) throw new Error('Failed to list workflows');
  return response.json();
}

export async function createWorkflow(boardId, data) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/workflows`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create workflow');
  return response.json();
}

export async function getWorkflow(boardId, workflowId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/workflows/${workflowId}`);
  if (!response.ok) throw new Error('Failed to get workflow');
  return response.json();
}

export async function deleteWorkflow(boardId, workflowId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/workflows/${workflowId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete workflow');
  return response.json();
}

// ── Workflow Execution ──────────────────────────

export async function runWorkflow(boardId, workflowId, { initialInput = '', contextCardIds = [] } = {}, onEvent) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/workflows/${workflowId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ initial_input: initialInput, context_card_ids: contextCardIds }),
  });

  if (!response.ok) throw new Error('Failed to run workflow');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const event = JSON.parse(line.slice(6));
          onEvent?.(event);
        } catch { /* skip malformed */ }
      }
    }
  }
}

export async function approveWorkflowStep(boardId, workflowId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/workflows/${workflowId}/approve`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to approve step');
  return response.json();
}

export async function cancelWorkflow(boardId, workflowId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/workflows/${workflowId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to cancel workflow');
  return response.json();
}

// ── Templates ──────────────────────────────

export async function listTemplates() {
  const response = await authFetch(`${API_BASE}/workflow-templates`);
  if (!response.ok) throw new Error('Failed to list templates');
  return response.json();
}

export async function createFromTemplate(boardId, templateId, overrides = {}) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/workflows/from-template`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template_id: templateId, ...overrides }),
  });
  if (!response.ok) throw new Error('Failed to create from template');
  return response.json();
}
