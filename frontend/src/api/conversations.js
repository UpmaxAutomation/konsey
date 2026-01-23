/**
 * Conversation API - CRUD operations and messaging.
 */

import {
  API_BASE,
  authFetch,
  safeFetch,
  handleResponse,
  withAPIRetry,
  withStreamRetry,
  getUserFriendlyMessage,
  NetworkError,
  AbortError,
  parseError,
} from './client.js';

/**
 * List all conversations.
 */
export async function listConversations() {
  const response = await authFetch(`${API_BASE}/api/conversations`);
  if (!response.ok) {
    throw new Error('Failed to list conversations');
  }
  return response.json();
}

/**
 * Create a new conversation.
 */
export async function createConversation() {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H2',location:'conversations.js:32',message:'createConversation:request',data:{url:`${API_BASE}/api/conversations`},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  const response = await authFetch(`${API_BASE}/api/conversations`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H2',location:'conversations.js:37',message:'createConversation:response',data:{status:response.status,ok:response.ok},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  if (!response.ok) {
    let errorMessage = 'Failed to create conversation';
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch (e) {
      // If response is not JSON, use status text
      errorMessage = response.statusText || errorMessage;
    }
    const error = new Error(errorMessage);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

/**
 * Get a specific conversation.
 */
export async function getConversation(conversationId) {
  const response = await authFetch(
    `${API_BASE}/api/conversations/${conversationId}`
  );
  if (!response.ok) {
    throw new Error('Failed to get conversation');
  }
  return response.json();
}

/**
 * Delete a conversation.
 */
export async function deleteConversation(conversationId) {
  const response = await authFetch(
    `${API_BASE}/api/conversations/${conversationId}`,
    { method: 'DELETE' }
  );
  if (!response.ok) {
    throw new Error('Failed to delete conversation');
  }
  return response.json();
}

/**
 * Send a message in a conversation with retry logic.
 * @param {string} conversationId - The conversation ID
 * @param {string} content - The message content
 * @param {Array<string>} attachedFiles - Optional list of filenames
 * @param {Object} retryOptions - Optional retry configuration
 * @returns {Promise<Object>} The response data
 * @throws {APIError} On unrecoverable errors
 */
export async function sendMessage(conversationId, content, attachedFiles = [], retryOptions = {}) {
  const body = { content };
  if (attachedFiles && attachedFiles.length > 0) {
    body.attached_files = attachedFiles;
  }

  return withAPIRetry(
    async () => {
      const response = await authFetch(
        `${API_BASE}/api/conversations/${conversationId}/message`,
        {
          method: 'POST',
          body: JSON.stringify(body),
        },
        'sendMessage'
      );
      await handleResponse(response, 'sendMessage');
      return response.json();
    },
    {
      maxRetries: 3,
      onRetry: (attempt, error, delay) => {
        console.log(`[sendMessage] Retry ${attempt + 1} after ${delay}ms:`, error.message);
      },
      ...retryOptions,
    }
  );
}

/**
 * Send a message and receive streaming updates with retry logic.
 * Retry only applies to the initial connection - once streaming starts, failures are not retried.
 * @param {string} conversationId - The conversation ID
 * @param {string} content - The message content
 * @param {function} onEvent - Callback function for each event: (eventType, data) => void
 * @param {AbortSignal} signal - Optional abort signal for cancellation
 * @param {Array<string>} attachedFiles - Optional list of filenames
 * @param {Object} retryOptions - Optional retry configuration for initial connection
 * @returns {Promise<void>}
 * @throws {APIError} On unrecoverable connection errors
 */
export async function sendMessageStream(conversationId, content, onEvent, signal = null, attachedFiles = [], retryOptions = {}) {
  const body = { content };
  if (attachedFiles && attachedFiles.length > 0) {
    body.attached_files = attachedFiles;
  }

  // Retry only the initial connection, not the streaming itself
  const response = await withStreamRetry(
    async () => {
      const res = await authFetch(
        `${API_BASE}/api/conversations/${conversationId}/message/stream`,
        {
          method: 'POST',
          body: JSON.stringify(body),
          signal: signal,
        },
        'sendMessageStream'
      );
      await handleResponse(res, 'sendMessageStream');
      return res;
    },
    {
      maxRetries: 2,
      signal,
      onRetry: (attempt, error, delay) => {
        onEvent('retry', { attempt: attempt + 1, error: getUserFriendlyMessage(error), delay });
      },
      ...retryOptions,
    }
  );

  // Safety check for response body
  if (!response.body) {
    const error = new NetworkError('No response body received');
    onEvent('error', { message: getUserFriendlyMessage(error) });
    throw error;
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
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  } catch (err) {
    // Handle stream errors (network failure, abort, etc.)
    if (err.name !== 'AbortError') {
      const error = parseError(err);
      onEvent('error', { message: getUserFriendlyMessage(error), error: error.toJSON() });
      throw error;
    }
    throw new AbortError('Stream was cancelled');
  } finally {
    // Clean up the reader when done or aborted
    try {
      await reader.cancel();
    } catch (e) {
      // Ignore cancel errors
    }
  }
}

/**
 * Send a quick mode message with streaming and retry logic.
 * Retry only applies to the initial connection - once streaming starts, failures are not retried.
 * @param {string} conversationId - The conversation ID
 * @param {string} content - The message content
 * @param {string} model - The model to use (optional, defaults to chairman)
 * @param {function} onEvent - Callback function for each event: (eventType, data) => void
 * @param {AbortSignal} signal - Optional abort signal for cancellation
 * @param {Array<string>} attachedFiles - Optional list of filenames
 * @param {Object} retryOptions - Optional retry configuration for initial connection
 * @returns {Promise<void>}
 * @throws {APIError} On unrecoverable connection errors
 */
export async function sendQuickMessageStream(conversationId, content, model, onEvent, signal, attachedFiles = [], retryOptions = {}) {
  const body = { content, model };
  if (attachedFiles && attachedFiles.length > 0) {
    body.attached_files = attachedFiles;
  }

  // Retry only the initial connection, not the streaming itself
  const response = await withStreamRetry(
    async () => {
      const res = await authFetch(
        `${API_BASE}/api/conversations/${conversationId}/quick-message`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
          signal,
        },
        'sendQuickMessageStream'
      );
      await handleResponse(res, 'sendQuickMessageStream');
      return res;
    },
    {
      maxRetries: 2,
      signal,
      onRetry: (attempt, error, delay) => {
        onEvent('retry', { attempt: attempt + 1, error: getUserFriendlyMessage(error), delay });
      },
      ...retryOptions,
    }
  );

  // Safety check for response body
  if (!response.body) {
    const error = new NetworkError('No response body received');
    onEvent('error', { message: getUserFriendlyMessage(error) });
    throw error;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        onEvent('complete', {});
        break;
      }

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  } catch (err) {
    // Handle stream errors (network failure, abort, etc.)
    if (err.name !== 'AbortError') {
      const error = parseError(err);
      onEvent('error', { message: getUserFriendlyMessage(error), error: error.toJSON() });
      throw error;
    }
    throw new AbortError('Stream was cancelled');
  } finally {
    // Ensure reader is released
    try {
      reader.releaseLock();
    } catch (e) {
      // Ignore release errors
    }
  }
}

