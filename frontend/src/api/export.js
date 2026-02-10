/**
 * Export and Sharing API.
 */

import { API_BASE, authFetch } from './client.js';

// ============ EXPORT API ============

/**
 * Export a conversation in the specified format.
 * @param {string} conversationId - The conversation ID
 * @param {string} format - Export format ('md', 'json', 'html')
 * @returns {Promise<Blob>} The exported file as a blob
 */
export async function exportConversation(conversationId, format = 'md') {
  const response = await authFetch(
    `${API_BASE}/conversations/${conversationId}/export?format=${format}`
  );
  if (!response.ok) {
    throw new Error('Failed to export conversation');
  }
  return response.blob();
}

/**
 * Export conversation to markdown.
 * @param {string} conversationId - Conversation ID
 */
export async function exportMarkdown(conversationId) {
  const response = await authFetch(`${API_BASE}/export/${conversationId}/markdown`);
  if (!response.ok) {
    throw new Error('Failed to export');
  }
  return response.text();
}

/**
 * Export conversation to JSON.
 * @param {string} conversationId - Conversation ID
 */
export async function exportJSON(conversationId) {
  const response = await authFetch(`${API_BASE}/export/${conversationId}/json`);
  if (!response.ok) {
    throw new Error('Failed to export');
  }
  return response.text();
}

/**
 * Export conversation to HTML.
 * @param {string} conversationId - Conversation ID
 */
export async function exportHTML(conversationId) {
  const response = await authFetch(`${API_BASE}/export/${conversationId}/html`);
  if (!response.ok) {
    throw new Error('Failed to export');
  }
  return response.text();
}

// ============ SHARING API ============

/**
 * Create a shareable link for a conversation.
 * @param {string} conversationId - The conversation ID
 * @returns {Promise<{token: string, share_url: string}>}
 */
export async function shareConversation(conversationId) {
  const response = await authFetch(`${API_BASE}/share/${conversationId}`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to create share link');
  }
  return response.json();
}

/**
 * Get a shared conversation by token.
 * @param {string} token - The share token
 * @returns {Promise<Object>} The conversation data
 */
export async function getSharedConversation(token) {
  const response = await fetch(`${API_BASE}/shared/${token}`);
  if (!response.ok) {
    throw new Error('Share link not found or expired');
  }
  return response.json();
}

// ============ BOARD EXPORT & SHARING API ============

export async function exportBoard(boardId, format = 'md') {
  const res = await fetch(`${API_BASE}/api/boards/${boardId}/export?format=${format}`, {
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to export board');
  return res.blob();
}

export async function shareBoard(boardId) {
  const res = await fetch(`${API_BASE}/api/boards/${boardId}/share`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Failed to share board');
  return res.json();
}

export async function getSharedBoard(token) {
  const res = await fetch(`${API_BASE}/api/shared/boards/${token}`, {
    credentials: 'include',
  });
  if (!res.ok) throw new Error('Shared board not found');
  return res.json();
}
