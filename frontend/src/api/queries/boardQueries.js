import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listBoards, getBoard, createBoard, updateBoard, deleteBoard,
  listBoardChildren, getBoardBreadcrumbs, createChildBoard, moveBoard,
} from '../boards.js';

export const boardKeys = {
  all: ['boards'],
  detail: (id) => ['boards', id],
  children: (id) => ['boards', id, 'children'],
  breadcrumbs: (id) => ['boards', id, 'breadcrumbs'],
};

export function useBoards(projectId) {
  return useQuery({
    queryKey: [...boardKeys.all, { projectId }],
    queryFn: () => listBoards(projectId),
  });
}

export function useBoard(boardId) {
  return useQuery({
    queryKey: boardKeys.detail(boardId),
    queryFn: () => getBoard(boardId),
    enabled: !!boardId,
  });
}

export function useBoardChildren(boardId) {
  return useQuery({
    queryKey: boardKeys.children(boardId),
    queryFn: () => listBoardChildren(boardId),
    enabled: !!boardId,
  });
}

export function useBoardBreadcrumbs(boardId) {
  return useQuery({
    queryKey: boardKeys.breadcrumbs(boardId),
    queryFn: () => getBoardBreadcrumbs(boardId),
    enabled: !!boardId,
  });
}

export function useCreateBoard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createBoard,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardKeys.all }),
  });
}

export function useUpdateBoard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ boardId, updates }) => updateBoard(boardId, updates),
    onSuccess: (_, { boardId }) => {
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) });
      queryClient.invalidateQueries({ queryKey: boardKeys.all });
    },
  });
}

export function useDeleteBoard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteBoard,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardKeys.all }),
  });
}

export function useCreateChildBoard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ parentBoardId, data }) => createChildBoard(parentBoardId, data),
    onSuccess: (_, { parentBoardId }) => {
      queryClient.invalidateQueries({ queryKey: boardKeys.all });
      queryClient.invalidateQueries({ queryKey: boardKeys.children(parentBoardId) });
    },
  });
}

export function useMoveBoard() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ boardId, newParentId }) => moveBoard(boardId, newParentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: boardKeys.all }),
  });
}
