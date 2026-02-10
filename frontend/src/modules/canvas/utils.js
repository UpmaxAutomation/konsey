import { MarkerType } from '@xyflow/react';

export const EDGE_STYLES = {
  derived_from: { stroke: '#94a3b8', strokeWidth: 1.5, animated: false, dashed: false, label: 'derived' },
  ranks_above: { stroke: '#f59e0b', strokeWidth: 1.5, animated: false, dashed: true, label: 'ranks' },
  synthesizes: { stroke: '#10b981', strokeWidth: 2, animated: true, dashed: false, label: 'synthesizes' },
  related: { stroke: '#cbd5e1', strokeWidth: 1, animated: false, dashed: true, label: '' },
  workflow_step: { stroke: '#a855f7', strokeWidth: 1.5, animated: true, dashed: true, label: '' },
};

export function cardToNode(card) {
  const node = {
    id: card.id,
    type: 'canvasCard',
    position: { x: card.position_x, y: card.position_y },
    dragHandle: '.canvas-card__header',
    data: {
      cardId: card.id,
      card_type: card.card_type,
      title: card.title,
      content: card.content,
      color: card.color,
      extra: card.extra,
    },
    style: { width: card.width },
  };
  if (card.section_id) {
    node.parentId = `section-${card.section_id}`;
    node.extent = 'parent';
  }
  return node;
}

/** Normalize legacy handle IDs: "right-source" → "right", "left-target" → "left" */
export function normalizeHandle(h) {
  if (!h) return null;
  return h.replace(/-(?:source|target)$/, '');
}

export function edgeToFlow(edge) {
  const styleCfg = EDGE_STYLES[edge.edge_type] || EDGE_STYLES.related;
  // Merge custom style from edge.style if present
  const customStyle = edge.style || {};
  const stroke = customStyle.color || styleCfg.stroke;
  const strokeWidth = customStyle.strokeWidth || styleCfg.strokeWidth;
  return {
    id: edge.id,
    source: edge.from_card_id,
    target: edge.to_card_id,
    type: 'animatedEdge',
    label: edge.label || styleCfg.label || undefined,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 14,
      height: 14,
      color: stroke,
    },
    sourceHandle: normalizeHandle(edge.source_handle),
    targetHandle: normalizeHandle(edge.target_handle),
    data: { edge_type: edge.edge_type, style: { ...styleCfg, stroke, strokeWidth } },
  };
}

// Card color palette constant
export const CARD_COLORS = [
  { key: 'gray', label: 'Gray', color: 'var(--card-gray)', bg: 'var(--card-gray-bg)' },
  { key: 'red', label: 'Red', color: 'var(--card-red)', bg: 'var(--card-red-bg)' },
  { key: 'orange', label: 'Orange', color: 'var(--card-orange)', bg: 'var(--card-orange-bg)' },
  { key: 'yellow', label: 'Yellow', color: 'var(--card-yellow)', bg: 'var(--card-yellow-bg)' },
  { key: 'green', label: 'Green', color: 'var(--card-green)', bg: 'var(--card-green-bg)' },
  { key: 'blue', label: 'Blue', color: 'var(--card-blue)', bg: 'var(--card-blue-bg)' },
  { key: 'purple', label: 'Purple', color: 'var(--card-purple)', bg: 'var(--card-purple-bg)' },
  { key: 'pink', label: 'Pink', color: 'var(--card-pink)', bg: 'var(--card-pink-bg)' },
];

export function sectionToNode(section) {
  return {
    id: `section-${section.id}`,
    type: 'sectionNode',
    position: { x: section.x, y: section.y },
    data: {
      sectionId: section.id,
      title: section.title,
      color: section.color,
    },
    style: {
      width: section.width,
      height: section.height,
    },
  };
}
