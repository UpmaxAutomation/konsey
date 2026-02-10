import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listTags,
  createTag,
  updateTag,
  deleteTag,
  getCardTags,
  addCardTag,
  removeCardTag,
} from '../tags.js';

export const tagKeys = {
  all: ['tags'],
  cardTags: (boardId, cardId) => ['tags', boardId, 'card', cardId],
};

export function useTags() {
  return useQuery({
    queryKey: tagKeys.all,
    queryFn: listTags,
  });
}

export function useCardTags(boardId, cardId) {
  return useQuery({
    queryKey: tagKeys.cardTags(boardId, cardId),
    queryFn: () => getCardTags(boardId, cardId),
    enabled: !!boardId && !!cardId,
  });
}

export function useCreateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createTag,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tagKeys.all }),
  });
}

export function useUpdateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ tagId, updates }) => updateTag(tagId, updates),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tagKeys.all }),
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteTag,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: tagKeys.all }),
  });
}

export function useAddCardTag(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cardId, tagId }) => addCardTag(boardId, cardId, tagId),
    onSuccess: (_, { cardId }) => {
      queryClient.invalidateQueries({ queryKey: tagKeys.cardTags(boardId, cardId) });
    },
  });
}

export function useRemoveCardTag(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cardId, tagId }) => removeCardTag(boardId, cardId, tagId),
    onSuccess: (_, { cardId }) => {
      queryClient.invalidateQueries({ queryKey: tagKeys.cardTags(boardId, cardId) });
    },
  });
}
