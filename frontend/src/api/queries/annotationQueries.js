import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '../annotations';

/**
 * Fetch all annotations for an attachment.
 * @param {string} attachmentId - Attachment UUID
 */
export function useAnnotations(attachmentId) {
  return useQuery({
    queryKey: ['annotations', attachmentId],
    queryFn: () => api.getAnnotations(attachmentId),
    enabled: !!attachmentId,
  });
}

/**
 * Mutation to add a new annotation.
 * @param {string} attachmentId - Attachment UUID
 */
export function useAddAnnotation(attachmentId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => api.addAnnotation(attachmentId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['annotations', attachmentId] });
      // Also invalidate card-attachments so the badge count updates
      qc.invalidateQueries({ queryKey: ['card-attachments'] });
    },
  });
}

/**
 * Mutation to update an existing annotation.
 * @param {string} attachmentId - Attachment UUID
 */
export function useUpdateAnnotation(attachmentId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ annotationId, ...data }) =>
      api.updateAnnotation(attachmentId, annotationId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['annotations', attachmentId] });
    },
  });
}

/**
 * Mutation to delete an annotation.
 * @param {string} attachmentId - Attachment UUID
 */
export function useDeleteAnnotation(attachmentId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (annotationId) => api.deleteAnnotation(attachmentId, annotationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['annotations', attachmentId] });
      qc.invalidateQueries({ queryKey: ['card-attachments'] });
    },
  });
}
