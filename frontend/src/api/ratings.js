/**
 * Ratings API - Model rating system.
 */

import { API_BASE, authFetch } from './client.js';

/**
 * Submit a rating for a model's response.
 * @param {Object} ratingData - Rating data
 * @param {string} ratingData.conversation_id - Conversation ID
 * @param {number} ratingData.message_index - Message index
 * @param {string} ratingData.model_id - Model ID
 * @param {number} ratingData.rating - Rating (1-5)
 * @param {string} ratingData.feedback_text - Optional feedback text
 * @param {string} ratingData.query_category - Optional category
 * @returns {Promise<Object>} Submission status
 */
export async function submitRating({ conversation_id, message_index, model_id, rating, feedback_text, query_category }) {
  const response = await authFetch(`${API_BASE}/ratings`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      conversation_id,
      message_index,
      model_id,
      rating,
      feedback_text: feedback_text || null,
      query_category: query_category || 'general',
    }),
  });
  if (!response.ok) {
    throw new Error('Failed to submit rating');
  }
  return response.json();
}

/**
 * Get existing rating for a specific response.
 * @param {string} conversationId - Conversation ID
 * @param {number} messageIndex - Message index
 * @param {string} modelId - Model ID
 * @returns {Promise<Object>} Rating data or {has_rating: false}
 */
export async function getRating(conversationId, messageIndex, modelId) {
  const response = await authFetch(
    `${API_BASE}/ratings/${conversationId}/${messageIndex}/${encodeURIComponent(modelId)}`
  );
  if (!response.ok) {
    throw new Error('Failed to get rating');
  }
  return response.json();
}

/**
 * Get rating statistics for all models.
 * @returns {Promise<Object>} Model rating statistics
 */
export async function getModelRatings() {
  const response = await authFetch(`${API_BASE}/ratings/models`);
  if (!response.ok) {
    throw new Error('Failed to get model ratings');
  }
  return response.json();
}

/**
 * Get model recommendations based on query.
 * @param {string} query - User query
 * @param {number} numRecommendations - Number of recommendations (default: 3)
 * @returns {Promise<Object>} Recommended models
 */
export async function getRatingRecommendations(query, numRecommendations = 3) {
  const response = await authFetch(
    `${API_BASE}/ratings/recommendations?query=${encodeURIComponent(query)}&num_recommendations=${numRecommendations}`
  );
  if (!response.ok) {
    throw new Error('Failed to get recommendations');
  }
  return response.json();
}

/**
 * Get comprehensive rating analytics.
 * @returns {Promise<Object>} Rating analytics summary
 */
export async function getRatingAnalytics() {
  const response = await authFetch(`${API_BASE}/ratings/analytics`);
  if (!response.ok) {
    throw new Error('Failed to get rating analytics');
  }
  return response.json();
}

/**
 * Clear all rating data.
 * @returns {Promise<Object>} Clear status
 */
export async function clearRatings() {
  const response = await authFetch(`${API_BASE}/ratings/clear`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Failed to clear ratings');
  }
  return response.json();
}
