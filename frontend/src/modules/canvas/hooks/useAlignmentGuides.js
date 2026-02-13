import { useState, useCallback, useRef } from 'react';

const SNAP_THRESHOLD = 5; // pixels in flow coordinates
const GUIDE_COLOR = '#6366f1';

/**
 * Provides smart alignment guides when dragging nodes.
 * Returns:
 *  - guides: array of { x1, y1, x2, y2, type } lines to render
 *  - onNodeDrag: handler to wire into ReactFlow
 *  - onNodeDragStop: handler to clear guides
 *  - alignSelected: functions for explicit alignment of selected nodes
 */
export default function useAlignmentGuides(nodes, setNodes) {
  const [guides, setGuides] = useState([]);
  const snappedRef = useRef({ x: null, y: null });

  const onNodeDrag = useCallback((_event, draggedNode) => {
    const otherNodes = nodes.filter(
      (n) => n.id !== draggedNode.id && !n.selected && n.type !== 'sectionNode'
    );
    if (otherNodes.length === 0) {
      setGuides([]);
      return;
    }

    const dw = draggedNode.measured?.width || 280;
    const dh = draggedNode.measured?.height || 200;
    const dLeft = draggedNode.position.x;
    const dRight = dLeft + dw;
    const dTop = draggedNode.position.y;
    const dBottom = dTop + dh;
    const dCx = dLeft + dw / 2;
    const dCy = dTop + dh / 2;

    const newGuides = [];
    let snapX = null;
    let snapY = null;
    let bestDx = SNAP_THRESHOLD + 1;
    let bestDy = SNAP_THRESHOLD + 1;

    for (const node of otherNodes) {
      const nw = node.measured?.width || 280;
      const nh = node.measured?.height || 200;
      const nLeft = node.position.x;
      const nRight = nLeft + nw;
      const nTop = node.position.y;
      const nBottom = nTop + nh;
      const nCx = nLeft + nw / 2;
      const nCy = nTop + nh / 2;

      // Vertical alignment checks (x-axis snapping)
      const xChecks = [
        { dragVal: dLeft, nodeVal: nLeft, type: 'left-left' },
        { dragVal: dRight, nodeVal: nRight, type: 'right-right' },
        { dragVal: dLeft, nodeVal: nRight, type: 'left-right' },
        { dragVal: dRight, nodeVal: nLeft, type: 'right-left' },
        { dragVal: dCx, nodeVal: nCx, type: 'center-x' },
      ];

      for (const check of xChecks) {
        const dist = Math.abs(check.dragVal - check.nodeVal);
        if (dist < SNAP_THRESHOLD && dist < bestDx) {
          bestDx = dist;
          snapX = check.nodeVal - (check.dragVal - dLeft);
          const minY = Math.min(dTop, nTop) - 20;
          const maxY = Math.max(dBottom, nBottom) + 20;
          newGuides.push({
            x1: check.nodeVal,
            y1: minY,
            x2: check.nodeVal,
            y2: maxY,
            type: 'vertical',
          });
        }
      }

      // Horizontal alignment checks (y-axis snapping)
      const yChecks = [
        { dragVal: dTop, nodeVal: nTop, type: 'top-top' },
        { dragVal: dBottom, nodeVal: nBottom, type: 'bottom-bottom' },
        { dragVal: dTop, nodeVal: nBottom, type: 'top-bottom' },
        { dragVal: dBottom, nodeVal: nTop, type: 'bottom-top' },
        { dragVal: dCy, nodeVal: nCy, type: 'center-y' },
      ];

      for (const check of yChecks) {
        const dist = Math.abs(check.dragVal - check.nodeVal);
        if (dist < SNAP_THRESHOLD && dist < bestDy) {
          bestDy = dist;
          snapY = check.nodeVal - (check.dragVal - dTop);
          const minX = Math.min(dLeft, nLeft) - 20;
          const maxX = Math.max(dRight, nRight) + 20;
          newGuides.push({
            x1: minX,
            y1: check.nodeVal,
            x2: maxX,
            y2: check.nodeVal,
            type: 'horizontal',
          });
        }
      }
    }

    // Keep only the best guide per axis (remove duplicates from earlier iterations)
    const finalGuides = [];
    let hasVert = false;
    let hasHoriz = false;
    for (let i = newGuides.length - 1; i >= 0; i--) {
      if (newGuides[i].type === 'vertical' && !hasVert) {
        finalGuides.push(newGuides[i]);
        hasVert = true;
      }
      if (newGuides[i].type === 'horizontal' && !hasHoriz) {
        finalGuides.push(newGuides[i]);
        hasHoriz = true;
      }
    }

    snappedRef.current = { x: snapX, y: snapY };
    setGuides(finalGuides);
  }, [nodes]);

  const onNodeDragStop = useCallback(() => {
    setGuides([]);
    snappedRef.current = { x: null, y: null };
  }, []);

  // ── Alignment actions for selected nodes ───────────────────────────
  const alignSelected = useCallback((action, selectedNodes) => {
    if (selectedNodes.length < 2) return;
    const cards = selectedNodes.filter((n) => n.type !== 'sectionNode');
    if (cards.length < 2) return;

    setNodes((nds) => {
      const idSet = new Set(cards.map((n) => n.id));
      const targets = nds.filter((n) => idSet.has(n.id));

      let updates = {};

      switch (action) {
        case 'align-left': {
          const minX = Math.min(...targets.map((n) => n.position.x));
          targets.forEach((n) => { updates[n.id] = { ...n.position, x: minX }; });
          break;
        }
        case 'align-right': {
          const maxRight = Math.max(...targets.map((n) => n.position.x + (n.measured?.width || 280)));
          targets.forEach((n) => { updates[n.id] = { ...n.position, x: maxRight - (n.measured?.width || 280) }; });
          break;
        }
        case 'align-top': {
          const minY = Math.min(...targets.map((n) => n.position.y));
          targets.forEach((n) => { updates[n.id] = { ...n.position, y: minY }; });
          break;
        }
        case 'align-bottom': {
          const maxBottom = Math.max(...targets.map((n) => n.position.y + (n.measured?.height || 200)));
          targets.forEach((n) => { updates[n.id] = { ...n.position, y: maxBottom - (n.measured?.height || 200) }; });
          break;
        }
        case 'center-h': {
          const avgX = targets.reduce((sum, n) => sum + n.position.x + (n.measured?.width || 280) / 2, 0) / targets.length;
          targets.forEach((n) => { updates[n.id] = { ...n.position, x: avgX - (n.measured?.width || 280) / 2 }; });
          break;
        }
        case 'center-v': {
          const avgY = targets.reduce((sum, n) => sum + n.position.y + (n.measured?.height || 200) / 2, 0) / targets.length;
          targets.forEach((n) => { updates[n.id] = { ...n.position, y: avgY - (n.measured?.height || 200) / 2 }; });
          break;
        }
        case 'distribute-h': {
          const sorted = [...targets].sort((a, b) => a.position.x - b.position.x);
          const first = sorted[0];
          const last = sorted[sorted.length - 1];
          const totalSpan = (last.position.x + (last.measured?.width || 280)) - first.position.x;
          const totalWidth = sorted.reduce((sum, n) => sum + (n.measured?.width || 280), 0);
          const gap = (totalSpan - totalWidth) / (sorted.length - 1);
          let currentX = first.position.x;
          sorted.forEach((n) => {
            updates[n.id] = { ...n.position, x: currentX };
            currentX += (n.measured?.width || 280) + gap;
          });
          break;
        }
        case 'distribute-v': {
          const sorted = [...targets].sort((a, b) => a.position.y - b.position.y);
          const first = sorted[0];
          const last = sorted[sorted.length - 1];
          const totalSpan = (last.position.y + (last.measured?.height || 200)) - first.position.y;
          const totalHeight = sorted.reduce((sum, n) => sum + (n.measured?.height || 200), 0);
          const gap = (totalSpan - totalHeight) / (sorted.length - 1);
          let currentY = first.position.y;
          sorted.forEach((n) => {
            updates[n.id] = { ...n.position, y: currentY };
            currentY += (n.measured?.height || 200) + gap;
          });
          break;
        }
        default:
          break;
      }

      return nds.map((n) => (updates[n.id] ? { ...n, position: updates[n.id] } : n));
    });
  }, [setNodes]);

  return { guides, onNodeDrag, onNodeDragStop, alignSelected };
}
