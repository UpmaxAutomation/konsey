/**
 * Annotations API module for PDF highlight/comment annotations.
 */

import { API_BASE, authFetch } from './client.js';

/**
 * Get all annotations for an attachment.
 * @param {string} attachmentId - The attachment UUID
 * @returns {Promise<Array>} List of annotation objects
 */
export async function getAnnotations(attachmentId) {
  const response = await authFetch(`${API_BASE}/attachments/${attachmentId}/annotations`);
  if (!response.ok) throw new Error('Failed to get annotations');
  return response.json();
}

/**
 * Add a new annotation to an attachment.
 * @param {string} attachmentId - The attachment UUID
 * @param {Object} data - Annotation data
 * @param {number} data.page - Page number
 * @param {string} data.type - Annotation type (highlight, comment, etc.)
 * @param {string} data.content - Annotation text content
 * @param {Array} data.rects - Array of {x, y, width, height} rectangles
 * @param {string} [data.color] - Highlight color (default #FFEB3B)
 * @returns {Promise<Object>} Created annotation
 */
export async function addAnnotation(attachmentId, { page, type, content, rects, color }) {
  const response = await authFetch(`${API_BASE}/attachments/${attachmentId}/annotations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ page, type, content, rects, color }),
  });
  if (!response.ok) throw new Error('Failed to add annotation');
  return response.json();
}

/**
 * Update an existing annotation.
 * @param {string} attachmentId - The attachment UUID
 * @param {string} annotationId - The annotation UUID
 * @param {Object} data - Fields to update (content, color)
 * @returns {Promise<Object>} Updated annotation
 */
export async function updateAnnotation(attachmentId, annotationId, data) {
  const response = await authFetch(
    `${API_BASE}/attachments/${attachmentId}/annotations/${annotationId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }
  );
  if (!response.ok) throw new Error('Failed to update annotation');
  return response.json();
}

/**
 * Delete an annotation.
 * @param {string} attachmentId - The attachment UUID
 * @param {string} annotationId - The annotation UUID
 * @returns {Promise<void>}
 */
export async function deleteAnnotation(attachmentId, annotationId) {
  const response = await authFetch(
    `${API_BASE}/attachments/${attachmentId}/annotations/${annotationId}`,
    { method: 'DELETE' }
  );
  if (!response.ok) throw new Error('Failed to delete annotation');
}
