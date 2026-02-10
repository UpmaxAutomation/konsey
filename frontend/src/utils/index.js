/**
 * Utility exports for the LLM Council frontend.
 * Provides centralized access to error handling and retry utilities.
 */

// Error classes and utilities
export {
  // Base error class
  APIError,
  // Specific error types
  NetworkError,
  RateLimitError,
  ServerError,
  ValidationError,
  AuthenticationError,
  AuthorizationError,
  NotFoundError,
  TimeoutError,
  AbortError,
  BudgetExceededError,
  // Utility functions
  parseAPIError,
  parseError,
  getUserFriendlyMessage,
  isRetryableError,
  logError,
} from './errors.js';

// Retry utilities
export {
  // Main retry functions
  withRetry,
  withAPIRetry,
  withStreamRetry,
  withCriticalRetry,
  // Timeout utilities
  withTimeout,
  withRetryAndTimeout,
  // Batch operations
  withRetryAll,
  // Helper utilities
  calculateBackoff,
  sleep,
  createRetryWrapper,
  createDebouncedRetry,
  // Configuration
  DEFAULT_RETRY_OPTIONS,
} from './retry.js';
