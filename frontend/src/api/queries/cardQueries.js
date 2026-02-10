import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createCard, updateCard, deleteCard } from '../boards.js';
import { boardKeys } from './boardQueries.js';

export const cardKeys = {
  all: (boardId) => ['cards', boardId],
};

export function useCreateCard(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (cardData) => createCard(boardId, cardData),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) }),
  });
}

export function useUpdateCard(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cardId, updates }) => updateCard(boardId, cardId, updates),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) }),
  });
}

export function useDeleteCard(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (cardId) => deleteCard(boardId, cardId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) }),
  });
}
