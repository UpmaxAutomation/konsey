/**
 * Connection check utility to verify backend availability.
 */

import { API_BASE } from '../api/client.js';

let connectionStatus = null;
let lastCheck = null;
const CHECK_INTERVAL = 30000; // Check every 30 seconds
const CACHE_DURATION = 5000; // Cache result for 5 seconds

/**
 * Check if the backend is reachable.
 * @returns {Promise<boolean>} True if backend is reachable
 */
export async function checkConnection() {
  // Use cached result if recent
  if (connectionStatus !== null && lastCheck && Date.now() - lastCheck < CACHE_DURATION) {
    return connectionStatus;
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5s timeout for health check

    // Check root endpoint (not /api/) - backend root is at /
    const baseUrl = API_BASE.replace('/api', '');
    const response = await fetch(`${baseUrl}/`, {
      method: 'GET',
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    clearTimeout(timeoutId);
    connectionStatus = response.ok;
    lastCheck = Date.now();
    return connectionStatus;
  } catch (error) {
    connectionStatus = false;
    lastCheck = Date.now();
    return false;
  }
}

/**
 * Get connection status (cached).
 * @returns {boolean|null} Connection status or null if not checked yet
 */
export function getConnectionStatus() {
  return connectionStatus;
}

/**
 * Reset connection status cache.
 */
export function resetConnectionStatus() {
  connectionStatus = null;
  lastCheck = null;
}
