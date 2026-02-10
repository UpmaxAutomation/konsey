/**
 * Custom error classes and utilities for better error handling in the LLM Council frontend.
 * Provides structured error types and user-friendly error messages.
 */

/**
 * Base API error class with status code and error code support.
 * @extends Error
 */
export class APIError extends Error {
  /**
   * Create an API error.
   * @param {string} message - Error message
   * @param {number} status - HTTP status code
   * @param {string} code - Error code for programmatic handling
   * @param {Object} details - Additional error details
   */
  constructor(message, status = 0, code = 'API_ERROR', details = null) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.timestamp = new Date().toISOString();
  }

  /**
   * Check if this error is retryable.
   * @returns {boolean}
   */
  isRetryable() {
    return false;
  }

  /**
   * Convert to JSON for logging.
   * @returns {Object}
   */
  toJSON() {
    return {
      name: this.name,
      message: this.message,
      status: this.status,
      code: this.code,
      details: this.details,
      timestamp: this.timestamp,
    };
  }
}

/**
 * Network error for connection failures, timeouts, etc.
 * @extends APIError
 */
export class NetworkError extends APIError {
  /**
   * Create a network error.
   * @param {string} message - Error message
   * @param {Object} details - Additional error details
   */
  constructor(message = 'Network connection failed', details = null) {
    super(message, 0, 'NETWORK_ERROR', details);
    this.name = 'NetworkError';
  }

  isRetryable() {
    return true;
  }
}

/**
 * Rate limit error (HTTP 429).
 * @extends APIError
 */
export class RateLimitError extends APIError {
  /**
   * Create a rate limit error.
   * @param {string} message - Error message
   * @param {number} retryAfter - Seconds to wait before retry
   * @param {Object} details - Additional error details
   */
  constructor(message = 'Rate limit exceeded', retryAfter = null, details = null) {
    super(message, 429, 'RATE_LIMIT_ERROR', details);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }

  isRetryable() {
    return true;
  }
}

/**
 * Server error (HTTP 5xx).
 * @extends APIError
 */
export class ServerError extends APIError {
  /**
   * Create a server error.
   * @param {string} message - Error message
   * @param {number} status - HTTP status code (500-599)
   * @param {Object} details - Additional error details
   */
  constructor(message = 'Server error occurred', status = 500, details = null) {
    super(message, status, 'SERVER_ERROR', details);
    this.name = 'ServerError';
  }

  isRetryable() {
    return true;
  }
}

/**
 * Validation error for invalid input (HTTP 400, 422).
 * @extends APIError
 */
export class ValidationError extends APIError {
  /**
   * Create a validation error.
   * @param {string} message - Error message
   * @param {Array|Object} validationErrors - Validation error details
   */
  constructor(message = 'Validation failed', validationErrors = null) {
    super(message, 400, 'VALIDATION_ERROR', { validationErrors });
    this.name = 'ValidationError';
    this.validationErrors = validationErrors;
  }
}

/**
 * Authentication error (HTTP 401).
 * @extends APIError
 */
export class AuthenticationError extends APIError {
  /**
   * Create an authentication error.
   * @param {string} message - Error message
   */
  constructor(message = 'Authentication required') {
    super(message, 401, 'AUTHENTICATION_ERROR');
    this.name = 'AuthenticationError';
  }
}

/**
 * Authorization error (HTTP 403).
 * @extends APIError
 */
export class AuthorizationError extends APIError {
  /**
   * Create an authorization error.
   * @param {string} message - Error message
   */
  constructor(message = 'Access denied') {
    super(message, 403, 'AUTHORIZATION_ERROR');
    this.name = 'AuthorizationError';
  }
}

/**
 * Not found error (HTTP 404).
 * @extends APIError
 */
export class NotFoundError extends APIError {
  /**
   * Create a not found error.
   * @param {string} message - Error message
   * @param {string} resource - The resource that was not found
   */
  constructor(message = 'Resource not found', resource = null) {
    super(message, 404, 'NOT_FOUND_ERROR', { resource });
    this.name = 'NotFoundError';
    this.resource = resource;
  }
}

/**
 * Timeout error for request timeouts.
 * @extends APIError
 */
export class TimeoutError extends APIError {
  /**
   * Create a timeout error.
   * @param {string} message - Error message
   * @param {number} timeout - The timeout duration in milliseconds
   */
  constructor(message = 'Request timed out', timeout = null) {
    super(message, 0, 'TIMEOUT_ERROR', { timeout });
    this.name = 'TimeoutError';
  }

  isRetryable() {
    return true;
  }
}

/**
 * Abort error for cancelled requests.
 * @extends APIError
 */
export class AbortError extends APIError {
  /**
   * Create an abort error.
   * @param {string} message - Error message
   */
  constructor(message = 'Request was cancelled') {
    super(message, 0, 'ABORT_ERROR');
    this.name = 'AbortError';
  }

  isRetryable() {
    return false;
  }
}

/**
 * Budget exceeded error for cost limits.
 * @extends APIError
 */
export class BudgetExceededError extends APIError {
  /**
   * Create a budget exceeded error.
   * @param {string} message - Error message
   * @param {Object} budgetDetails - Budget limit details
   */
  constructor(message = 'Budget limit exceeded', budgetDetails = null) {
    super(message, 402, 'BUDGET_EXCEEDED_ERROR', budgetDetails);
    this.name = 'BudgetExceededError';
  }
}