/**
 * Move a conversation to a folder.
 * @param {string} conversationId - Conversation ID
 * @param {string|null} folderId - Folder ID (null to remove from folder)
 * @returns {Promise<Object>} Update status
 */
export async function moveConversationToFolder(conversationId, folderId) {
  const response = await authFetch(`${API_BASE}/api/conversations/${conversationId}/folder`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ folder_id: folderId }),
  });
  if (!response.ok) {
    throw new Error('Failed to move conversation to folder');
  }
  return response.json();
}

/**
 * Update tags for a conversation.
 * @param {string} conversationId - Conversation ID
 * @param {Array<string>} tags - List of tags
 * @returns {Promise<Object>} Update status
 */
export async function updateConversationTags(conversationId, tags) {
  const response = await authFetch(`${API_BASE}/api/conversations/${conversationId}/tags`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ tags }),
  });
  if (!response.ok) {
    throw new Error('Failed to update conversation tags');
  }
  return response.json();
}

/**
 * Upload a file to a conversation.
 * @param {string} conversationId - Conversation ID
 * @param {File} file - File to upload
 */
export async function uploadFile(conversationId, file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await authFetch(`${API_BASE}/api/conversations/${conversationId}/upload`, {
    method: 'POST',
    body: formData,
    // Note: Don't set Content-Type header, let browser set it with boundary for FormData
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to upload file');
  }
  return response.json();
}

/**
 * List files in a conversation.
 * @param {string} conversationId - Conversation ID
 * @returns {Promise<Array>} List of file objects
 */
export async function listFiles(conversationId) {
  const response = await authFetch(`${API_BASE}/api/conversations/${conversationId}/files`);
  if (!response.ok) {
    throw new Error('Failed to list files');
  }
  return response.json();
}

/**
 * Delete a file from a conversation.
 * @param {string} conversationId - Conversation ID
 * @param {string} filename - Name of file to delete
 * @returns {Promise<Object>} Status
 */
export async function deleteFile(conversationId, filename) {
  const response = await authFetch(`${API_BASE}/api/conversations/${conversationId}/files/${filename}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete file');
  }
  return response.json();
}

/**
 * Import a conversation from exported JSON data.
 * @param {Object} data - Conversation data to import
 * @param {Array} data.messages - List of message objects (required)
 * @param {string} [data.title] - Optional conversation title
 * @param {string} [data.created_at] - Optional creation timestamp
 * @param {string} [data.folder_id] - Optional folder ID
 * @param {Array<string>} [data.tags] - Optional list of tags
 * @returns {Promise<Object>} The imported conversation
 */
export async function importConversation(data) {
  const response = await authFetch(`${API_BASE}/api/conversations/import`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to import conversation');
  }
  return response.json();
}

/**
 * Fork a conversation from a specific message.
 * Creates a new conversation with messages up to and including the specified index.
 * @param {string} conversationId - Source conversation ID
 * @param {number} messageIndex - Include messages up to this index (0-based)
 * @returns {Promise<Object>} The new forked conversation
 */
export async function forkConversation(conversationId, messageIndex) {
  const response = await authFetch(`${API_BASE}/api/conversations/${conversationId}/fork`, {
    method: 'POST',
    body: JSON.stringify({ message_index: messageIndex }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to fork conversation');
  }
  return response.json();
}
