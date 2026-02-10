/**
 * AI Agents API.
 */

import { API_BASE, authFetch } from './client.js';

/**
 * Create a new AI agent task.
 * @param {Object} params - Agent task parameters
 * @param {string} params.query - The task for the agent
 * @param {string} params.model - Model to use (default: claude-sonnet-4)
 * @param {Object} params.context - Additional context for the agent
 * @returns {Promise<Object>} Created agent task
 */
export async function createAgent({ query, model = 'anthropic/claude-sonnet-4', context = null }) {
  const response = await authFetch(`${API_BASE}/agents`, {
    method: 'POST',
    body: JSON.stringify({ query, model, context }),
  });
  if (!response.ok) {
    throw new Error('Failed to create agent');
  }
  return response.json();
}

/**
 * List all agent tasks.
 * @returns {Promise<Object>} List of agent tasks
 */
export async function listAgents() {
  const response = await authFetch(`${API_BASE}/agents`);
  if (!response.ok) {
    throw new Error('Failed to list agents');
  }
  return response.json();
}

/**
 * Get a specific agent task.
 * @param {string} taskId - Agent task ID
 * @returns {Promise<Object>} Agent task details
 */
export async function getAgent(taskId) {
  const response = await authFetch(`${API_BASE}/agents/${taskId}`);
  if (!response.ok) {
    throw new Error('Failed to get agent');
  }
  return response.json();
}

/**
 * Run an agent task to completion.
 * @param {string} taskId - Agent task ID
 * @param {number} maxSteps - Maximum steps to execute
 * @returns {Promise<Object>} Completed agent task
 */
export async function runAgent(taskId, maxSteps = 10) {
  const response = await authFetch(`${API_BASE}/agents/${taskId}/run?max_steps=${maxSteps}`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to run agent');
  }
  return response.json();
}

/**
 * Run an agent task with streaming updates.
 * @param {string} taskId - Agent task ID
 * @param {number} maxSteps - Maximum steps to execute
 * @param {function} onEvent - Callback for each event
 * @returns {Promise<void>}
 */
export async function runAgentStream(taskId, maxSteps = 10, onEvent) {
  const response = await authFetch(`${API_BASE}/agents/${taskId}/run/stream?max_steps=${maxSteps}`, {
    method: 'POST',
  });

  if (!response.ok) {
    throw new Error('Failed to run agent');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse agent event:', e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Cancel a running agent task.
 * @param {string} taskId - Agent task ID
 * @returns {Promise<Object>} Cancellation status
 */
export async function cancelAgent(taskId) {
  const response = await authFetch(`${API_BASE}/agents/${taskId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to cancel agent');
  }
  return response.json();
}

/**
 * Delete an agent task.
 * @param {string} taskId - Agent task ID
 * @returns {Promise<Object>} Deletion status
 */
export async function deleteAgent(taskId) {
  const response = await authFetch(`${API_BASE}/agents/${taskId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete agent');
  }
  return response.json();
}

// ── Canvas Agent (v6) ──────────────────────────

export async function runCanvasAgent(boardId, { goal, model = 'openai/gpt-4o', maxIterations = 20 } = {}, onEvent) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal, model, max_iterations: maxIterations }),
  });

  if (!response.ok) throw new Error('Failed to start canvas agent');

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

export async function pauseCanvasAgent(boardId, runId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/agent/${runId}/pause`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to pause agent');
  return response.json();
}

export async function resumeCanvasAgent(boardId, runId, onEvent) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/agent/${runId}/resume`, {
    method: 'POST',
  });

  if (!response.ok) throw new Error('Failed to resume agent');

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

export async function cancelCanvasAgent(boardId, runId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/agent/${runId}/cancel`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to cancel agent');
  return response.json();
}

export async function listCanvasAgentRuns(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/agent/runs`);
  if (!response.ok) throw new Error('Failed to list agent runs');
  return response.json();
}
