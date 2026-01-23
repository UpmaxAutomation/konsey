/**
 * Batch Processing API.
 */

import { API_BASE, authFetch } from './client.js';

/**
 * Create and start a new batch processing job.
 * @param {Array<string>} questions - List of questions to process
 * @returns {Promise<Object>} Created batch job
 */
export async function createBatchJob(questions) {
  const response = await authFetch(`${API_BASE}/batch`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ questions }),
  });
  if (!response.ok) {
    throw new Error('Failed to create batch job');
  }
  return response.json();
}

/**
 * List all batch jobs.
 * @returns {Promise<Object>} List of batch jobs
 */
export async function listBatchJobs() {
  const response = await authFetch(`${API_BASE}/batch`);
  if (!response.ok) {
    throw new Error('Failed to list batch jobs');
  }
  return response.json();
}

/**
 * Get a specific batch job status and results.
 * @param {string} jobId - Batch job ID
 * @returns {Promise<Object>} Batch job details
 */
export async function getBatchJob(jobId) {
  const response = await authFetch(`${API_BASE}/batch/${jobId}`);
  if (!response.ok) {
    throw new Error('Failed to get batch job');
  }
  return response.json();
}

/**
 * Cancel/delete a batch job.
 * @param {string} jobId - Batch job ID
 * @returns {Promise<Object>} Deletion status
 */
export async function deleteBatchJob(jobId) {
  const response = await authFetch(`${API_BASE}/batch/${jobId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Failed to delete batch job');
  }
  return response.json();
}
