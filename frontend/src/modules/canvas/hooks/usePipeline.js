import { useState, useCallback } from 'react';
import { runPipeline } from '../../../api/pipeline.js';

export default function usePipeline(boardId) {
  const [running, setRunning] = useState(false);
  const [nodeStatuses, setNodeStatuses] = useState({});
  const [nodeOutputs, setNodeOutputs] = useState({});
  const [error, setError] = useState(null);

  const run = useCallback(async () => {
    if (!boardId || running) return;
    setRunning(true);
    setError(null);
    setNodeStatuses({});
    setNodeOutputs({});

    try {
      await runPipeline(boardId, (event) => {
        switch (event.type) {
          case 'node_start':
            setNodeStatuses(prev => ({ ...prev, [event.node_id]: 'running' }));
            break;
          case 'node_complete':
            setNodeStatuses(prev => ({ ...prev, [event.node_id]: 'done' }));
            setNodeOutputs(prev => ({ ...prev, [event.node_id]: event.output }));
            break;
          case 'node_error':
            setNodeStatuses(prev => ({ ...prev, [event.node_id]: 'error' }));
            setError(event.error);
            break;
          case 'pipeline_complete':
            setRunning(false);
            break;
          default:
            break;
        }
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  }, [boardId, running]);

  const clearError = useCallback(() => setError(null), []);

  return { running, nodeStatuses, nodeOutputs, error, clearError, run };
}
