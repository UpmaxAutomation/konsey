import { useMemo, useRef } from 'react';

/**
 * Computes a backlinks map from edges: for each target node,
 * returns an array of { edgeType, sourceTitle, sourceId } entries.
 *
 * Uses a ref for nodes so that the memo only recomputes when edges change,
 * while always reading the latest node titles.
 *
 * @param {Array} edges - ReactFlow edges
 * @param {Array} nodes - ReactFlow nodes (for title lookup)
 * @returns {Object} Map of targetId -> backlink entries
 */
export default function useBacklinks(edges, nodes) {
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;

  return useMemo(() => {
    const currentNodes = nodesRef.current;
    const titleMap = {};
    for (const n of currentNodes) {
      titleMap[n.id] = n.data?.title || n.data?.card_type || 'Card';
    }
    const map = {};
    for (const edge of edges) {
      if (!map[edge.target]) map[edge.target] = [];
      map[edge.target].push({
        edgeType: edge.data?.edge_type || 'related',
        sourceTitle: titleMap[edge.source] || 'Card',
        sourceId: edge.source,
      });
    }
    return map;
  }, [edges]);
}
