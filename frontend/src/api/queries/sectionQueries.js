import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listSections, createSection, updateSection, deleteSection } from '../boards.js';
import { boardKeys } from './boardQueries.js';

export const sectionKeys = {
  all: (boardId) => ['sections', boardId],
};

export function useSections(boardId) {
  return useQuery({
    queryKey: sectionKeys.all(boardId),
    queryFn: () => listSections(boardId),
    enabled: !!boardId,
  });
}

export function useCreateSection(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => createSection(boardId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sectionKeys.all(boardId) });
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) });
    },
  });
}

export function useUpdateSection(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sectionId, updates }) => updateSection(boardId, sectionId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sectionKeys.all(boardId) });
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) });
    },
  });
}

export function useDeleteSection(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sectionId) => deleteSection(boardId, sectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sectionKeys.all(boardId) });
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) });
    },
  });
}
