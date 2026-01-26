/**
 * Projects API - Projects, folders, tags, and team workspaces.
 */

import { API_BASE, authFetch } from './client.js';

// ============ PROJECTS API ============

/**
 * List all projects.
 */
export async function listProjects() {
  const response = await authFetch(`${API_BASE}/projects`);
  if (!response.ok) {
    throw new Error('Failed to list projects');
  }
  return response.json();
}

/**
 * Create a new project.
 */
export async function createProject({ name, description, system_prompt, council_models, chairman_model }) {
  const response = await authFetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      name,
      description,
      system_prompt,
      council_models,
      chairman_model,
    }),
  });
  if (!response.ok) {
    throw new Error('Failed to create project');
  }
  return response.json();
}

/**
 * Get a specific project.
 */
export async function getProject(projectId) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}`);
  if (!response.ok) {
    throw new Error('Failed to get project');
  }
  return response.json();
}

/**
 * Update a project.
 */
export async function updateProject(projectId, updates) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error('Failed to update project');
  }
  return response.json();
}

/**
 * Delete a project.
 */
export async function deleteProject(projectId) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete project');
  }
  return response.json();
}

/**
 * Add a file to project's knowledge base.
 */
export async function addKnowledgeToProject(projectId, { filename, content, file_type }) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}/knowledge`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      filename,
      content,
      file_type: file_type || 'text',
    }),
  });
  if (!response.ok) {
    throw new Error('Failed to add knowledge');
  }
  return response.json();
}

/**
 * Remove a file from project's knowledge base.
 */
export async function removeKnowledgeFromProject(projectId, fileId) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}/knowledge/${fileId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to remove knowledge');
  }
  return response.json();
}

/**
 * Get knowledge base file content.
 */
export async function getKnowledgeContent(projectId, fileId) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}/knowledge/${fileId}`);
  if (!response.ok) {
    throw new Error('Failed to get knowledge content');
  }
  return response.json();
}

/**
 * Create a new conversation in a project.
 */
export async function createConversationInProject(projectId) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}/conversations`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to create conversation in project');
  }
  return response.json();
}

/**
 * Move a conversation to a project.
 * @param {string} conversationId - Conversation ID
 * @param {string|null} projectId - Project ID (or null to remove from project)
 */
export async function moveConversationToProject(conversationId, projectId) {
  const response = await authFetch(`${API_BASE}/conversations/${conversationId}/project`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId }),
  });
  if (!response.ok) {
    let errorMessage = 'Failed to move conversation to project';
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorData.message || errorMessage;
    } catch (e) {
      errorMessage = response.statusText || errorMessage;
    }
    throw new Error(errorMessage);
  }
  return response.json();
}

// ============ PROJECT MEMORY API ============

/**
 * Get project memory context.
 */
export async function getProjectMemory(projectId) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'get_context' }),
  });
  if (!response.ok) {
    throw new Error('Failed to get project memory');
  }
  return response.json();
}

/**
 * Get project memory statistics.
 */
export async function getProjectMemoryStats(projectId) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'stats' }),
  });
  if (!response.ok) {
    throw new Error('Failed to get project memory stats');
  }
  return response.json();
}

/**
 * Clear project memory.
 */
export async function clearProjectMemory(projectId) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'clear' }),
  });
  if (!response.ok) {
    throw new Error('Failed to clear project memory');
  }
  return response.json();
}

/**
 * Add a fact to project memory.
 */
