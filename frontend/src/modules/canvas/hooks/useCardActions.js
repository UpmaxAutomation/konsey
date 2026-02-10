import { useState, useCallback, useRef } from 'react';
import { createCard, updateCard, runCardAIAction } from '../../../api/boards.js';
import { cardToNode, edgeToFlow } from '../utils.js';

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

  const handleUpdateCardRef = useRef(null);

  // Update card (inline editing)
  handleUpdateCardRef.current = useCallback(async (cardId, updates) => {
    try {
      const updated = await updateCard(boardId, cardId, updates);
      setNodes((nds) => nds.map((n) =>
        n.id === cardId
          ? { ...n, data: { ...n.data, ...updated } }
          : n
      ));
    } catch (err) {
      console.error('Failed to update card:', err);
    }
  }, [boardId, setNodes]);

  // Stable wrapper that delegates to ref (identity never changes)
  const stableUpdateCard = useCallback((cardId, updates) => handleUpdateCardRef.current(cardId, updates), []);

  // Add card (with optional template for pre-filled content)
  const handleAddCard = useCallback(async (cardType, template) => {
    try {
      const isKnowledge = cardType === 'knowledge';
      const card = await createCard(boardId, {
        card_type: isKnowledge ? 'note' : cardType,
        title: template?.title || (isKnowledge ? 'New Knowledge' : cardType === 'note' ? 'New Note' : cardType === 'link' ? 'New Link' : ''),
        content: template?.content || '',
        position_x: Math.random() * 400 + 100,
        position_y: Math.random() * 300 + 100,
        ...(isKnowledge ? { extra: { is_knowledge: true } } : {}),
      });
      setNodes((nds) => [...nds, cardToNode(card)]);
    } catch (err) {
      console.error('Failed to create card:', err);
    }
  }, [boardId, setNodes]);

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
      setNodes((nds) => [...nds, ...newNodes]);
      setEdges((eds) => [...eds, ...newEdges]);
    } catch (err) {
      console.error('Card AI action failed:', err);
      const message = err?.response?.data?.detail || err?.message || 'AI action failed';
      setActionError({ action, cardId, message });
    } finally {
      setProcessingCards((prev) => { const next = new Set(prev); next.delete(cardId); return next; });
    }
  }, [boardId, setNodes, setEdges]);

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
