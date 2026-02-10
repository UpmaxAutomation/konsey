import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listAssets, getAsset, updateAsset, deleteAsset, createCardFromImage } from '../assets';

export function useProjectAssets(projectId, filters = {}) {
  return useQuery({
    queryKey: ['assets', projectId, filters],
    queryFn: () => listAssets(projectId, filters),
    enabled: !!projectId,
    staleTime: 30_000,
  });
}

export function useAsset(assetId) {
  return useQuery({
    queryKey: ['asset', assetId],
    queryFn: () => getAsset(assetId),
    enabled: !!assetId,
  });
}

export function useUpdateAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }) => updateAsset(id, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['asset', id] });
      qc.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

export function useDeleteAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => deleteAsset(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

export function useCreateCardFromImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, imageId }) => createCardFromImage(projectId, imageId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}
