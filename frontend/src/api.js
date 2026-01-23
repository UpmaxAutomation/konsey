/**
 * API client for the LLM Council backend.
 *
 * This file re-exports from the modular api/ directory structure
 * for backward compatibility with existing imports.
 *
 * The API has been split into feature-based modules:
 * - api/client.js - Base fetch client, auth helpers, error handling
 * - api/conversations.js - Conversation CRUD, messaging, files
 * - api/config.js - Config, presets, API keys, personas, features, budget
 * - api/tools.js - Code execution, memory, search
 * - api/images.js - Image generation
 * - api/voice.js - TTS, STT
 * - api/agents.js - AI agents
 * - api/integrations.js - Google Drive, Slack, GitHub
 * - api/analytics.js - Analytics endpoints
 * - api/templates.js - Templates CRUD
 * - api/projects.js - Projects, folders, tags, teams
 * - api/ratings.js - Ratings system
 * - api/batch.js - Batch processing
 * - api/export.js - Export and sharing
 */

// Re-export everything from the modular API
export * from './api/index.js';

// Re-export the api object for backward compatibility with api.methodName() usage
export { api } from './api/index.js';

// Re-export error utilities for consumers that import them from api.js
export {
  parseAPIError,
  parseError,
  getUserFriendlyMessage,
  isRetryableError,
  NetworkError,
  AbortError,
  logError,
} from './utils/errors.js';

// Re-export retry utilities for consumers that import them from api.js
export { withRetry, withAPIRetry, withStreamRetry } from './utils/retry.js';
