import { useCallback } from 'react';
import dagre from 'dagre';
import { batchUpdateCardPositions } from '../../../api/boards.js';

/**
 * Computes a hierarchical auto-layout for board nodes using the dagre library.
 * Filters out section nodes and pipeline nodes, then arranges remaining cards
 * based on their edge connections in the specified direction.
 *
 * @param {Object} params
 * @param {Array} params.nodes - Current ReactFlow nodes
 * @param {Array} params.edges - Current ReactFlow edges
 * @param {Function} params.setNodes - ReactFlow setNodes updater
 * @param {string} params.boardId - Current board ID for persisting positions
 * @returns {{ applyAutoLayout: (direction?: string) => Object }} Auto-layout callback
 */
export function useAutoLayout({ nodes, edges, setNodes, boardId }) {
  const applyAutoLayout = useCallback((direction = 'TB') => {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({
      rankdir: direction,
      nodesep: 60,
      ranksep: 80,
      marginx: 40,
      marginy: 40,
    });

    // Only include non-section, non-pipeline nodes in the layout
    const layoutNodes = nodes.filter(
      (n) => n.type !== 'sectionNode' && !n.data?.card_type?.startsWith('pl_')
    );

    if (layoutNodes.length === 0) {
      return {};
    }

    layoutNodes.forEach((node) => {
      const width = parseInt(node.style?.width, 10) || 280;
      const height = node.measured?.height || parseInt(node.data?.extra?.height, 10) || 200;
      g.setNode(node.id, { width, height });
    });

    edges.forEach((edge) => {
      if (g.hasNode(edge.source) && g.hasNode(edge.target)) {
        g.setEdge(edge.source, edge.target);
      }
    });

    dagre.layout(g);

    // Capture old positions for undo support
    const oldPositions = {};
    layoutNodes.forEach((n) => {
      oldPositions[n.id] = { x: n.position.x, y: n.position.y };
    });

    // Build new positions from dagre output
    const newPositions = [];
    const positionMap = {};

    layoutNodes.forEach((node) => {
      if (!g.hasNode(node.id)) return;
      const dagreNode = g.node(node.id);
      const width = parseInt(node.style?.width, 10) || 280;
      const height = node.measured?.height || parseInt(node.data?.extra?.height, 10) || 200;
      // dagre returns center coords; convert to top-left for ReactFlow
      const newX = dagreNode.x - width / 2;
      const newY = dagreNode.y - height / 2;
      positionMap[node.id] = { x: newX, y: newY };
      newPositions.push({ card_id: node.id, x: newX, y: newY });
    });

    // Apply positions to the node state
    setNodes((prev) =>
      prev.map((node) => {
        const newPos = positionMap[node.id];
        if (!newPos) return node;
        return { ...node, position: { x: newPos.x, y: newPos.y } };
      })
    );

    // Persist new positions to the backend
    if (newPositions.length > 0) {
      batchUpdateCardPositions(boardId, newPositions).catch((err) => {
        console.error('Failed to save auto-layout positions:', err);
      });
    }

    return oldPositions;
  }, [nodes, edges, setNodes, boardId]);

  /**
   * Grid-pack isolated nodes (those with no edges) into a tidy arrangement.
   * Connected nodes are left in place; only orphans are repositioned.
   */
  const tidyUp = useCallback(() => {
    const layoutNodes = nodes.filter(
      (n) => n.type !== 'sectionNode' && !n.data?.card_type?.startsWith('pl_')
    );
    if (layoutNodes.length === 0) return;

    // Find which nodes have edges
    const connectedIds = new Set();
    edges.forEach((e) => {
      connectedIds.add(e.source);
      connectedIds.add(e.target);
    });

    const orphans = layoutNodes.filter((n) => !connectedIds.has(n.id));
    if (orphans.length === 0) return;

    // Find the bounding box of all nodes to place the grid below
    let maxBottom = 0;
    layoutNodes.forEach((n) => {
      const h = n.measured?.height || parseInt(n.data?.extra?.height, 10) || 200;
      const bottom = n.position.y + h;
      if (bottom > maxBottom) maxBottom = bottom;
    });

    // Grid settings
    const GAP = 30;
    const COLS = Math.max(1, Math.ceil(Math.sqrt(orphans.length)));
    const startY = maxBottom + 80;
    // Use the leftmost node position as the starting X
    const startX = Math.min(...layoutNodes.map((n) => n.position.x), 0);

    const positionMap = {};
    const newPositions = [];

    orphans.forEach((node, i) => {
      const col = i % COLS;
      const row = Math.floor(i / COLS);
      const w = parseInt(node.style?.width, 10) || 280;
      const h = node.measured?.height || parseInt(node.data?.extra?.height, 10) || 200;
      const x = startX + col * (w + GAP);
      const y = startY + row * (h + GAP);
      positionMap[node.id] = { x, y };
      newPositions.push({ card_id: node.id, x, y });
    });

    setNodes((prev) =>
      prev.map((node) => {
        const newPos = positionMap[node.id];
        if (!newPos) return node;
        return { ...node, position: { x: newPos.x, y: newPos.y } };
      })
    );

    if (newPositions.length > 0) {
      batchUpdateCardPositions(boardId, newPositions).catch((err) => {
        console.error('Failed to save tidy-up positions:', err);
      });
    }
  }, [nodes, edges, setNodes, boardId]);

  return { applyAutoLayout, tidyUp };
}
