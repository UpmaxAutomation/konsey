/**
 * Retry utilities with exponential backoff for the LLM Council frontend.
 * Provides robust retry logic for handling transient failures.
 */

import {
  isRetryableError,
  RateLimitError,
  TimeoutError,
  NetworkError,
  AbortError,
  parseError,
  logError,
} from './errors.js';

/**
 * Default retry configuration.
 * @type {Object}
 */
export const DEFAULT_RETRY_OPTIONS = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 10000,
  backoffMultiplier: 2,
  jitterFactor: 0.1,
  shouldRetry: isRetryableError,
  onRetry: null,
  timeout: 0, // 0 = no timeout
};

/**
 * Calculate delay for the next retry attempt with exponential backoff and jitter.
 * @param {number} attempt - Current attempt number (0-indexed)
 * @param {Object} options - Retry options
 * @returns {number} Delay in milliseconds
 */
export function calculateBackoff(attempt, options = {}) {
  const {
    initialDelay = DEFAULT_RETRY_OPTIONS.initialDelay,
    maxDelay = DEFAULT_RETRY_OPTIONS.maxDelay,
    backoffMultiplier = DEFAULT_RETRY_OPTIONS.backoffMultiplier,
    jitterFactor = DEFAULT_RETRY_OPTIONS.jitterFactor,
  } = options;

  // Exponential backoff: initialDelay * (multiplier ^ attempt)
  let delay = initialDelay * Math.pow(backoffMultiplier, attempt);

  // Cap at maxDelay
  delay = Math.min(delay, maxDelay);

  // Add jitter to prevent thundering herd
  if (jitterFactor > 0) {
    const jitter = delay * jitterFactor * (Math.random() * 2 - 1);
    delay = Math.max(0, delay + jitter);
  }

  return Math.round(delay);
}

/**
 * Sleep for a specified duration.
 * @param {number} ms - Duration in milliseconds
 * @param {AbortSignal} signal - Optional abort signal
 * @returns {Promise<void>}
 */
export function sleep(ms, signal = null) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(resolve, ms);

    if (signal) {
      signal.addEventListener('abort', () => {
        clearTimeout(timeout);
        reject(new AbortError('Sleep was aborted'));
      });
    }
  });
}

/**
 * Execute a function with retry logic and exponential backoff.
 * @param {Function} fn - Async function to execute
 * @param {Object} options - Retry options
 * @param {number} options.maxRetries - Maximum retry attempts (default: 3)
 * @param {number} options.initialDelay - Initial delay in ms (default: 1000)
 * @param {number} options.maxDelay - Maximum delay in ms (default: 10000)
 * @param {number} options.backoffMultiplier - Backoff multiplier (default: 2)
 * @param {number} options.jitterFactor - Jitter factor 0-1 (default: 0.1)
 * @param {Function} options.shouldRetry - Function to check if error is retryable
 * @param {Function} options.onRetry - Callback called before each retry (attempt, error, delay)
 * @param {number} options.timeout - Request timeout in ms (0 = no timeout)
 * @param {AbortSignal} options.signal - Abort signal for cancellation
 * @returns {Promise<*>} Result of the function
 * @throws {Error} The last error if all retries fail
 */
export async function withRetry(fn, options = {}) {
  const config = { ...DEFAULT_RETRY_OPTIONS, ...options };
  const {
    maxRetries,
    shouldRetry,
    onRetry,
    signal,
  } = config;

  let lastError = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    // Check if aborted before each attempt
    if (signal?.aborted) {
      throw new AbortError('Request was cancelled');
    }

    try {
      // Execute the function
      const result = await fn();
      return result;
    } catch (error) {
      lastError = parseError(error);

      // Don't retry abort errors
      if (lastError instanceof AbortError) {
        throw lastError;
      }

      // Check if we should retry
      const canRetry = attempt < maxRetries && shouldRetry(lastError);

      if (!canRetry) {
        // Log the final error
        logError(lastError, 'withRetry', { attempt, maxRetries });
        throw lastError;
      }

      // Calculate delay (respect rate limit retry-after header)
      let delay;
      if (lastError instanceof RateLimitError && lastError.retryAfter) {
        // Use the server-specified retry-after value (in seconds)
        delay = lastError.retryAfter * 1000;
      } else {
        delay = calculateBackoff(attempt, config);
      }

      // Call onRetry callback if provided
      if (onRetry) {
        try {
          await onRetry(attempt, lastError, delay);
        } catch (callbackError) {
          console.warn('onRetry callback error:', callbackError);
        }
      }

      // Log retry attempt
      console.log(`[Retry] Attempt ${attempt + 1}/${maxRetries} failed, retrying in ${delay}ms...`, {
        error: lastError.message,
        code: lastError.code,
      });

      // Wait before retrying
      await sleep(delay, signal);
    }
  }

  // Should never reach here, but just in case
  throw lastError || new Error('Retry failed with unknown error');
}

