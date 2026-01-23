/**
 * Configuration API - Council config, presets, models, API keys, personas.
 */

import { API_BASE, authFetch } from './client.js';

// ============ API KEYS ============

/**
 * Get all configured API keys (masked for security).
 * @returns {Promise<Object>} API keys status and providers list
 */
export async function getApiKeys() {
  const response = await authFetch(`${API_BASE}/api/keys`);
  if (!response.ok) {
    throw new Error('Failed to get API keys');
  }
  return response.json();
}

/**
 * Set an API key for a provider.
 * When set, the system uses direct provider API instead of OpenRouter.
 * @param {string} provider - Provider name (openai, anthropic, google, x-ai, deepseek, mistralai, cohere)
 * @param {string} apiKey - The API key (empty string to clear)
 * @returns {Promise<Object>} Status of the operation
 */
export async function setApiKey(provider, apiKey) {
  const response = await authFetch(`${API_BASE}/api/keys`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ provider, api_key: apiKey }),
  });
  if (!response.ok) {
    throw new Error('Failed to set API key');
  }
  return response.json();
}

/**
 * Remove an API key for a provider (revert to using OpenRouter).
 * @param {string} provider - Provider name
 * @returns {Promise<Object>} Status of the operation
 */
export async function deleteApiKey(provider) {
  const response = await authFetch(`${API_BASE}/api/keys/${provider}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete API key');
  }
  return response.json();
}

// ============ CONFIG API ============

/**
 * Get current council configuration.
 */
export async function getConfig() {
  const response = await authFetch(`${API_BASE}/api/config`);
  if (!response.ok) {
    throw new Error('Failed to get config');
  }
  return response.json();
}

/**
 * Update council configuration.
 */
export async function updateConfig(config) {
  const response = await authFetch(`${API_BASE}/api/config`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new Error('Failed to update config');
  }
  return response.json();
}

/**
 * Reset configuration to defaults.
 */
export async function resetConfig() {
  const response = await authFetch(`${API_BASE}/api/config/reset`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to reset config');
  }
  return response.json();
}

// ============ PRESETS API ============

/**
 * Get all available council presets.
 * @returns {Promise<Object>} Presets list with id, name, description, models, chairman
 */
export async function getPresets() {
  const response = await authFetch(`${API_BASE}/api/presets`);
  if (!response.ok) {
    throw new Error('Failed to get presets');
  }
  return response.json();
}

/**
 * Apply a built-in council preset.
 * @param {string} presetId - The preset ID to apply
 * @returns {Promise<Object>} Applied preset with council_models and chairman_model
 */
export async function applyPreset(presetId) {
  const response = await authFetch(`${API_BASE}/api/presets/${presetId}/apply`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to apply preset');
  }
  return response.json();
}

// ============ COST ESTIMATION API ============

/**
 * Estimate the cost of a council query before sending it.
 * @param {Object} params - Cost estimation parameters
 * @param {number} params.message_length - Character length of the user's message
 * @param {Array<string>} params.council_models - Optional list of model IDs
 * @param {string} params.chairman_model - Optional chairman model ID
 * @returns {Promise<Object>} Cost estimate with min/max costs, breakdown, and token estimates
 */
export async function estimateCost({ message_length, council_models = null, chairman_model = null }) {
  const body = { message_length };
  if (council_models) {
    body.council_models = council_models;
  }
  if (chairman_model) {
    body.chairman_model = chairman_model;
  }

  const response = await authFetch(`${API_BASE}/api/estimate-cost`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error('Failed to estimate cost');
  }
  return response.json();
}

// ============ USAGE API ============

/**
 * Get session usage statistics.
 */
export async function getUsage() {
  const response = await authFetch(`${API_BASE}/api/usage`);
  if (!response.ok) {
    throw new Error('Failed to get usage');
  }
  return response.json();
}

/**
 * Reset session usage statistics.
 */
export async function resetUsage() {
  const response = await authFetch(`${API_BASE}/api/usage/reset`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to reset usage');
  }
  return response.json();
}

// ============ MODELS API ============

/**
 * Refresh available models from OpenRouter.
 */
export async function refreshModels() {
  const response = await authFetch(`${API_BASE}/api/models/refresh`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to refresh models');
  }
  return response.json();
}

// ============ PERSONA API ============

/**
 * Get all available personas (default + custom).
 */
export async function getPersonas() {
  const response = await authFetch(`${API_BASE}/api/personas`);
  if (!response.ok) {
    throw new Error('Failed to get personas');
  }
  return response.json();
}

/**
 * Set persona for a specific model.
 */
export async function setPersona(modelId, personaKey) {
  const response = await authFetch(`${API_BASE}/api/personas`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model_id: modelId, persona_key: personaKey }),
  });
  if (!response.ok) {
    throw new Error('Failed to set persona');
  }
  return response.json();
}

/**
 * Create a custom persona.
 */
export async function createCustomPersona(personaId, personaText) {
  const response = await authFetch(`${API_BASE}/api/personas/custom`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ persona_id: personaId, persona_text: personaText }),
  });
  if (!response.ok) {
    throw new Error('Failed to create custom persona');
  }
  return response.json();
}

// ============ FEATURES API ============

/**
 * Get enhanced features configuration.
 */
export async function getFeatures() {
  const response = await authFetch(`${API_BASE}/api/features`);
  if (!response.ok) {
    throw new Error('Failed to get features');
  }
  return response.json();
}

/**
 * Update enhanced features configuration.
 * @param {Object} features - Feature toggles (web_search, code_execution, memory)
 */
export async function setFeatures(features) {
  const response = await authFetch(`${API_BASE}/api/features`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(features),
  });
  if (!response.ok) {
    throw new Error('Failed to set features');
  }
  return response.json();
}

// ============ BUDGET API ============

/**
 * Get current budget configuration and status.
 * @returns {Promise<Object>} Budget config with limits, spending, status, and alerts
 */
export async function getBudget() {
  const response = await authFetch(`${API_BASE}/api/budget`);
  if (!response.ok) {
    throw new Error('Failed to get budget');
  }
  return response.json();
}

/**
 * Set budget limits and alert threshold.
 * @param {Object} budgetConfig - Budget configuration
 * @param {number} budgetConfig.daily - Daily budget limit (0 = disabled)
 * @param {number} budgetConfig.weekly - Weekly budget limit (0 = disabled)
 * @param {number} budgetConfig.monthly - Monthly budget limit (0 = disabled)
 * @param {number} budgetConfig.alert_threshold - Alert threshold percentage (0-100)
 * @returns {Promise<Object>} Updated budget configuration
 */
export async function setBudget(budgetConfig) {
  const response = await authFetch(`${API_BASE}/api/budget`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(budgetConfig),
  });
  if (!response.ok) {
    throw new Error('Failed to set budget');
  }
  return response.json();
}

/**
 * Get all currently active budget alerts.
 * @returns {Promise<Object>} Active alerts and exceeded status
 */
export async function getBudgetAlerts() {
  const response = await authFetch(`${API_BASE}/api/budget/alerts`);
  if (!response.ok) {
    throw new Error('Failed to get budget alerts');
  }
  return response.json();
}

/**
 * Manually reset budget spending for a period.
 * @param {string} period - Period to reset (daily/weekly/monthly), or null for all
 * @returns {Promise<Object>} Reset status
 */
export async function resetBudget(period = null) {
  const url = period
    ? `${API_BASE}/api/budget/reset?period=${period}`
    : `${API_BASE}/api/budget/reset`;
  const response = await authFetch(url, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to reset budget');
  }
  return response.json();
}

/**
 * Clear all active budget alerts.
 * @returns {Promise<Object>} Clear status
 */
export async function clearBudgetAlerts() {
  const response = await authFetch(`${API_BASE}/api/budget/alerts/clear`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to clear budget alerts');
  }
  return response.json();
}

// ============ CACHE ============

/**
 * Get cache statistics.
 */
export async function getCacheStats() {
  const response = await authFetch(`${API_BASE}/api/cache`);
  if (!response.ok) {
    throw new Error('Failed to get cache stats');
  }
  return response.json();
}

/**
 * Clear the response cache.
 */
export async function clearCache() {
  const response = await authFetch(`${API_BASE}/api/cache/clear`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to clear cache');
  }
  return response.json();
}

// ============ ROUTELLM API ============

/**
 * Route a query to the best model(s).
 * @param {Object} params - Routing parameters
 * @param {string} params.query - The query to route
 * @param {boolean} params.prefer_speed - Prefer faster models
 * @param {boolean} params.prefer_cost - Prefer cheaper models
 * @param {boolean} params.prefer_quality - Prefer higher quality models
 * @param {number} params.num_recommendations - Number of models to recommend
 * @returns {Promise<Object>} Routing result with query type, scores, and recommendations
 */
export async function routeQuery({ query, prefer_speed = false, prefer_cost = false, prefer_quality = true, num_recommendations = 3 }) {
  const response = await authFetch(`${API_BASE}/api/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, prefer_speed, prefer_cost, prefer_quality, num_recommendations }),
  });
  if (!response.ok) {
    throw new Error('Failed to route query');
  }
  return response.json();
}

