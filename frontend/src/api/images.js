/**
 * Image Generation API.
 */

import { API_BASE, authFetch } from './client.js';

/**
 * Generate an image using AI.
 * @param {Object} params - Image generation parameters
 * @param {string} params.prompt - Text prompt for the image
 * @param {string} params.provider - Provider (dalle-3, dalle-2, sdxl, flux)
 * @param {string} params.size - Image size (1024x1024, 1792x1024, 1024x1792)
 * @param {string} params.quality - Quality (standard, hd)
 * @param {string} params.style - Style (vivid, natural)
 * @returns {Promise<Object>} Generated image with URL or base64
 */
export async function generateImage({ prompt, provider = 'dalle-3', size = '1024x1024', quality = 'standard', style = 'vivid' }) {
  const response = await authFetch(`${API_BASE}/images/generate`, {
    method: 'POST',
    body: JSON.stringify({ prompt, provider, size, quality, style }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate image');
  }
  return response.json();
}

/**
 * Get available image generation providers.
 * @returns {Promise<Object>} List of providers with their capabilities
 */
export async function getImageProviders() {
  const response = await fetch(`${API_BASE}/images/providers`);
  if (!response.ok) {
    throw new Error('Failed to get image providers');
  }
  return response.json();
}

/**
 * List all generated images.
 * @param {number} limit - Maximum number of images
 * @returns {Promise<Object>} List of generated images
 */
export async function listImages(limit = 50) {
  const response = await authFetch(`${API_BASE}/images?limit=${limit}`);
  if (!response.ok) {
    throw new Error('Failed to list images');
  }
  return response.json();
}

/**
 * Get a specific generated image.
 * @param {string} imageId - Image ID
 * @returns {Promise<Object>} Image details
 */
export async function getImage(imageId) {
  const response = await authFetch(`${API_BASE}/images/${imageId}`);
  if (!response.ok) {
    throw new Error('Failed to get image');
  }
  return response.json();
}

/**
 * Delete a generated image.
 * @param {string} imageId - Image ID
 * @returns {Promise<Object>} Deletion status
 */
export async function deleteImage(imageId) {
  const response = await authFetch(`${API_BASE}/images/${imageId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete image');
  }
  return response.json();
}
