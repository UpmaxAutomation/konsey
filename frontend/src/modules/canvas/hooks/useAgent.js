import { useState, useCallback, useRef } from 'react';
import {
  runCanvasAgent,
  pauseCanvasAgent,
  resumeCanvasAgent,
  cancelCanvasAgent,
  listCanvasAgentRuns,
} from '../../../api/agents.js';

export default function useAgent(boardId) {
  const [running, setRunning] = useState(false);
  const [paused, setPaused] = useState(false);
  const [runId, setRunId] = useState(null);
  const [thoughts, setThoughts] = useState([]);
  const [iteration, setIteration] = useState(0);
  const [error, setError] = useState(null);
  const [runs, setRuns] = useState([]);
  const createdCardsRef = useRef([]);

  const fetchRuns = useCallback(async () => {
    if (!boardId) return;
    try {
      const data = await listCanvasAgentRuns(boardId);
      setRuns(data);
    } catch (err) {
      console.error('Failed to fetch agent runs:', err);
    }
  }, [boardId]);

  const handleEvent = useCallback((event, onCardCreated) => {
    switch (event.type) {
      case 'agent_start':
        setRunId(event.run_id);
        setIteration(0);
        setThoughts([]);
        break;
      case 'agent_iteration':
        setIteration(event.iteration);
        setThoughts((prev) => [...prev, {
          iteration: event.iteration,
          thought: event.thought,
          tool: event.tool,
          tool_params: event.tool_params,
        }]);
        break;
      case 'agent_tool_result':
        setThoughts((prev) => {
          const updated = [...prev];
          if (updated.length > 0) {
            updated[updated.length - 1] = {
              ...updated[updated.length - 1],
              result: event.result,
            };
          }
          return updated;
        });
        break;
      case 'agent_card_created':
        if (event.card) {
          createdCardsRef.current.push(event.card);
          onCardCreated?.(event.card, event.edge || null);
        }
        break;
      case 'agent_complete':
        setRunning(false);
        setPaused(false);
        break;
      case 'agent_error':
        setRunning(false);
        setPaused(false);
        setError(event.error || 'Agent failed');
        break;
      case 'agent_paused':
        setPaused(true);
        break;
      default:
        break;
    }
  }, []);

  const startAgent = useCallback(async ({ goal, model, maxIterations } = {}, onCardCreated) => {
    if (!boardId || running) return;
    setRunning(true);
    setPaused(false);
    setError(null);
    setThoughts([]);
    setIteration(0);
    createdCardsRef.current = [];

    try {
      await runCanvasAgent(boardId, { goal, model, maxIterations }, (event) => {
        handleEvent(event, onCardCreated);
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
      fetchRuns();
    }
  }, [boardId, running, handleEvent, fetchRuns]);

  const pause = useCallback(async () => {
    if (!boardId || !runId) return;
    try {
      await pauseCanvasAgent(boardId, runId);
      setPaused(true);
    } catch (err) {
      setError(err.message);
    }
  }, [boardId, runId]);

  const resume = useCallback(async (onCardCreated) => {
    if (!boardId || !runId) return;
    try {
      setPaused(false);
      setRunning(true);
      await resumeCanvasAgent(boardId, runId, (event) => {
        handleEvent(event, onCardCreated);
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
      fetchRuns();
    }
  }, [boardId, runId, handleEvent, fetchRuns]);

  const cancel = useCallback(async () => {
    if (!boardId || !runId) return;
    try {
      await cancelCanvasAgent(boardId, runId);
      setRunning(false);
      setPaused(false);
    } catch (err) {
      setError(err.message);
    }
  }, [boardId, runId]);

  return {
    running,
    paused,
    runId,
    thoughts,
    iteration,
    error,
    runs,
    clearError: () => setError(null),
    startAgent,
    pause,
    resume,
    cancel,
    fetchRuns,
  };
}
