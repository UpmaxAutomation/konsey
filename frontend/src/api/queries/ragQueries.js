import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  embedDocument,
  embedAllDocuments,
  semanticSearch,
  getRAGStatus,
  deleteDocumentEmbeddings,
} from '../rag.js';

export const ragKeys = {
  status: (projectId) => ['rag', 'status', projectId],
  search: (projectId, query) => ['rag', 'search', projectId, query],
};

export function useRAGStatus(projectId) {
  return useQuery({
    queryKey: ragKeys.status(projectId),
    queryFn: () => getRAGStatus(projectId),
    enabled: !!projectId,
  });
}

export function useSemanticSearch(projectId, query, topK = 5) {
  return useQuery({
    queryKey: ragKeys.search(projectId, query),
    queryFn: () => semanticSearch(projectId, query, topK),
    enabled: !!projectId && !!query && query.length > 2,
  });
}

export function useEmbedDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, documentId }) => embedDocument(projectId, documentId),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ragKeys.status(projectId) });
    },
  });
}

export function useEmbedAll() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId }) => embedAllDocuments(projectId),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ragKeys.status(projectId) });
    },
  });
}

export function useDeleteDocumentEmbeddings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, documentId }) => deleteDocumentEmbeddings(projectId, documentId),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: ragKeys.status(projectId) });
    },
  });
}
