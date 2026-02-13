/**
 * Pipeline API module.
 */

import { API_BASE, authFetch } from './client.js';

// ── Pipeline Execution ──────────────────────────

export async function runPipeline(boardId, onEvent) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/pipeline/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) throw new Error('Failed to run pipeline');

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
