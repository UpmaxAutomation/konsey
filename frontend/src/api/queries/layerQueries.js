import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createLayer,
  listLayers,
  getLayer,
  updateLayer,
  deleteLayer,
  assignDocuments,
  reorderLayers,
} from '../layers.js';
import { ragKeys } from './ragQueries.js';

export const layerKeys = {
  all: ['layers'],
  project: (projectId) => ['layers', 'project', projectId],
  detail: (layerId) => ['layers', layerId],
};

export function useProjectLayers(projectId) {
  return useQuery({
    queryKey: layerKeys.project(projectId),
    queryFn: () => listLayers(projectId),
    select: (data) => data?.layers ?? [],
    enabled: !!projectId,
  });
}

export function useLayer(layerId) {
  return useQuery({
    queryKey: layerKeys.detail(layerId),
    queryFn: () => getLayer(layerId),
    enabled: !!layerId,
  });
}

export function useCreateLayer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createLayer,
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: layerKeys.all });
    },
  });
}

export function useUpdateLayer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ layerId, updates }) => updateLayer(layerId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: layerKeys.all });
    },
  });
}

export function useDeleteLayer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteLayer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: layerKeys.all });
    },
  });
}

export function useAssignDocuments() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ layerId, documentIds }) => assignDocuments(layerId, documentIds),
    onSuccess: (_, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: layerKeys.all });
      if (projectId) {
        queryClient.invalidateQueries({ queryKey: ragKeys.status(projectId) });
      }
    },
  });
}

export function useReorderLayers() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, layerIds }) => reorderLayers(projectId, layerIds),
    onMutate: async ({ projectId, layerIds }) => {
      await queryClient.cancelQueries({ queryKey: layerKeys.project(projectId) });
      const previousData = queryClient.getQueryData(layerKeys.project(projectId));
      if (previousData?.layers) {
        const reordered = layerIds
          .map((id) => previousData.layers.find((l) => l.id === id))
          .filter(Boolean)
          .map((layer, idx) => ({ ...layer, sort_order: idx }));
        queryClient.setQueryData(layerKeys.project(projectId), { layers: reordered });
      }
      return { previousData };
    },
    onError: (err, { projectId }, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(layerKeys.project(projectId), context.previousData);
      }
    },
    onSettled: (_, __, { projectId }) => {
      queryClient.invalidateQueries({ queryKey: layerKeys.project(projectId) });
    },
  });
}
