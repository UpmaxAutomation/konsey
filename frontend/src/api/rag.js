/**
 * RAG (Retrieval-Augmented Generation) API module.
 */

import { API_BASE, authFetch } from './client.js';

export async function embedDocument(projectId, documentId) {
  const response = await authFetch(`${API_BASE}/rag/embed`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, document_id: documentId }),
  });
  if (!response.ok) throw new Error('Failed to embed document');
  return response.json();
}

export async function embedAllDocuments(projectId) {
  const response = await authFetch(`${API_BASE}/rag/embed-all`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId }),
  });
  if (!response.ok) throw new Error('Failed to embed all documents');
  return response.json();
}

export async function semanticSearch(projectId, query, topK = 5) {
  const response = await authFetch(`${API_BASE}/rag/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_id: projectId, query, top_k: topK }),
  });
  if (!response.ok) throw new Error('Failed to perform semantic search');
  return response.json();
}

export async function getRAGStatus(projectId) {
  const response = await authFetch(`${API_BASE}/rag/status/${projectId}`);
  if (!response.ok) throw new Error('Failed to get RAG status');
  return response.json();
}

export async function deleteDocumentEmbeddings(projectId, documentId) {
  const response = await authFetch(`${API_BASE}/rag/${projectId}/${documentId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('Failed to delete embeddings');
  return response.json();
}
