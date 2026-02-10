import { useState, useCallback, useRef } from 'react';
import { createCard, updateCard, deleteCard, deleteEdge, runCardAIAction } from '../../../api/boards.js';
import { cardToNode, edgeToFlow } from '../utils.js';
import { useHistoryStore } from '../../../stores/historyStore';

/**
 * Manages card CRUD operations and AI actions.
 *
 * @param {string} boardId - The current board ID
 * @param {Array} nodes - Current ReactFlow nodes
 * @param {Function} setNodes - ReactFlow setNodes dispatcher
 * @param {Function} setEdges - ReactFlow setEdges dispatcher
 * @returns Card action handlers and processing state
 */
export default function useCardActions(boardId, nodes, setNodes, setEdges) {
  const [processingCards, setProcessingCards] = useState(new Set());
  const [actionError, setActionError] = useState(null);
  const pushEntry = useHistoryStore((s) => s.pushEntry);
  const isUndoing = useHistoryStore((s) => s.isUndoing);
  const isRedoing = useHistoryStore((s) => s.isRedoing);

  const handleUpdateCardRef = useRef(null);

  // Update card (inline editing)
  handleUpdateCardRef.current = useCallback(async (cardId, updates) => {
    try {
      // Capture old data before mutation for undo
      const oldNode = nodes.find((n) => n.id === cardId);
      const oldData = oldNode ? { ...oldNode.data } : null;

      const updated = await updateCard(boardId, cardId, updates);
      setNodes((nds) => nds.map((n) =>
        n.id === cardId
          ? { ...n, data: { ...n.data, ...updated } }
          : n
      ));

      if (!isUndoing && !isRedoing && oldData) {
        const newData = { ...updated };
        pushEntry({
          type: 'update_card',
          description: `Update card ${cardId}`,
          undo: () => setNodes((nds) => nds.map((n) =>
            n.id === cardId ? { ...n, data: { ...n.data, ...oldData } } : n
          )),
          redo: () => setNodes((nds) => nds.map((n) =>
            n.id === cardId ? { ...n, data: { ...n.data, ...newData } } : n
          )),
          apiUndo: () => updateCard(boardId, cardId, oldData),
          apiRedo: () => updateCard(boardId, cardId, newData),
        });
      }
    } catch (err) {
      console.error('Failed to update card:', err);
    }
  }, [boardId, nodes, setNodes, pushEntry, isUndoing, isRedoing]);

  // Stable wrapper that delegates to ref (identity never changes)
  const stableUpdateCard = useCallback((cardId, updates) => handleUpdateCardRef.current(cardId, updates), []);

  // Add card (with optional template for pre-filled content)
  const handleAddCard = useCallback(async (cardType, template) => {
    try {
      const isKnowledge = cardType === 'knowledge';
      const cardData = {
        card_type: isKnowledge ? 'note' : cardType,
        title: template?.title || (isKnowledge ? 'New Knowledge' : cardType === 'note' ? 'New Note' : cardType === 'link' ? 'New Link' : ''),
        content: template?.content || '',
        position_x: Math.random() * 400 + 100,
        position_y: Math.random() * 300 + 100,
        ...(isKnowledge ? { extra: { is_knowledge: true } } : {}),
      };
      const card = await createCard(boardId, cardData);
      const node = cardToNode(card);
      setNodes((nds) => [...nds, node]);

      if (!isUndoing && !isRedoing) {
        pushEntry({
          type: 'add_card',
          description: `Add ${cardType} card`,
          undo: () => setNodes((nds) => nds.filter((n) => n.id !== card.id)),
          redo: () => setNodes((nds) => [...nds, node]),
          apiUndo: () => deleteCard(boardId, card.id),
          apiRedo: () => createCard(boardId, cardData),
        });
      }
    } catch (err) {
      console.error('Failed to create card:', err);
    }
  }, [boardId, setNodes, pushEntry, isUndoing, isRedoing]);

  // Toggle knowledge flag on a card
  const handleToggleKnowledge = useCallback(async (cardId) => {
    const node = nodes.find((n) => n.id === cardId);
    if (!node) return;
    const isKnowledge = node.data?.extra?.is_knowledge;
    const newExtra = { ...(node.data?.extra || {}), is_knowledge: !isKnowledge };
    try {
      await updateCard(boardId, cardId, { extra: newExtra });
      setNodes((nds) => nds.map((n) =>
        n.id === cardId
          ? { ...n, data: { ...n.data, extra: newExtra } }
          : n
      ));
    } catch (err) {
      console.error('Failed to toggle knowledge flag:', err);
    }
  }, [boardId, nodes, setNodes]);

  // Card AI action from context menu
  const handleCardAIAction = useCallback(async (cardId, action, customPrompt) => {
    setActionError(null);
    setProcessingCards((prev) => new Set([...prev, cardId]));
    try {
      const result = await runCardAIAction(boardId, cardId, { action, customPrompt });
      const newNodes = (result.cards || []).map(cardToNode);
      const newEdges = (result.edges || []).map(edgeToFlow);
      const newCardIds = newNodes.map((n) => n.id);
      const newEdgeIds = newEdges.map((e) => e.id);
      setNodes((nds) => [...nds, ...newNodes]);
      setEdges((eds) => [...eds, ...newEdges]);

      if (!isUndoing && !isRedoing && (newCardIds.length > 0 || newEdgeIds.length > 0)) {
        pushEntry({
          type: 'ai_action',
          description: `AI ${action} on card ${cardId}`,
          undo: () => {
            setNodes((nds) => nds.filter((n) => !newCardIds.includes(n.id)));
            setEdges((eds) => eds.filter((e) => !newEdgeIds.includes(e.id)));
          },
          redo: () => {
            setNodes((nds) => [...nds, ...newNodes]);
            setEdges((eds) => [...eds, ...newEdges]);
          },
          apiUndo: async () => {
            for (const eid of newEdgeIds) { try { await deleteEdge(boardId, eid); } catch {} }
            for (const cid of newCardIds) { try { await deleteCard(boardId, cid); } catch {} }
          },
        });
      }
    } catch (err) {
      console.error('Card AI action failed:', err);
      const message = err?.response?.data?.detail || err?.message || 'AI action failed';
      setActionError({ action, cardId, message });
    } finally {
      setProcessingCards((prev) => { const next = new Set(prev); next.delete(cardId); return next; });
    }
  }, [boardId, setNodes, setEdges, pushEntry, isUndoing, isRedoing]);

  const clearActionError = useCallback(() => setActionError(null), []);

  return {
    handleAddCard,
    stableUpdateCard,
    handleToggleKnowledge,
    handleCardAIAction,
    processingCards,
    setProcessingCards,
    actionError,
    clearActionError,
  };
}
