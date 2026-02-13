import { useMemo, useState } from 'react';
import '../styles/SelectionToolbar.css';

export default function SelectionToolbar({ selectedNodes, onGroup, onUngroup, onDelete, onMerge, onAlign, reactFlowInstance }) {
  const isSectionSelected = selectedNodes.length === 1 && selectedNodes[0].type === 'sectionNode';
  const cardNodes = selectedNodes.filter(n => n.type !== 'sectionNode');
  const canGroup = cardNodes.length >= 2;
  const canMerge = cardNodes.length >= 2;
  const canAlign = cardNodes.length >= 2;
  const showToolbar = canGroup || isSectionSelected;

  const [showAlignMenu, setShowAlignMenu] = useState(false);

  // Calculate centroid position in screen coords
  const position = useMemo(() => {
    if (!showToolbar || !reactFlowInstance) return null;
    const nodes = selectedNodes;
    const avgX = nodes.reduce((sum, n) => sum + n.position.x + (n.measured?.width || 280) / 2, 0) / nodes.length;
    const avgY = Math.min(...nodes.map(n => n.position.y));
    const screen = reactFlowInstance.flowToScreenPosition({ x: avgX, y: avgY });
    return { x: screen.x, y: screen.y - 50 };
  }, [selectedNodes, showToolbar, reactFlowInstance]);

  if (!showToolbar || !position) return null;

  const handleAlign = (action) => {
    onAlign?.(action, selectedNodes);
    setShowAlignMenu(false);
  };

  return (
    <div
      className="selection-toolbar"
      style={{ left: position.x, top: position.y, transform: 'translateX(-50%)' }}
    >
      {canGroup && (
        <button className="selection-toolbar__btn" onClick={onGroup} title="Group into section">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
          Group
        </button>
      )}
      {canMerge && (
        <button className="selection-toolbar__btn" onClick={onMerge} title="Merge selected cards into one">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
          </svg>
          Merge
        </button>
      )}
      {canAlign && (
        <div className="selection-toolbar__align-wrap">
          <button
            className="selection-toolbar__btn"
            onClick={() => setShowAlignMenu((p) => !p)}
            title="Align & distribute"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 3v18M9 6h6v4H9zM9 14h10v4H9z" />
            </svg>
            Align
          </button>
          {showAlignMenu && (
            <div className="selection-toolbar__align-menu">
              <button onClick={() => handleAlign('align-left')} title="Align Left">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18M9 6h6v4H9zM9 14h10v4H9z" /></svg>
                Left
              </button>
              <button onClick={() => handleAlign('align-right')} title="Align Right">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 3v18M5 6h10v4H5zM9 14h6v4H9z" /></svg>
                Right
              </button>
              <button onClick={() => handleAlign('align-top')} title="Align Top">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3h18M6 9v6h4V9zM14 9v10h4V9z" /></svg>
                Top
              </button>
              <button onClick={() => handleAlign('align-bottom')} title="Align Bottom">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 21h18M6 5v10h4V5zM14 9v6h4V9z" /></svg>
                Bottom
              </button>
              <div className="selection-toolbar__align-divider" />
              <button onClick={() => handleAlign('center-h')} title="Center Horizontally">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 3v18M6 6h12v4H6zM8 14h8v4H8z" /></svg>
                Center H
              </button>
              <button onClick={() => handleAlign('center-v')} title="Center Vertically">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h18M6 6v12h4V6zM14 8v8h4V8z" /></svg>
                Center V
              </button>
              <div className="selection-toolbar__align-divider" />
              <button onClick={() => handleAlign('distribute-h')} title="Distribute Horizontally">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18M21 3v18M8 8h2v8H8zM14 8h2v8h-2z" /></svg>
                Distribute H
              </button>
              <button onClick={() => handleAlign('distribute-v')} title="Distribute Vertically">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3h18M3 21h18M8 8v2h8V8zM8 14v2h8v-2z" /></svg>
                Distribute V
              </button>
            </div>
          )}
        </div>
      )}
      {isSectionSelected && (
        <button className="selection-toolbar__btn" onClick={() => {
          const sectionId = selectedNodes[0].id.replace('section-', '');
          onUngroup(sectionId);
        }} title="Ungroup section">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M16 3h5v5M8 3H3v5M16 21h5v-5M8 21H3v-5" />
          </svg>
          Ungroup
        </button>
      )}
      <button className="selection-toolbar__btn selection-toolbar__btn--danger" onClick={onDelete} title="Delete selected">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2" />
        </svg>
        Delete
      </button>
    </div>
  );
}
