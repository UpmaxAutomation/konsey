import { useState, useEffect, useCallback } from 'react';
import { getBoard, updateBoard, boardMemoryAction, deleteBoardFact } from '../../../api/boards.js';
import { cardToNode, edgeToFlow, sectionToNode } from '../utils.js';

/**
 * Manages board loading, saving, rename, and board memory.
 *
 * @param {string} boardId - The current board ID
 * @param {Function} setNodes - ReactFlow setNodes dispatcher
 * @param {Function} setEdges - ReactFlow setEdges dispatcher
 * @returns Board state, loading flag, memory state, and action handlers
 */
export default function useBoardState(boardId, setNodes, setEdges) {
  const [board, setBoard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [boardMemory, setBoardMemory] = useState({ facts: [], decisions: [], preferences: {} });

  // Load board data + memory
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const data = await getBoard(boardId);
        if (cancelled) return;
        setBoard(data);
        const cardNodes = (data.cards || []).map(cardToNode);
        const sectionNodes = (data.sections || []).map(sectionToNode);
        setNodes([...sectionNodes, ...cardNodes]);
        const flowEdges = (data.edges || []).map(edgeToFlow);
        setEdges(flowEdges);
        if (data.memory) {
          setBoardMemory(data.memory);
        }
      } catch (err) {
        console.error('Failed to load board:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [boardId]);

  // Rename board
  const handleRenameBoard = useCallback(async (newName) => {
    try {
      const updated = await updateBoard(boardId, { name: newName });
      setBoard((prev) => ({ ...prev, name: updated.name }));
    } catch (err) {
      console.error('Failed to rename board:', err);
    }
  }, [boardId]);

  // Board memory handlers
  const handleAddFact = useCallback(async (content) => {
    try {
      const res = await boardMemoryAction(boardId, { action: 'add_fact', content });
      setBoardMemory(res.memory);
    } catch (err) {
      console.error('Failed to add fact:', err);
    }
  }, [boardId]);

  const handleDeleteFact = useCallback(async (factIndex) => {
    try {
      const res = await deleteBoardFact(boardId, factIndex);
      setBoardMemory(res.memory);
    } catch (err) {
      console.error('Failed to delete fact:', err);
    }
  }, [boardId]);

  const handleClearMemory = useCallback(async () => {
    try {
      const res = await boardMemoryAction(boardId, { action: 'clear' });
      setBoardMemory(res.memory);
    } catch (err) {
      console.error('Failed to clear memory:', err);
    }
  }, [boardId]);

  const memoryCount = (boardMemory.facts?.length || 0) + (boardMemory.decisions?.length || 0);

  return {
    board,
    setBoard,
    loading,
    boardMemory,
    setBoardMemory,
    handleRenameBoard,
    handleAddFact,
    handleDeleteFact,
    handleClearMemory,
    memoryCount,
  };
}