export async function addProjectFact(projectId, content, category = 'general') {
  const response = await authFetch(`${API_BASE}/projects/${projectId}/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'add_fact', content, category }),
  });
  if (!response.ok) {
    throw new Error('Failed to add project fact');
  }
  return response.json();
}

/**
 * Set a project preference.
 */
export async function setProjectPreference(projectId, key, value) {
  const response = await authFetch(`${API_BASE}/projects/${projectId}/memory`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'set_preference', key, value }),
  });
  if (!response.ok) {
    throw new Error('Failed to set project preference');
  }
  return response.json();
}

// ============ FOLDER API ============

/**
 * List all folders.
 * @returns {Promise<Object>} Folders list
 */
export async function listFolders() {
  const response = await authFetch(`${API_BASE}/folders`);
  if (!response.ok) {
    throw new Error('Failed to list folders');
  }
  return response.json();
}

/**
 * Create a new folder.
 * @param {Object} folderData - Folder data
 * @param {string} folderData.name - Folder name
 * @param {string} folderData.color - Hex color code (default: #4a90e2)
 * @param {string} folderData.icon - Icon name (default: folder)
 * @returns {Promise<Object>} Created folder
 */
export async function createFolder({ name, color = '#4a90e2', icon = 'folder' }) {
  const response = await authFetch(`${API_BASE}/folders`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name, color, icon }),
  });
  if (!response.ok) {
    throw new Error('Failed to create folder');
  }
  return response.json();
}

/**
 * Delete a folder.
 * @param {string} folderId - Folder ID
 * @returns {Promise<Object>} Deletion status
 */
export async function deleteFolder(folderId) {
  const response = await authFetch(`${API_BASE}/folders/${folderId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete folder');
  }
  return response.json();
}

// ============ TAG API ============

/**
 * List all unique tags across all conversations.
 * @returns {Promise<Object>} Tags list
 */
export async function listAllTags() {
  const response = await authFetch(`${API_BASE}/tags`);
  if (!response.ok) {
    throw new Error('Failed to list tags');
  }
  return response.json();
}

// ============ TEAM WORKSPACES API ============

/**
 * List all teams the user belongs to.
 */
export async function listTeams() {
  const response = await authFetch(`${API_BASE}/teams`);
  if (!response.ok) {
    throw new Error('Failed to list teams');
  }
  return response.json();
}

/**
 * Create a new team.
 * @param {Object} teamData - Team data
 * @param {string} teamData.name - Team name
 * @param {string} teamData.description - Team description
 */
export async function createTeam({ name, description }) {
  const response = await authFetch(`${API_BASE}/teams`, {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  });
  if (!response.ok) {
    throw new Error('Failed to create team');
  }
  return response.json();
}

/**
 * Get team details.
 * @param {string} teamId - Team ID
 */
export async function getTeam(teamId) {
  const response = await authFetch(`${API_BASE}/teams/${teamId}`);
  if (!response.ok) {
    throw new Error('Failed to get team');
  }
  return response.json();
}

/**
 * Update team settings.
 * @param {string} teamId - Team ID
 * @param {Object} updates - Updates to apply
 */
export async function updateTeam(teamId, updates) {
  const response = await authFetch(`${API_BASE}/teams/${teamId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error('Failed to update team');
  }
  return response.json();
}

/**
 * Delete a team.
 * @param {string} teamId - Team ID
 */
export async function deleteTeam(teamId) {
  const response = await authFetch(`${API_BASE}/teams/${teamId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete team');
  }
  return response.json();
}

/**
 * Invite a member to the team.
 * @param {string} teamId - Team ID
 * @param {string} email - Member email
 * @param {string} role - Member role (owner, admin, member)
 */
export async function inviteTeamMember(teamId, email, role = 'member') {
  const response = await authFetch(`${API_BASE}/teams/${teamId}/members`, {
    method: 'POST',
    body: JSON.stringify({ email, role }),
  });
  if (!response.ok) {
    throw new Error('Failed to invite member');
  }
  return response.json();
}

/**
 * Remove a member from the team.
 * @param {string} teamId - Team ID
 * @param {string} memberId - Member ID
 */
export async function removeTeamMember(teamId, memberId) {
  const response = await authFetch(`${API_BASE}/teams/${teamId}/members/${memberId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to remove member');
  }
  return response.json();
}

/**
 * Share a conversation with a team.
 * @param {string} teamId - Team ID
 * @param {string} conversationId - Conversation ID
 */
export async function shareConversationToTeam(teamId, conversationId) {
  const response = await authFetch(`${API_BASE}/teams/${teamId}/conversations`, {
    method: 'POST',
    body: JSON.stringify({ conversation_id: conversationId }),
  });
  if (!response.ok) {
    throw new Error('Failed to share conversation');
  }
  return response.json();
}

/**
 * List conversations shared with a team.
 * @param {string} teamId - Team ID
 */
export async function listTeamConversations(teamId) {
  const response = await authFetch(`${API_BASE}/teams/${teamId}/conversations`);
  if (!response.ok) {
    throw new Error('Failed to list team conversations');
  }
  return response.json();
}
