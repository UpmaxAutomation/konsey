import { useState, useCallback, useRef } from 'react';
import {
  listWorkflows,
  createWorkflow,
  deleteWorkflow,
  runWorkflow,
  approveWorkflowStep,
  cancelWorkflow,
} from '../../../api/workflows.js';

export default function useWorkflows(boardId) {
  const [workflows, setWorkflows] = useState([]);
  const [activeWorkflow, setActiveWorkflow] = useState(null);
  const [running, setRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(null);
  const [waitingReview, setWaitingReview] = useState(false);
  const [error, setError] = useState(null);
  const createdCardsRef = useRef([]);
  const createdEdgesRef = useRef([]);

  const fetchWorkflows = useCallback(async () => {
    if (!boardId) return;
    try {
      const data = await listWorkflows(boardId);
      setWorkflows(data);
    } catch (err) {
      console.error('Failed to fetch workflows:', err);
    }
  }, [boardId]);

  const handleCreate = useCallback(async (data) => {
    if (!boardId) return null;
    try {
      const wf = await createWorkflow(boardId, data);
      setWorkflows((prev) => [wf, ...prev]);
      return wf;
    } catch (err) {
      setError(err.message);
      return null;
    }
  }, [boardId]);

  const handleDelete = useCallback(async (workflowId) => {
    if (!boardId) return;
    try {
      await deleteWorkflow(boardId, workflowId);
      setWorkflows((prev) => prev.filter((w) => w.id !== workflowId));
      if (activeWorkflow?.id === workflowId) setActiveWorkflow(null);
    } catch (err) {
      setError(err.message);
    }
  }, [boardId, activeWorkflow]);

  const handleRun = useCallback(async (workflowId, { initialInput = '', contextCardIds = [] } = {}, onCardCreated) => {
    if (!boardId || running) return;
    setRunning(true);
    setError(null);
    setWaitingReview(false);
    createdCardsRef.current = [];
    createdEdgesRef.current = [];

    try {
      await runWorkflow(boardId, workflowId, { initialInput, contextCardIds }, (event) => {
        switch (event.type) {
          case 'step_start':
            setCurrentStep({ index: event.step_index, name: event.step_name, type: event.step_type });
            break;
          case 'step_card_created':
            if (event.card) {
              createdCardsRef.current.push(event.card);
              onCardCreated?.(event.card, event.edge || null);
            }
            break;
          case 'step_complete':
            setCurrentStep((prev) => prev ? { ...prev, status: 'completed' } : null);
            break;
          case 'step_waiting_review':
            setWaitingReview(true);
            setCurrentStep({ index: event.step_index, name: event.step_name, status: 'waiting_review' });
            break;
          case 'workflow_complete':
            setRunning(false);
            setCurrentStep(null);
            break;
          case 'workflow_error':
            setRunning(false);
            setError(event.error || 'Workflow failed');
            break;
          default:
            break;
        }
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
      fetchWorkflows();
    }
  }, [boardId, running, fetchWorkflows]);

  const handleApprove = useCallback(async (workflowId) => {
    if (!boardId) return;
    try {
      const wf = await approveWorkflowStep(boardId, workflowId);
      setWaitingReview(false);
      setActiveWorkflow(wf);
    } catch (err) {
      setError(err.message);
    }
  }, [boardId]);

  const handleCancel = useCallback(async (workflowId) => {
    if (!boardId) return;
    try {
      await cancelWorkflow(boardId, workflowId);
      setRunning(false);
      setCurrentStep(null);
      setWaitingReview(false);
      fetchWorkflows();
    } catch (err) {
      setError(err.message);
    }
  }, [boardId, fetchWorkflows]);

  return {
    workflows,
    activeWorkflow,
    setActiveWorkflow,
    running,
    currentStep,
    waitingReview,
    error,
    clearError: () => setError(null),
    fetchWorkflows,
    createWorkflow: handleCreate,
    deleteWorkflow: handleDelete,
    runWorkflow: handleRun,
    approveStep: handleApprove,
    cancelWorkflow: handleCancel,
  };
}
