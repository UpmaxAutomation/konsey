import { useMemo, useCallback } from 'react';
import { addEdge } from '@xyflow/react';
import { createEdge as apiCreateEdge, createEdgesBatch, deleteEdge, deleteCard, deleteSection } from '../../../api/boards.js';
import { edgeToFlow, normalizeHandle } from '../utils.js';

/**
 * Manages edge connections and deletion of selected nodes/edges.
 *
 * @param {string} boardId - The current board ID
 * @param {Array} nodes - Current ReactFlow nodes
 * @param {Array} edges - Current ReactFlow edges
 * @param {Function} setNodes - ReactFlow setNodes dispatcher
 * @param {Function} setEdges - ReactFlow setEdges dispatcher
 * @returns Edge action handlers and selection state
 */
export default function useEdgeActions(boardId, nodes, edges, setNodes, setEdges) {
  const selectedNodes = useMemo(() => nodes.filter((n) => n.selected), [nodes]);
  const selectedEdges = useMemo(() => edges.filter((e) => e.selected), [edges]);

  // Handle new edge connection (supports section-to-section, card-to-section, section-to-card)
  const handleConnect = useCallback(async (connection) => {
    try {
      const srcIsSection = connection.source.startsWith('section-');
      const tgtIsSection = connection.target.startsWith('section-');

      if (srcIsSection || tgtIsSection) {
        // Resolve child card IDs for sections
        const srcCardIds = srcIsSection
          ? nodes.filter((n) => n.parentId === connection.source).map((n) => n.id)
          : [connection.source];
        const tgtCardIds = tgtIsSection
          ? nodes.filter((n) => n.parentId === connection.target).map((n) => n.id)
          : [connection.target];

        // Build cross-product of edges, skip self-connections
        const edgePairs = [];
        for (const src of srcCardIds) {
          for (const tgt of tgtCardIds) {
            if (src !== tgt) {
              edgePairs.push({
                from_card_id: src,
                to_card_id: tgt,
                edge_type: 'related',
              });
            }
          }
        }

        if (edgePairs.length === 0) return;

        const result = await createEdgesBatch(boardId, edgePairs);
        const flowEdges = (result.edges || []).map(edgeToFlow);
        setEdges((eds) => {
          let updated = eds;
          for (const fe of flowEdges) {
            updated = addEdge(fe, updated);
          }
          return updated;
        });
      } else {
        // Normal card-to-card connection
        const srcHandle = normalizeHandle(connection.sourceHandle);
        const tgtHandle = normalizeHandle(connection.targetHandle);
        const edge = await apiCreateEdge(boardId, {
          from_card_id: connection.source,
          to_card_id: connection.target,
          edge_type: 'related',
          source_handle: srcHandle,
          target_handle: tgtHandle,
        });
        const flowEdge = edgeToFlow(edge);
        setEdges((eds) => addEdge(flowEdge, eds));
      }
    } catch (err) {
      console.error('Failed to create edge:', err);
    }
  }, [boardId, nodes, setEdges]);

  // Delete selected nodes/edges
  const handleDeleteSelected = useCallback(async () => {
    for (const edge of selectedEdges) {
      try { await deleteEdge(boardId, edge.id); } catch (err) { console.error('Failed to delete edge:', err); }
    }
    setEdges((eds) => eds.filter((e) => !e.selected));

    const deletedIds = new Set();
    const sectionNodeIds = new Set();
    for (const node of selectedNodes) {
      try {
        if (node.type === 'sectionNode') {
          const sectionId = node.id.replace('section-', '');
          sectionNodeIds.add(node.id);
          // Backend delete converts child positions to absolute
          await deleteSection(boardId, sectionId);
        } else {
          await deleteCard(boardId, node.id);
        }
        deletedIds.add(node.id);
      } catch (err) { console.error('Failed to delete node:', err); }
    }
    setNodes((nds) => {
      // For section deletions, convert child card positions to absolute
      const updated = nds.map((n) => {
        if (n.parentId && sectionNodeIds.has(n.parentId) && !deletedIds.has(n.id)) {
          const sectionNode = nds.find((s) => s.id === n.parentId);
          const { parentId, extent, ...rest } = n;
          if (sectionNode) {
            const headerOffset = 36;
            return {
              ...rest,
              position: {
                x: n.position.x + sectionNode.position.x,
                y: n.position.y + sectionNode.position.y + headerOffset,
              },
            };
          }
          return rest;
        }
        return n;
      });
      return updated.filter((n) => !deletedIds.has(n.id));
    });
    setEdges((eds) => eds.filter((e) => !deletedIds.has(e.source) && !deletedIds.has(e.target)));
  }, [boardId, selectedNodes, selectedEdges, setNodes, setEdges]);

  return {
    handleConnect,
    handleDeleteSelected,
    selectedNodes,
    selectedEdges,
  };
}
