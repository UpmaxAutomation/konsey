import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listBoardTemplates,
  getBoardTemplate,
  saveBoardAsTemplate,
  applyBoardTemplate,
  deleteBoardTemplate,
  rateTemplate,
  getTemplateRatings,
  getMarketplace,
} from '../boardTemplates';

export function useBoardTemplates(filters = {}) {
  return useQuery({
    queryKey: ['boardTemplates', filters],
    queryFn: () => listBoardTemplates(filters),
    staleTime: 30_000,
  });
}

export function useBoardTemplate(templateId) {
  return useQuery({
    queryKey: ['boardTemplate', templateId],
    queryFn: () => getBoardTemplate(templateId),
    enabled: !!templateId,
  });
}

export function useMarketplace(filters = {}) {
  return useQuery({
    queryKey: ['marketplace', filters],
    queryFn: () => getMarketplace(filters),
    staleTime: 60_000,
  });
}

export function useTemplateRatings(type, templateId) {
  return useQuery({
    queryKey: ['templateRatings', type, templateId],
    queryFn: () => getTemplateRatings(type, templateId),
    enabled: !!type && !!templateId,
  });
}

export function useSaveBoardAsTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => saveBoardAsTemplate(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['boardTemplates'] });
      qc.invalidateQueries({ queryKey: ['marketplace'] });
    },
  });
}

export function useApplyBoardTemplate() {
  return useMutation({
    mutationFn: ({ templateId, boardId }) => applyBoardTemplate(templateId, boardId),
  });
}

export function useDeleteBoardTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => deleteBoardTemplate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['boardTemplates'] });
      qc.invalidateQueries({ queryKey: ['marketplace'] });
    },
  });
}

export function useRateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ type, id, rating, review }) => rateTemplate(type, id, rating, review),
    onSuccess: (_, { type, id }) => {
      qc.invalidateQueries({ queryKey: ['templateRatings', type, id] });
      qc.invalidateQueries({ queryKey: ['marketplace'] });
      qc.invalidateQueries({ queryKey: ['boardTemplates'] });
    },
  });
}
