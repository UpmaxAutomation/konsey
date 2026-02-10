import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listPropertyDefinitions,
  createPropertyDefinition,
  updatePropertyDefinition,
  deletePropertyDefinition,
  getCardProperties,
  bulkSetCardProperties,
  getAllPropertyValues,
} from '../properties.js';
import { boardKeys } from './boardQueries.js';

export const propertyKeys = {
  definitions: (boardId) => ['properties', boardId],
  allValues: (boardId) => ['properties', boardId, 'all-values'],
  cardValues: (boardId, cardId) => ['properties', boardId, 'card', cardId],
};

export function usePropertyDefinitions(boardId) {
  return useQuery({
    queryKey: propertyKeys.definitions(boardId),
    queryFn: () => listPropertyDefinitions(boardId),
    enabled: !!boardId,
  });
}

export function useAllPropertyValues(boardId) {
  return useQuery({
    queryKey: propertyKeys.allValues(boardId),
    queryFn: () => getAllPropertyValues(boardId),
    enabled: !!boardId,
  });
}

export function useCardProperties(boardId, cardId) {
  return useQuery({
    queryKey: propertyKeys.cardValues(boardId, cardId),
    queryFn: () => getCardProperties(boardId, cardId),
    enabled: !!boardId && !!cardId,
  });
}

export function useCreatePropertyDefinition(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => createPropertyDefinition(boardId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: propertyKeys.definitions(boardId) });
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) });
    },
  });
}

export function useUpdatePropertyDefinition(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ propId, updates }) => updatePropertyDefinition(boardId, propId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: propertyKeys.definitions(boardId) });
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) });
    },
  });
}

export function useDeletePropertyDefinition(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (propId) => deletePropertyDefinition(boardId, propId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: propertyKeys.definitions(boardId) });
      queryClient.invalidateQueries({ queryKey: propertyKeys.allValues(boardId) });
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) });
    },
  });
}

export function useBulkSetCardProperties(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ cardId, values }) => bulkSetCardProperties(boardId, cardId, values),
    onSuccess: (_, { cardId }) => {
      queryClient.invalidateQueries({ queryKey: propertyKeys.cardValues(boardId, cardId) });
      queryClient.invalidateQueries({ queryKey: propertyKeys.allValues(boardId) });
    },
  });
}
