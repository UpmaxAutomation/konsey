import { useCallback, useEffect, useRef } from 'react';
import { batchUpdateCardPositions, updateBoardViewport } from '../../../api/boards.js';

/**
 * Manages debounced position saving on node drag and viewport save on pan/zoom.
 * Flushes pending saves on unmount and before browser unload to prevent data loss.
 *
 * @param {string} boardId - The current board ID
 * @param {Function} onNodesChange - ReactFlow's raw onNodesChange handler
 * @returns Wrapped node change handler and viewport move-end handler
 */
export default function useDebouncedPositions(boardId, onNodesChange) {
  const viewportSaveTimer = useRef(null);
  const positionSaveTimer = useRef(null);
  const pendingPositions = useRef({});
  const pendingViewport = useRef(null);
  const boardIdRef = useRef(boardId);
  const savingRef = useRef(false);
  boardIdRef.current = boardId;

  // Flush any pending position saves immediately
  const flushPositions = useCallback(() => {
    clearTimeout(positionSaveTimer.current);
    const positions = Object.values(pendingPositions.current);
    pendingPositions.current = {};
    if (positions.length > 0 && !savingRef.current) {
      savingRef.current = true;
      batchUpdateCardPositions(boardIdRef.current, positions)
        .catch(() => { /* silent — backend may be unavailable */ })
        .finally(() => { savingRef.current = false; });
    }
  }, []);

  // Flush any pending viewport save immediately
  const flushViewport = useCallback(() => {
    clearTimeout(viewportSaveTimer.current);
    const vp = pendingViewport.current;
    pendingViewport.current = null;
    if (vp) {
      updateBoardViewport(boardIdRef.current, vp).catch(() => {});
    }
  }, []);

  // Flush all pending saves
  const flushAll = useCallback(() => {
    flushPositions();
    flushViewport();
  }, [flushPositions, flushViewport]);

  // Flush on unmount (navigating away from board) and before browser close/refresh
  useEffect(() => {
    const handleBeforeUnload = () => flushAll();
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      flushAll();
    };
  }, [flushAll]);

  // Debounced position save on node drag
  const handleNodesChange = useCallback((changes) => {
    onNodesChange(changes);

    for (const change of changes) {
      if (change.type === 'position' && change.position && !change.dragging) {
        pendingPositions.current[change.id] = {
          card_id: change.id,
          x: change.position.x,
          y: change.position.y,
        };
      }
    }

    if (Object.keys(pendingPositions.current).length > 0) {
      clearTimeout(positionSaveTimer.current);
      positionSaveTimer.current = setTimeout(() => {
        const positions = Object.values(pendingPositions.current);
        pendingPositions.current = {};
        if (positions.length > 0 && !savingRef.current) {
          savingRef.current = true;
          batchUpdateCardPositions(boardId, positions)
            .catch(() => { /* silent */ })
            .finally(() => { savingRef.current = false; });
        }
      }, 500);
    }
  }, [boardId, onNodesChange]);

  // Save viewport on pan/zoom (debounced)
  const handleMoveEnd = useCallback((_event, viewport) => {
    const vp = { x: viewport.x, y: viewport.y, zoom: viewport.zoom };
    pendingViewport.current = vp;
    clearTimeout(viewportSaveTimer.current);
    viewportSaveTimer.current = setTimeout(() => {
      pendingViewport.current = null;
      updateBoardViewport(boardId, vp).catch(() => {});
    }, 800);
  }, [boardId]);

  return { handleNodesChange, handleMoveEnd };
}
