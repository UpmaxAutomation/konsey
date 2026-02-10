import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listUserTemplates,
  createFlowTemplate,
  updateFlowTemplate,
  deleteFlowTemplate,
  createWorkflowFromUserTemplate,
  listWorkflowRuns,
} from '../flowTemplates.js';

export function useUserTemplates(projectId = null) {
  return useQuery({
    queryKey: ['flow-templates', projectId],
    queryFn: () => listUserTemplates(projectId),
  });
}

export function useCreateFlowTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createFlowTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['flow-templates'] });
    },
  });
}

export function useUpdateFlowTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }) => updateFlowTemplate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['flow-templates'] });
    },
  });
}

export function useDeleteFlowTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteFlowTemplate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['flow-templates'] });
    },
  });
}

export function useCreateFromUserTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ boardId, templateId }) => createWorkflowFromUserTemplate(boardId, templateId),
    onSuccess: (_, { boardId }) => {
      queryClient.invalidateQueries({ queryKey: ['workflows', boardId] });
    },
  });
}

export function useWorkflowRuns(boardId, workflowId) {
  return useQuery({
    queryKey: ['workflow-runs', boardId, workflowId],
    queryFn: () => listWorkflowRuns(boardId, workflowId),
    enabled: !!boardId && !!workflowId,
  });
}
