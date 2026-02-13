import { useMemo, useCallback } from 'react';
import { addEdge } from '@xyflow/react';
import { createEdge as apiCreateEdge, createEdgesBatch, deleteEdge, updateEdge as apiUpdateEdge, deleteCard, createCard, createSection, deleteSection } from '../../../api/boards.js';
import { edgeToFlow, normalizeHandle } from '../utils.js';
import { useHistoryStore } from '../../../stores/historyStore';

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
  const pushEntry = useHistoryStore((s) => s.pushEntry);
  const isUndoing = useHistoryStore((s) => s.isUndoing);
  const isRedoing = useHistoryStore((s) => s.isRedoing);

  // Handle new edge connection (supports section-to-section, card-to-section, section-to-card)
  const handleConnect = useCallback(async (connection) => {
    try {
      // Connection validation: prevent self-referential edges
      if (connection.source === connection.target) {
        console.warn('Cannot connect a node to itself.');
        return;
      }

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
        const batchEdgeIds = flowEdges.map((e) => e.id);
        setEdges((eds) => {
          let updated = eds;
          for (const fe of flowEdges) {
            updated = addEdge(fe, updated);
          }
          return updated;
        });

        if (!isUndoing && !isRedoing && flowEdges.length > 0) {
          pushEntry({
            type: 'connect_batch',
            description: `Connect ${flowEdges.length} edges`,
            undo: () => setEdges((eds) => eds.filter((e) => !batchEdgeIds.includes(e.id))),
            redo: () => setEdges((eds) => {
              let updated = eds;
              for (const fe of flowEdges) { updated = addEdge(fe, updated); }
              return updated;
            }),
            apiUndo: async () => {
              for (const eid of batchEdgeIds) { try { await deleteEdge(boardId, eid); } catch {} }
            },
            apiRedo: () => createEdgesBatch(boardId, edgePairs),
          });
        }
      } else {
        // Connection validation: prevent duplicate edges
        const existingEdge = edges.find(
          (e) => e.source === connection.source && e.target === connection.target
        );
        if (existingEdge) {
          console.warn('An edge already exists between these nodes.');
          return;
        }

        // Normal card-to-card connection
        const srcHandle = normalizeHandle(connection.sourceHandle);
        const tgtHandle = normalizeHandle(connection.targetHandle);
        // Auto-detect pipeline edge type
        const srcNode = nodes.find(n => n.id === connection.source);
        const tgtNode = nodes.find(n => n.id === connection.target);
        const isPipeline = srcNode?.data?.card_type?.startsWith('pl_') || tgtNode?.data?.card_type?.startsWith('pl_');
        const edgeData = {
          from_card_id: connection.source,
          to_card_id: connection.target,
          edge_type: isPipeline ? 'pipeline' : 'related',
          source_handle: srcHandle,
          target_handle: tgtHandle,
        };
        const edge = await apiCreateEdge(boardId, edgeData);
        const flowEdge = edgeToFlow(edge);
        setEdges((eds) => addEdge(flowEdge, eds));

        if (!isUndoing && !isRedoing) {
          pushEntry({
            type: 'connect',
            description: `Connect ${connection.source} to ${connection.target}`,
            undo: () => setEdges((eds) => eds.filter((e) => e.id !== edge.id)),
            redo: () => setEdges((eds) => addEdge(flowEdge, eds)),
            apiUndo: () => deleteEdge(boardId, edge.id),
            apiRedo: () => apiCreateEdge(boardId, edgeData),
          });
        }
      }
    } catch (err) {
      console.error('Failed to create edge:', err);
    }
  }, [boardId, nodes, edges, setEdges, pushEntry, isUndoing, isRedoing]);

  // Update an edge via API and refresh local state
  const handleUpdateEdge = useCallback(async (edgeId, updates) => {
    try {
      const updatedEdge = await apiUpdateEdge(boardId, edgeId, updates);
      const flowEdge = edgeToFlow(updatedEdge);
      setEdges((eds) => eds.map((e) => e.id === edgeId ? { ...flowEdge, selected: e.selected } : e));
    } catch (err) {
      console.error('Failed to update edge:', err);
    }
  }, [boardId, setEdges]);

  // Reverse edge direction: swap source/target via API
  const handleReverseEdge = useCallback(async (edgeId) => {
    try {
      const edge = edges.find((e) => e.id === edgeId);
      if (!edge) return;
      // Delete old edge and create a new one with swapped source/target
      await deleteEdge(boardId, edgeId);
      const newEdge = await apiCreateEdge(boardId, {
        from_card_id: edge.target,
        to_card_id: edge.source,
        edge_type: edge.data?.edge_type || 'related',
        source_handle: edge.targetHandle,
        target_handle: edge.sourceHandle,
      });
      const flowEdge = edgeToFlow(newEdge);
      setEdges((eds) => eds.filter((e) => e.id !== edgeId).concat(flowEdge));
    } catch (err) {
      console.error('Failed to reverse edge:', err);
    }
  }, [boardId, edges, setEdges]);

  // Delete selected nodes/edges
  const handleDeleteSelected = useCallback(async () => {
    // Capture state before deletion for undo
    const deletedEdgeSnapshots = selectedEdges.map((e) => ({ ...e }));
    const deletedNodeSnapshots = selectedNodes.map((n) => ({ ...n, data: { ...n.data }, position: { ...n.position } }));
    // Also capture orphaned edges (edges connected to nodes being deleted)
    const deletedNodeIds = new Set(selectedNodes.map((n) => n.id));
    const orphanedEdges = edges.filter(
      (e) => !e.selected && (deletedNodeIds.has(e.source) || deletedNodeIds.has(e.target))
    ).map((e) => ({ ...e }));

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
          await deleteSection(boardId, sectionId);
        } else {
          await deleteCard(boardId, node.id);
        }
        deletedIds.add(node.id);
      } catch (err) { console.error('Failed to delete node:', err); }
    }
    setNodes((nds) => {
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

    if (!isUndoing && !isRedoing && (deletedNodeSnapshots.length > 0 || deletedEdgeSnapshots.length > 0)) {
      const allDeletedEdges = [...deletedEdgeSnapshots, ...orphanedEdges];
      pushEntry({
        type: 'delete_selected',
        description: `Delete ${deletedNodeSnapshots.length} nodes, ${allDeletedEdges.length} edges`,
        undo: () => {
          setNodes((nds) => [...nds, ...deletedNodeSnapshots]);
          setEdges((eds) => [...eds, ...allDeletedEdges]);
        },
        redo: () => {
          const nodeIds = new Set(deletedNodeSnapshots.map((n) => n.id));
          const edgeIds = new Set(allDeletedEdges.map((e) => e.id));
          setNodes((nds) => nds.filter((n) => !nodeIds.has(n.id)));
          setEdges((eds) => eds.filter((e) => !edgeIds.has(e.id)));
        },
        apiUndo: async () => {
          for (const node of deletedNodeSnapshots) {
            try {
              if (node.type === 'sectionNode') {
                await createSection(boardId, {
                  title: node.data.title,
                  color: node.data.color,
                  x: node.position.x,
                  y: node.position.y,
                  ...node.style,
                });
              } else {
                await createCard(boardId, {
                  card_type: node.data.card_type,
                  title: node.data.title,
                  content: node.data.content,
                  color: node.data.color,
                  position_x: node.position.x,
                  position_y: node.position.y,
                  extra: node.data.extra,
                });
              }
            } catch {}
          }
          for (const edge of allDeletedEdges) {
            try {
              await apiCreateEdge(boardId, {
                from_card_id: edge.source,
                to_card_id: edge.target,
                edge_type: edge.data?.edge_type || 'related',
              });
            } catch {}
          }
        },
        apiRedo: async () => {
          for (const edge of allDeletedEdges) {
            try { await deleteEdge(boardId, edge.id); } catch {}
          }
          for (const node of deletedNodeSnapshots) {
            try {
              if (node.type === 'sectionNode') {
                await deleteSection(boardId, node.id.replace('section-', ''));
              } else {
                await deleteCard(boardId, node.id);
              }
            } catch {}
          }
        },
      });
    }
  }, [boardId, selectedNodes, selectedEdges, edges, setNodes, setEdges, pushEntry, isUndoing, isRedoing]);

  // Delete a single edge by ID (for context menu)
  const handleDeleteEdge = useCallback(async (edgeId) => {
    try {
      await deleteEdge(boardId, edgeId);
      setEdges((eds) => eds.filter((e) => e.id !== edgeId));
    } catch (err) {
      console.error('Failed to delete edge:', err);
    }
  }, [boardId, setEdges]);

  return {
    handleConnect,
    handleDeleteSelected,
    handleUpdateEdge,
    handleReverseEdge,
    handleDeleteEdge,
    selectedNodes,
    selectedEdges,
  };
}