/**
 * Get a quick single model recommendation.
 * @param {string} query - The query to route
 * @returns {Promise<Object>} { model_id: string }
 */
export async function getQuickRoute(query) {
  const response = await authFetch(`${API_BASE}/api/route/quick?query=${encodeURIComponent(query)}`);
  if (!response.ok) {
    throw new Error('Failed to get quick route');
  }
  return response.json();
}

/**
 * Get an optimal council composition for a query.
 * @param {string} query - The query to analyze
 * @param {number} maxModels - Maximum number of models
 * @returns {Promise<Object>} { council_models: string[] }
 */
export async function getCouncilRoute(query, maxModels = 5) {
  const response = await authFetch(`${API_BASE}/api/route/council?query=${encodeURIComponent(query)}&max_models=${maxModels}`);
  if (!response.ok) {
    throw new Error('Failed to get council route');
  }
  return response.json();
}

// ============ API KEYS API (User Keys) ============

/**
 * List all API keys for the current user.
 */
export async function listAPIKeys() {
  const response = await authFetch(`${API_BASE}/api/keys`);
  if (!response.ok) {
    throw new Error('Failed to list API keys');
  }
  return response.json();
}

/**
 * Create a new API key.
 * @param {Object} keyData - API key configuration
 * @param {string} keyData.name - Key name
 * @param {Array<string>} keyData.scopes - Key scopes
 * @param {number} keyData.rate_limit - Rate limit per minute
 */
export async function createAPIKey({ name, scopes = ['chat', 'read'], rate_limit = 100 }) {
  const response = await authFetch(`${API_BASE}/api/keys`, {
    method: 'POST',
    body: JSON.stringify({ name, scopes, rate_limit }),
  });
  if (!response.ok) {
    throw new Error('Failed to create API key');
  }
  return response.json();
}

/**
 * Update an API key.
 * @param {string} keyId - API key ID
 * @param {Object} updates - Updates to apply
 */
export async function updateAPIKey(keyId, updates) {
  const response = await authFetch(`${API_BASE}/api/keys/${keyId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    throw new Error('Failed to update API key');
  }
  return response.json();
}

/**
 * Revoke an API key.
 * @param {string} keyId - API key ID
 */
export async function revokeAPIKey(keyId) {
  const response = await authFetch(`${API_BASE}/api/keys/${keyId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to revoke API key');
  }
  return response.json();
}
