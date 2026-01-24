/**
 * Base API client with authentication and error handling.
 * All other API modules import from this file.
 */

import { withRetry, withAPIRetry, withStreamRetry } from '../utils/retry.js';
import {
  parseAPIError,
  parseError,
  getUserFriendlyMessage,
  isRetryableError,
  NetworkError,
  AbortError,
  logError,
} from '../utils/errors.js';

// Get API base URL - Vite env vars are available at build time
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
// Remove trailing slash and add /api if not present
export const API_BASE = BASE_URL.replace(/\/$/, '') + (BASE_URL.includes('/api') ? '' : '/api');

// Debug logging in production
if (import.meta.env.PROD) {
  console.log('🔍 API Configuration:', {
    VITE_API_URL: import.meta.env.VITE_API_URL,
    BASE_URL,
    API_BASE,
    mode: import.meta.env.MODE
  });
}

/**
 * Parse response and throw appropriate error if not OK.
 * @param {Response} response - Fetch response
 * @param {string} context - Context for error logging
 * @returns {Promise<Response>} The response if OK
 * @throws {APIError} Appropriate error type if response not OK
 */
export async function handleResponse(response, context = 'API call') {
  if (response.ok) {
    return response;
  }

  // Try to parse error body
  let data = null;
  try {
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }
  } catch (e) {
    // Ignore parse errors
  }

  const error = parseAPIError(response, data);
  logError(error, context, { url: response.url, status: response.status });
  throw error;
}

/**
 * Safe fetch wrapper that converts network errors to proper error types.
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @param {string} context - Context for error logging
 * @returns {Promise<Response>} Fetch response
 * @throws {NetworkError|AbortError} On network or abort errors
 */
export async function safeFetch(url, options = {}, context = 'fetch') {
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'cors-debug',hypothesisId:'H1',location:'client.js:70',message:'safeFetch:entry',data:{url,method:options.method || 'GET',origin:window.location.origin,apiBase:API_BASE},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), options.timeout || 30000); // 30s default timeout
    
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'cors-debug',hypothesisId:'H1',location:'client.js:81',message:'safeFetch:beforeFetch',data:{url,headers:Object.keys(options.headers || {})},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'cors-debug',hypothesisId:'H1',location:'client.js:87',message:'safeFetch:response',data:{url,status:response.status,ok:response.ok,headers:Object.fromEntries(response.headers.entries())},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'cors-debug',hypothesisId:'H1',location:'client.js:92',message:'safeFetch:error',data:{url,name:error?.name,message:error?.message,stack:error?.stack?.substring(0,200),isCORS:error?.message?.includes('CORS') || error?.message?.includes('Access-Control')},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    // Handle abort (timeout or manual)
    if (error.name === 'AbortError') {
      if (error.message?.includes('timeout') || !error.message) {
        throw new NetworkError(
          'Connection timeout. The server may be slow or unreachable. Please try again.',
          { originalError: error.message, url, timeout: true }
        );
      }
      throw new AbortError('Request was cancelled');
    }

    // Handle network errors (connection refused, DNS failure, etc.)
    if (error instanceof TypeError) {
      const isLocalhost = url.includes('localhost') || url.includes('127.0.0.1');
      const errorMessage = isLocalhost
        ? 'Cannot connect to server. Make sure the backend is running on http://localhost:8001'
        : 'Failed to connect to server. Please check your internet connection and try again.';
      
      throw new NetworkError(
        errorMessage,
        { 
          originalError: error.message, 
          url,
          suggestion: isLocalhost 
            ? 'Start the backend server with: cd backend && python -m uvicorn main:app --reload --port 8001'
            : 'Check if the server is running and accessible'
        }
      );
    }

    // Re-throw other errors
    throw parseError(error);
  }
}

/**
 * Get authorization headers with access token.
 */
export function getAuthHeaders() {
  const headers = {
    'Content-Type': 'application/json',
  };
  const token = localStorage.getItem('access_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Attempt to refresh the access token.
 */
export async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) {
    throw new Error('No refresh token');
  }

  try {
    const response = await safeFetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
      timeout: 10000, // 10s timeout for refresh
    });

    if (!response.ok) {
      // Refresh failed, clear tokens and redirect to login
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data.access_token;
  } catch (error) {
    // If it's a network error, don't redirect - let the user see the connection issue
    if (error instanceof NetworkError) {
      throw error;
    }
    // For other errors, redirect to login
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
    throw new Error('Token refresh failed');
  }
}

/**
 * Make an authenticated fetch request with automatic token refresh.
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @param {string} context - Context for error logging
 * @returns {Promise<Response>} Fetch response
 */
export async function authFetch(url, options = {}, context = 'authFetch') {
  const headers = { ...getAuthHeaders(), ...options.headers };
  let response = await safeFetch(url, { ...options, headers }, context);
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H4',location:'client.js:171',message:'authFetch:response',data:{url,status:response.status,hasToken:Boolean(localStorage.getItem('access_token'))},timestamp:Date.now()})}).catch(()=>{});
  // #endregion

  // If unauthorized, try refreshing the token
  if (response.status === 401) {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'auth-401','hypothesisId':'H44',location:'client.js:200',message:'auth_401_detected',data:{url,hasToken:Boolean(localStorage.getItem('access_token'))},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    try {
      await refreshAccessToken();
      // Retry with new token
      const newHeaders = { ...getAuthHeaders(), ...options.headers };
      response = await safeFetch(url, { ...options, headers: newHeaders }, context);
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H4',location:'client.js:179',message:'authFetch:retryAfterRefresh',data:{url,status:response.status},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      
      // If still 401 after refresh, only redirect if not a streaming request
      if (response.status === 401) {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'auth-401-failed','hypothesisId':'H45',location:'client.js:212',message:'auth_401_after_refresh',data:{url,isStream:url.includes('/stream')},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        // Don't redirect for streaming requests - let the error handler deal with it
        if (!url.includes('/stream')) {
          window.location.href = '/login';
        }
        throw new Error('Session expired. Please log in again.');
      }
    } catch (err) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'auth-refresh-error','hypothesisId':'H46',location:'client.js:218',message:'auth_refresh_exception',data:{url,error:err.message,isStream:url.includes('/stream')},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      // If refresh failed, only redirect if not a streaming request
      if (err.message.includes('Token refresh failed') || err.message.includes('No refresh token')) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        // Don't redirect for streaming requests - let the error handler deal with it
        if (!url.includes('/stream')) {
          window.location.href = '/login';
        }
      }
      throw parseError(err);
    }
  }

  // Handle 403 Forbidden - user doesn't have permission
  if (response.status === 403) {
    const error = await parseAPIError(response, null);
    error.message = error.message || 'You do not have permission to perform this action.';
    throw error;
  }

  return response;
}

// Re-export utilities that may be needed by other modules
export {
  withRetry,
  withAPIRetry,
  withStreamRetry,
  parseAPIError,
  parseError,
  getUserFriendlyMessage,
  isRetryableError,
  NetworkError,
  AbortError,
  logError,
};
