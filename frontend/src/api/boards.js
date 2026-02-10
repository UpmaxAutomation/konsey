/**
 * Board/Canvas API module.
 */

import { API_BASE, authFetch } from './client.js';

// ── Board CRUD ──────────────────────────────

export async function listBoards(projectId = null) {
  const params = projectId ? `?project_id=${projectId}` : '';
  const response = await authFetch(`${API_BASE}/boards${params}`);
  if (!response.ok) throw new Error('Failed to list boards');
  return response.json();
}

export async function createBoard({ name, project_id = null, description = null }) {
  const response = await authFetch(`${API_BASE}/boards`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, project_id, description }),
  });
  if (!response.ok) throw new Error('Failed to create board');
  return response.json();
}

export async function getBoard(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}`);
  if (!response.ok) throw new Error('Failed to get board');
  return response.json();
}

export async function updateBoard(boardId, updates) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error('Failed to update board');
  return response.json();
}

export async function updateBoardViewport(boardId, viewport) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/viewport`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(viewport),
  });
  if (!response.ok) throw new Error('Failed to save viewport');
  return response.json();
}

export async function deleteBoard(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete board');
  return response.json();
}

// ── Card CRUD ──────────────────────────────

export async function listCards(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards`);
  if (!response.ok) throw new Error('Failed to list cards');
  return response.json();
}

export async function createCard(boardId, cardData) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cardData),
  });
  if (!response.ok) throw new Error('Failed to create card');
  return response.json();
}

export async function updateCard(boardId, cardId, updates) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/${cardId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error('Failed to update card');
  return response.json();
}

export async function batchUpdateCardPositions(boardId, positions) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/batch-positions`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ positions }),
  });
  if (!response.ok) throw new Error('Failed to update positions');
  return response.json();
}

export async function deleteCard(boardId, cardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/${cardId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete card');
  return response.json();
}

// ── Edge CRUD ──────────────────────────────

export async function listEdges(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/edges`);
  if (!response.ok) throw new Error('Failed to list edges');
  return response.json();
}

export async function createEdge(boardId, edgeData) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/edges`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(edgeData),
  });
  if (!response.ok) throw new Error('Failed to create edge');
  return response.json();
}

// ── Section CRUD ──────────────────────────────

export async function listSections(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/sections`);
  if (!response.ok) throw new Error('Failed to list sections');
  return response.json();
}

export async function createSection(boardId, sectionData) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/sections`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(sectionData),
  });
  if (!response.ok) throw new Error('Failed to create section');
  return response.json();
}

export async function updateSection(boardId, sectionId, updates) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/sections/${sectionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error('Failed to update section');
  return response.json();
}

export async function deleteSection(boardId, sectionId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/sections/${sectionId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete section');
  return response.json();
}

export async function groupIntoSection(boardId, { card_ids, title, color }) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/sections/group`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ card_ids, title, color }),
  });
  if (!response.ok) throw new Error('Failed to group cards into section');
  return response.json();
}

export async function ungroupSection(boardId, sectionId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/sections/${sectionId}/ungroup`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to ungroup section');
  return response.json();
}

// ── Nested Boards ──────────────────────────────

export async function listBoardChildren(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/children`);
  if (!response.ok) throw new Error('Failed to list child boards');
  return response.json();
}

export async function getBoardBreadcrumbs(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/breadcrumbs`);
  if (!response.ok) throw new Error('Failed to get breadcrumbs');
  return response.json();
}

export async function createChildBoard(parentBoardId, data) {
  const response = await authFetch(`${API_BASE}/boards/${parentBoardId}/create-child`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create child board');
  return response.json();
}

export async function moveBoard(boardId, newParentId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/move`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ new_parent_id: newParentId }),
  });
  if (!response.ok) throw new Error('Failed to move board');
  return response.json();
}

// ── Journal ──────────────────────────────

export async function createJournalEntry(boardId, data = {}) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/journal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create journal entry');
  return response.json();
}

export async function listJournalEntries(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/journal`);
  if (!response.ok) throw new Error('Failed to list journal entries');
  return response.json();
}

// ── Inbox ──────────────────────────────

export async function createInboxItem(boardId, data) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/inbox`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create inbox item');
  return response.json();
}

export async function listInboxItems(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/inbox`);
  if (!response.ok) throw new Error('Failed to list inbox items');
  return response.json();
}

export async function processInboxItem(boardId, cardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/inbox/${cardId}/process`, {
    method: 'PATCH',
  });
  if (!response.ok) throw new Error('Failed to process inbox item');
  return response.json();
}

export async function createEdgesBatch(boardId, edges) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/edges/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ edges }),
  });
  if (!response.ok) throw new Error('Failed to create edges batch');
  return response.json();
}

export async function deleteEdge(boardId, edgeId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/edges/${edgeId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete edge');
  return response.json();
}

// ── Chat → Canvas ──────────────────────────

export async function createCardFromMessage(boardId, messageData) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/from-message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(messageData),
  });
  if (!response.ok) throw new Error('Failed to create card from message');
  return response.json();
}

export async function createCardsFromCouncilTurn(boardId, turnData) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/from-council-turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(turnData),
  });
  if (!response.ok) throw new Error('Failed to create cards from council turn');
  return response.json();
}

// ── AI Actions ──────────────────────────────

export async function runCardAIAction(boardId, cardId, { action, customPrompt, model, useCouncil }) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/cards/${cardId}/ai-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, custom_prompt: customPrompt, model, use_council: useCouncil }),
  });
  if (!response.ok) throw new Error('AI action failed');
  return response.json();
}

export async function runBoardAIAction(boardId, { action, cardIds, model }) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/ai-action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, card_ids: cardIds, model }),
  });
  if (!response.ok) throw new Error('Board AI action failed');
  return response.json();
}

// ── Board Memory ───────────────────────────────

export async function getBoardMemory(boardId) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/memory`);
  if (!response.ok) throw new Error('Failed to get board memory');
  return response.json();
}

export async function boardMemoryAction(boardId, { action, content, context }) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, content, context }),
  });
  if (!response.ok) throw new Error('Board memory action failed');
  return response.json();
}

export async function deleteBoardFact(boardId, factIndex) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/memory/facts/${factIndex}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete fact');
  return response.json();
}

// ── Council from Board ─────────────────────────

/**
 * Run council deliberation from board context.
 * Returns an SSE stream. The caller must process events via EventSource or fetch+reader.
 */
export async function runCouncilFromBoard(boardId, { query, cardIds = [], webSearch = false, fastMode = false }, onEvent) {
  const response = await authFetch(`${API_BASE}/boards/${boardId}/council`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, card_ids: cardIds, web_search: webSearch, fast_mode: fastMode }),
  });

  if (!response.ok) throw new Error('Failed to start council from board');

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
