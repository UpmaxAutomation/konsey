/**
 * Utility for converting model IDs to friendly display names.
 */

/**
 * Convert a model ID to a friendly display name.
 * Examples:
 *   "anthropic/claude-sonnet-4" -> "Claude Sonnet 4"
 *   "openai/gpt-4o" -> "GPT-4o"
 *   "google/gemini-2.5-flash" -> "Gemini 2.5 Flash"
 */
export function getFriendlyModelName(modelId) {
  if (!modelId) return 'Unknown Model';

  // Split provider/model
  const parts = modelId.split('/');
  if (parts.length !== 2) return modelId;

  const [provider, model] = parts;

  // Remove common prefixes and format
  let friendly = model
    .replace(/^claude-/, 'Claude ')
    .replace(/^gpt-/, 'GPT-')
    .replace(/^gemini-/, 'Gemini ')
    .replace(/^grok-/, 'Grok ')
    .replace(/^llama-/, 'Llama ')
    .replace(/^deepseek-/, 'DeepSeek ')
    .replace(/^mistral-/, 'Mistral ')
    .replace(/^qwen-/, 'Qwen ')
    .replace(/^qwq-/, 'QwQ ')
    .replace(/^command-/, 'Command ')
    .replace(/^gemma-/, 'Gemma ')
    .replace(/^codestral/, 'Codestral')
    .replace(/-instruct/g, '')
    .replace(/-preview/g, ' Preview')
    .replace(/-latest/g, ' Latest')
    .replace(/:/g, ' ')
    .replace(/:free$/g, ' (Free)')
    .trim();

  // Capitalize first letter if needed
  if (friendly.length > 0) {
    friendly = friendly.charAt(0).toUpperCase() + friendly.slice(1);
  }

  // Handle special cases
  if (model.startsWith('o1') || model.startsWith('o3') || model.startsWith('o4')) {
    // OpenAI O-series
    friendly = model.toUpperCase()
      .replace(/-/g, ' ')
      .replace('MINI', 'Mini')
      .replace('PRO', 'Pro')
      .replace('DEEP RESEARCH', 'Deep Research');
  }

  return friendly;
}

/**
 * Get the provider name from a model ID.
 */
export function getProviderName(modelId) {
  if (!modelId) return 'Unknown';

  const parts = modelId.split('/');
  if (parts.length !== 2) return 'Unknown';

  const provider = parts[0];

  const providerNames = {
    'openai': 'OpenAI',
    'anthropic': 'Anthropic',
    'google': 'Google',
    'x-ai': 'xAI',
    'meta-llama': 'Meta',
    'deepseek': 'DeepSeek',
    'mistralai': 'Mistral',
    'qwen': 'Qwen',
    'cohere': 'Cohere',
  };

  return providerNames[provider] || provider;
}

/**
 * Group models by provider.
 * Returns object: { 'OpenAI': [...model IDs], 'Anthropic': [...], ... }
 */
export function groupModelsByProvider(modelIds) {
  const groups = {};

  for (const modelId of modelIds) {
    const provider = getProviderName(modelId);
    if (!groups[provider]) {
      groups[provider] = [];
    }
    groups[provider].push(modelId);
  }

  // Sort providers alphabetically
  const sortedGroups = {};
  Object.keys(groups)
    .sort()
    .forEach((provider) => {
      sortedGroups[provider] = groups[provider];
    });

  return sortedGroups;
}

/**
 * Get a good default model from available models list.
 * Prefers Claude Sonnet 4 or GPT-4o if available.
 */
export function getDefaultModel(availableModels) {
  if (!availableModels || availableModels.length === 0) {
    return 'anthropic/claude-sonnet-4';
  }

  // Priority order for defaults
  const preferredDefaults = [
    'anthropic/claude-sonnet-4',
    'anthropic/claude-sonnet-4-20250514',
    'openai/gpt-4o',
    'google/gemini-2.5-flash',
    'google/gemini-2.5-pro',
  ];

  for (const preferred of preferredDefaults) {
    if (availableModels.includes(preferred)) {
      return preferred;
    }
  }

  // Return first available model as fallback
  return availableModels[0];
}