/**
 * Parse an API response and return the appropriate error type.
 * @param {Response} response - Fetch Response object
 * @param {Object|string} data - Parsed response data (optional)
 * @returns {APIError} The appropriate error class instance
 */
export function parseAPIError(response, data = null) {
  const status = response?.status || 0;
  const statusText = response?.statusText || 'Unknown error';

  // Extract error message from response data
  let message = statusText;
  let details = null;
  let code = null;

  if (data) {
    if (typeof data === 'string') {
      message = data;
    } else if (typeof data === 'object') {
      message = data.detail || data.message || data.error || statusText;
      details = data.details || data;
      code = data.code || data.error_code;
    }
  }

  // Extract retry-after header for rate limits
  const retryAfter = response?.headers?.get('Retry-After');

  // Return appropriate error type based on status code
  switch (status) {
    case 400:
    case 422:
      return new ValidationError(message, details?.validationErrors || details);

    case 401:
      return new AuthenticationError(message);

    case 402:
      return new BudgetExceededError(message, details);

    case 403:
      return new AuthorizationError(message);

    case 404:
      return new NotFoundError(message, details?.resource);

    case 429:
      return new RateLimitError(
        message,
        retryAfter ? parseInt(retryAfter, 10) : null,
        details
      );

    case 500:
    case 502:
    case 503:
    case 504:
      return new ServerError(message, status, details);

    default:
      if (status >= 500) {
        return new ServerError(message, status, details);
      }
      return new APIError(message, status, code || 'API_ERROR', details);
  }
}

/**
 * Parse a caught error (from fetch or other operations) into an APIError.
 * @param {Error} error - The caught error
 * @returns {APIError} The appropriate error class instance
 */
export function parseError(error) {
  // Already an APIError
  if (error instanceof APIError) {
    return error;
  }

  // Abort error from AbortController
  if (error.name === 'AbortError') {
    return new AbortError('Request was cancelled');
  }

  // Network error (failed to fetch)
  if (error instanceof TypeError && error.message.includes('fetch')) {
    return new NetworkError('Failed to connect to server. Please check your connection.');
  }

  // Timeout
  if (error.name === 'TimeoutError' || error.message.includes('timeout')) {
    return new TimeoutError(error.message);
  }

  // Generic error
  return new APIError(error.message || 'An unexpected error occurred', 0, 'UNKNOWN_ERROR');
}

/**
 * Get a user-friendly error message from an error object.
 * @param {Error} error - Any error object
 * @returns {string} A user-friendly error message
 */
export function getUserFriendlyMessage(error) {
  // Parse to APIError if not already
  const apiError = error instanceof APIError ? error : parseError(error);

  // Network errors - provide detailed help
  if (apiError instanceof NetworkError) {
    if (apiError.details?.suggestion) {
      return `${apiError.message}\n\n💡 ${apiError.details.suggestion}`;
    }
    if (apiError.details?.timeout) {
      return `${apiError.message}\n\nThe server may be overloaded or unreachable. Please check if the backend is running.`;
    }
    // Check if it's a localhost connection issue
    if (apiError.details?.url?.includes('localhost') || apiError.details?.url?.includes('127.0.0.1')) {
      return `${apiError.message}\n\n💡 Make sure the backend server is running:\ncd backend && python -m uvicorn main:app --reload --port 8001`;
    }
    return apiError.message || 'Unable to connect to the server. Please check your internet connection and try again.';
  }

  // User-friendly messages based on error type
  const friendlyMessages = {
    RateLimitError: apiError.retryAfter
      ? `Too many requests. Please wait ${apiError.retryAfter} seconds before trying again.`
      : 'Too many requests. Please wait a moment before trying again.',
    ServerError: 'The server is experiencing issues. Please try again in a few moments.',
    ValidationError: apiError.message || 'Please check your input and try again.',
    AuthenticationError: 'Your session has expired. Please log in again.',
    AuthorizationError: 'You do not have permission to perform this action.',
    NotFoundError: apiError.resource
      ? `The requested ${apiError.resource} could not be found.`
      : 'The requested resource could not be found.',
    TimeoutError: 'The request took too long. Please try again.',
    AbortError: 'The request was cancelled.',
    BudgetExceededError: 'Budget limit exceeded. Please adjust your budget settings or wait for the next period.',
  };

  return friendlyMessages[apiError.name] || apiError.message || 'An unexpected error occurred. Please try again.';
}

/**
 * Check if an error is retryable.
 * @param {Error} error - Any error object
 * @returns {boolean} Whether the error is retryable
 */
export function isRetryableError(error) {
  // Parse to APIError if not already
  const apiError = error instanceof APIError ? error : parseError(error);
  return apiError.isRetryable();
}

/**
 * Log an error with context for debugging.
 * @param {Error} error - Any error object
 * @param {string} context - Context description (e.g., function name)
 * @param {Object} additionalData - Additional data to log
 */
export function logError(error, context = '', additionalData = null) {
  const apiError = error instanceof APIError ? error : parseError(error);

  const logData = {
    context,
    error: apiError.toJSON ? apiError.toJSON() : {
      name: error.name,
      message: error.message,
      stack: error.stack,
    },
    ...additionalData,
  };

  // Use console.error for visibility
  console.error(`[${context || 'API Error'}]`, logData);

  return logData;
}
