/**
 * Templates API - Template CRUD operations.
 */

import { API_BASE, authFetch } from './client.js';

/**
 * List all templates, optionally filtered by category.
 * @param {string} category - Optional category filter
 * @returns {Promise<Object>} Templates list and count
 */
export async function listTemplates(category = null) {
  const url = category
    ? `${API_BASE}/templates?category=${encodeURIComponent(category)}`
    : `${API_BASE}/templates`;
  const response = await authFetch(url);
  if (!response.ok) {
    throw new Error('Failed to list templates');
  }
  return response.json();
}

/**
 * Get all unique template categories.
 * @returns {Promise<Object>} Categories list
 */
export async function getTemplateCategories() {
  const response = await authFetch(`${API_BASE}/templates/categories`);
  if (!response.ok) {
    throw new Error('Failed to get template categories');
  }
  return response.json();
}

/**
 * Get a specific template by ID.
 * @param {string} templateId - Template ID
 * @returns {Promise<Object>} Template object
 */
export async function getTemplate(templateId) {
  const response = await authFetch(`${API_BASE}/templates/${templateId}`);
  if (!response.ok) {
    throw new Error('Failed to get template');
  }
  return response.json();
}

/**
 * Create a new custom template.
 * @param {Object} template - Template data
 * @param {string} template.name - Template name
 * @param {string} template.category - Template category
 * @param {string} template.prompt_text - Prompt text with {{variable}} placeholders
 * @param {Array<string>} template.variables - Variable names
 * @returns {Promise<Object>} Created template
 */
export async function createTemplate({ name, category, prompt_text, variables }) {
  const response = await authFetch(`${API_BASE}/templates`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ name, category, prompt_text, variables }),
  });
  if (!response.ok) {
    throw new Error('Failed to create template');
  }
  return response.json();
}

/**
 * Update an existing template (custom templates only).
 * @param {string} templateId - Template ID
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>} Updated template
 */
export async function updateTemplate(templateId, updates) {
  const response = await authFetch(`${API_BASE}/templates/${templateId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error('Failed to update template');
  }
  return response.json();
}

/**
 * Delete a template (custom templates only).
 * @param {string} templateId - Template ID
 * @returns {Promise<Object>} Deletion status
 */
export async function deleteTemplate(templateId) {
  const response = await authFetch(`${API_BASE}/templates/${templateId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete template');
  }
  return response.json();
}

/**
 * Fill a template with variable values.
 * @param {string} templateId - Template ID
 * @param {Object} variableValues - Variable name/value pairs
 * @returns {Promise<Object>} Filled prompt text
 */
export async function fillTemplate(templateId, variableValues) {
  const response = await authFetch(`${API_BASE}/templates/${templateId}/fill`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ variable_values: variableValues }),
  });
  if (!response.ok) {
    throw new Error('Failed to fill template');
  }
  return response.json();
}
