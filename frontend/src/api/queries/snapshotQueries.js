import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listSnapshots, createSnapshot, restoreSnapshot, deleteSnapshot } from '../snapshots.js';
import { boardKeys } from './boardQueries.js';

export const snapshotKeys = {
  all: (boardId) => ['snapshots', boardId],
};

export function useSnapshots(boardId) {
  return useQuery({
    queryKey: snapshotKeys.all(boardId),
    queryFn: () => listSnapshots(boardId),
    enabled: !!boardId,
  });
}

export function useCreateSnapshot(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => createSnapshot(boardId, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: snapshotKeys.all(boardId) }),
  });
}

export function useRestoreSnapshot(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (snapshotId) => restoreSnapshot(boardId, snapshotId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(boardId) });
      queryClient.invalidateQueries({ queryKey: snapshotKeys.all(boardId) });
    },
  });
}

export function useDeleteSnapshot(boardId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (snapshotId) => deleteSnapshot(boardId, snapshotId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: snapshotKeys.all(boardId) }),
  });
}