/**
 * Create a retry wrapper with preset configuration.
 * Useful for creating domain-specific retry functions.
 * @param {Object} defaultOptions - Default options for all retries
 * @returns {Function} A withRetry function with preset options
 */
export function createRetryWrapper(defaultOptions = {}) {
  return (fn, options = {}) => withRetry(fn, { ...defaultOptions, ...options });
}

/**
 * Retry wrapper optimized for API calls with longer timeouts.
 */
export const withAPIRetry = createRetryWrapper({
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 15000,
});

/**
 * Retry wrapper for streaming requests (fewer retries, shorter delays).
 */
export const withStreamRetry = createRetryWrapper({
  maxRetries: 2,
  initialDelay: 500,
  maxDelay: 5000,
});

/**
 * Retry wrapper for critical operations (more retries, longer delays).
 */
export const withCriticalRetry = createRetryWrapper({
  maxRetries: 5,
  initialDelay: 2000,
  maxDelay: 30000,
});

/**
 * Execute multiple functions with retry, collecting all results.
 * @param {Array<Function>} fns - Array of async functions to execute
 * @param {Object} options - Retry options
 * @returns {Promise<Array>} Array of results (or errors for failed attempts)
 */
export async function withRetryAll(fns, options = {}) {
  const results = await Promise.allSettled(
    fns.map(fn => withRetry(fn, options))
  );

  return results.map((result, index) => ({
    index,
    success: result.status === 'fulfilled',
    value: result.status === 'fulfilled' ? result.value : null,
    error: result.status === 'rejected' ? result.reason : null,
  }));
}

/**
 * Execute a function with timeout.
 * @param {Function} fn - Async function to execute
 * @param {number} timeout - Timeout in milliseconds
 * @param {AbortSignal} signal - Optional abort signal
 * @returns {Promise<*>} Result of the function
 * @throws {TimeoutError} If the operation times out
 */
export async function withTimeout(fn, timeout, signal = null) {
  if (!timeout || timeout <= 0) {
    return fn();
  }

  const controller = new AbortController();
  const combinedSignal = signal
    ? AbortSignal.any([signal, controller.signal])
    : controller.signal;

  const timeoutId = setTimeout(() => {
    controller.abort();
  }, timeout);

  try {
    const result = await fn(combinedSignal);
    clearTimeout(timeoutId);
    return result;
  } catch (error) {
    clearTimeout(timeoutId);

    // Convert abort from timeout to TimeoutError
    if (error.name === 'AbortError' && !signal?.aborted) {
      throw new TimeoutError(`Operation timed out after ${timeout}ms`, timeout);
    }

    throw error;
  }
}

/**
 * Combine retry and timeout for robust operation execution.
 * @param {Function} fn - Async function to execute
 * @param {Object} options - Options including retry and timeout settings
 * @returns {Promise<*>} Result of the function
 */
export async function withRetryAndTimeout(fn, options = {}) {
  const { timeout = 30000, signal, ...retryOptions } = options;

  return withRetry(
    () => withTimeout(fn, timeout, signal),
    { ...retryOptions, signal }
  );
}

/**
 * Create a debounced retry function that prevents rapid retries.
 * @param {Function} fn - Async function to execute
 * @param {number} debounceMs - Minimum time between attempts in ms
 * @param {Object} options - Retry options
 * @returns {Function} Debounced retry function
 */
export function createDebouncedRetry(fn, debounceMs = 1000, options = {}) {
  let lastAttempt = 0;
  let pendingPromise = null;

  return async (...args) => {
    const now = Date.now();
    const timeSinceLastAttempt = now - lastAttempt;

    // If within debounce window and we have a pending promise, return it
    if (timeSinceLastAttempt < debounceMs && pendingPromise) {
      return pendingPromise;
    }

    lastAttempt = now;
    pendingPromise = withRetry(() => fn(...args), options);

    try {
      return await pendingPromise;
    } finally {
      pendingPromise = null;
    }
  };
}
