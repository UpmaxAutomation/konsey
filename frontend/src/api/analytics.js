/**
 * Analytics API - Usage analytics and reporting.
 */

import { API_BASE, authFetch } from './client.js';

/**
 * Get comprehensive analytics overview.
 */
export async function getAnalyticsOverview() {
  const response = await authFetch(`${API_BASE}/analytics/overview`);
  if (!response.ok) {
    throw new Error('Failed to get analytics overview');
  }
  return response.json();
}

/**
 * Get per-model analytics.
 */
export async function getModelAnalytics() {
  const response = await authFetch(`${API_BASE}/analytics/models`);
  if (!response.ok) {
    throw new Error('Failed to get model analytics');
  }
  return response.json();
}

/**
 * Get conversation analytics.
 */
export async function getConversationAnalytics() {
  const response = await authFetch(`${API_BASE}/analytics/conversations`);
  if (!response.ok) {
    throw new Error('Failed to get conversation analytics');
  }
  return response.json();
}

/**
 * Export full analytics data.
 */
export async function exportAnalytics() {
  const response = await authFetch(`${API_BASE}/analytics/export`);
  if (!response.ok) {
    throw new Error('Failed to export analytics');
  }
  return response.json();
}
