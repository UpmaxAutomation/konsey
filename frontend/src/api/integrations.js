/**
 * Integrations API - Google Drive, Slack, GitHub.
 */

import { API_BASE, authFetch } from './client.js';

/**
 * Get status of all integrations.
 * @returns {Promise<Object>} Integration status
 */
export async function getIntegrationStatus() {
  const response = await fetch(`${API_BASE}/integrations/status`);
  if (!response.ok) {
    throw new Error('Failed to get integration status');
  }
  return response.json();
}

// ============ GOOGLE DRIVE ============

/**
 * List files in Google Drive.
 * @param {Object} params - List parameters
 * @param {string} params.access_token - Google OAuth access token
 * @param {string} params.folder_id - Folder ID (optional)
 * @param {number} params.page_size - Number of files per page
 * @returns {Promise<Object>} List of files
 */
export async function gdriveListFiles({ access_token, folder_id, page_size = 20, page_token }) {
  const response = await authFetch(`${API_BASE}/integrations/gdrive/list`, {
    method: 'POST',
    body: JSON.stringify({ access_token, folder_id, page_size, page_token }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to list Google Drive files');
  }
  return response.json();
}

/**
 * Get file content from Google Drive.
 * @param {string} access_token - Google OAuth access token
 * @param {string} file_id - File ID
 * @returns {Promise<Object>} File content
 */
export async function gdriveGetFile(access_token, file_id) {
  const response = await authFetch(`${API_BASE}/integrations/gdrive/file`, {
    method: 'POST',
    body: JSON.stringify({ access_token, file_id }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get Google Drive file');
  }
  return response.json();
}

/**
 * Upload file to Google Drive.
 * @param {Object} params - Upload parameters
 * @param {string} params.access_token - Google OAuth access token
 * @param {string} params.name - File name
 * @param {string} params.content - File content
 * @param {string} params.mime_type - MIME type
 * @param {string} params.folder_id - Target folder ID
 * @returns {Promise<Object>} Uploaded file info
 */
export async function gdriveUploadFile({ access_token, name, content, mime_type = 'text/plain', folder_id }) {
  const response = await authFetch(`${API_BASE}/integrations/gdrive/upload`, {
    method: 'POST',
    body: JSON.stringify({ access_token, name, content, mime_type, folder_id }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to upload to Google Drive');
  }
  return response.json();
}

// ============ SLACK ============

/**
 * Send message to Slack channel.
 * @param {string} channel - Channel ID or name
 * @param {string} text - Message text
 * @param {string} thread_ts - Thread timestamp (optional)
 * @returns {Promise<Object>} Message result
 */
export async function slackSendMessage(channel, text, thread_ts = null) {
  const response = await authFetch(`${API_BASE}/integrations/slack/message`, {
    method: 'POST',
    body: JSON.stringify({ channel, text, thread_ts }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send Slack message');
  }
  return response.json();
}

/**
 * Send message via Slack webhook.
 * @param {string} text - Message text
 * @param {string} username - Bot username
 * @returns {Promise<Object>} Webhook result
 */
export async function slackSendWebhook(text, username = 'LLM Council') {
  const response = await authFetch(`${API_BASE}/integrations/slack/webhook`, {
    method: 'POST',
    body: JSON.stringify({ text, username }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send Slack webhook');
  }
  return response.json();
}

/**
 * List Slack channels.
 * @returns {Promise<Object>} List of channels
 */
export async function slackListChannels() {
  const response = await authFetch(`${API_BASE}/integrations/slack/channels`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to list Slack channels');
  }
  return response.json();
}

// ============ GITHUB ============

/**
 * List GitHub repositories.
 * @param {string} username - GitHub username (optional)
 * @param {string} org - GitHub organization (optional)
 * @returns {Promise<Object>} List of repos
 */
export async function githubListRepos(username = null, org = null) {
  let url = `${API_BASE}/integrations/github/repos`;
  const params = new URLSearchParams();
  if (username) params.append('username', username);
  if (org) params.append('org', org);
  if (params.toString()) url += `?${params.toString()}`;

  const response = await authFetch(url);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to list GitHub repos');
  }
  return response.json();
}

/**
 * Get file content from GitHub repository.
 * @param {string} owner - Repository owner
 * @param {string} repo - Repository name
 * @param {string} path - File path
 * @param {string} ref - Branch/tag/commit
 * @returns {Promise<Object>} File content
 */
export async function githubGetFile(owner, repo, path, ref = 'main') {
  const response = await authFetch(`${API_BASE}/integrations/github/file`, {
    method: 'POST',
    body: JSON.stringify({ owner, repo, path, ref }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get GitHub file');
  }
  return response.json();
}

/**
 * List issues in a GitHub repository.
 * @param {string} owner - Repository owner
 * @param {string} repo - Repository name
 * @param {string} state - Issue state (open, closed, all)
 * @returns {Promise<Object>} List of issues
 */
export async function githubListIssues(owner, repo, state = 'open') {
  const response = await authFetch(`${API_BASE}/integrations/github/issues/${owner}/${repo}?state=${state}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to list GitHub issues');
  }
  return response.json();
}

/**
 * Create an issue in a GitHub repository.
 * @param {Object} params - Issue parameters
 * @param {string} params.owner - Repository owner
 * @param {string} params.repo - Repository name
 * @param {string} params.title - Issue title
 * @param {string} params.body - Issue body
 * @param {Array<string>} params.labels - Labels
 * @param {Array<string>} params.assignees - Assignees
 * @returns {Promise<Object>} Created issue
 */
export async function githubCreateIssue({ owner, repo, title, body, labels, assignees }) {
  const response = await authFetch(`${API_BASE}/integrations/github/issues`, {
    method: 'POST',
    body: JSON.stringify({ owner, repo, title, body, labels, assignees }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to create GitHub issue');
  }
  return response.json();
}

/**
 * List pull requests in a GitHub repository.
 * @param {string} owner - Repository owner
 * @param {string} repo - Repository name
 * @param {string} state - PR state (open, closed, all)
 * @returns {Promise<Object>} List of PRs
 */
export async function githubListPRs(owner, repo, state = 'open') {
  const response = await authFetch(`${API_BASE}/integrations/github/pulls/${owner}/${repo}?state=${state}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to list GitHub PRs');
  }
  return response.json();
}
