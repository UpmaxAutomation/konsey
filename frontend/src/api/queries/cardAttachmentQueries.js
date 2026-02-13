import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { uploadAttachment, addEmbed, listAttachments, deleteAttachment } from '../cardAttachments';

export function useCardAttachments(cardId) {
  return useQuery({
    queryKey: ['card-attachments', cardId],
    queryFn: () => listAttachments(cardId),
    enabled: !!cardId,
  });
}

export function useUploadAttachment(cardId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file) => uploadAttachment(cardId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['card-attachments', cardId] }),
  });
}

export function useAddEmbed(cardId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ url, title }) => addEmbed(cardId, url, title),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['card-attachments', cardId] }),
  });
}

export function useDeleteAttachment(cardId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (attachmentId) => deleteAttachment(attachmentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['card-attachments', cardId] }),
  });
}
