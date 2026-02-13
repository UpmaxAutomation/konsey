import { useEffect, useRef, useCallback } from 'react';
import '../styles/EdgeContextMenu.css';

const EDGE_COLORS = [
  { key: 'gray', color: '#94a3b8' },
  { key: 'red', color: '#ef4444' },
  { key: 'orange', color: '#f59e0b' },
  { key: 'yellow', color: '#eab308' },
  { key: 'green', color: '#10b981' },
  { key: 'blue', color: '#3b82f6' },
  { key: 'purple', color: '#8b5cf6' },
  { key: 'pink', color: '#ec4899' },
];

const PATH_TYPES = [
  { key: 'bezier', label: 'Bezier' },
  { key: 'straight', label: 'Straight' },
  { key: 'step', label: 'Step' },
];

const THICKNESS_OPTIONS = [
  { key: 1, label: 'Thin (1px)' },
  { key: 2, label: 'Normal (2px)' },
  { key: 3, label: 'Thick (3px)' },
];

const ARROW_OPTIONS = [
  { key: 'one-way', label: 'One-way' },
  { key: 'bidirectional', label: 'Bidirectional' },
  { key: 'none', label: 'No arrows' },
];

export default function EdgeContextMenu({
  x, y, edgeId, edgeData,
  onEditLabel, onUpdateEdge, onReverse, onDelete, onClose,
}) {
  const menuRef = useRef(null);

  // Close on click outside
  useEffect(() => {
    function handleClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        onClose();
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [onClose]);

  // Focus first menu item on mount
  useEffect(() => {
    const first = menuRef.current?.querySelector('[role="menuitem"]');
    if (first) first.focus();
  }, []);

  // Arrow-key navigation through menu items
  const handleMenuKeyDown = useCallback((e) => {
    if (e.key === 'Escape') { e.preventDefault(); onClose(); return; }
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault();
    const items = Array.from(menuRef.current?.querySelectorAll('[role="menuitem"]') || []);
    if (!items.length) return;
    const idx = items.indexOf(document.activeElement);
    if (e.key === 'ArrowDown') {
      items[(idx + 1) % items.length].focus();
    } else {
      items[(idx - 1 + items.length) % items.length].focus();
    }
  }, [onClose]);

  const style = {
    left: Math.min(x, window.innerWidth - 240),
    top: Math.min(y, window.innerHeight - 400),
  };

  const currentStyle = edgeData?.style || {};

  const handleColorChange = (color) => {
    onUpdateEdge(edgeId, { style: { ...currentStyle, color } });
    onClose();
  };

  const handlePathType = (pathType) => {
    onUpdateEdge(edgeId, { style: { ...currentStyle, pathType } });
    onClose();
  };

  const handleThickness = (strokeWidth) => {
    onUpdateEdge(edgeId, { style: { ...currentStyle, strokeWidth } });
    onClose();
  };

  const handleArrowDirection = (key) => {
    const updates = { ...currentStyle };
    if (key === 'one-way') {
      updates.bidirectional = false;
      updates.noArrows = false;
    } else if (key === 'bidirectional') {
      updates.bidirectional = true;
      updates.noArrows = false;
    } else {
      updates.bidirectional = false;
      updates.noArrows = true;
    }
    onUpdateEdge(edgeId, { style: updates });
    onClose();
  };

  const currentArrow = currentStyle.noArrows
    ? 'none'
    : currentStyle.bidirectional
      ? 'bidirectional'
      : 'one-way';

  return (
    <div className="edge-context-menu" style={style} ref={menuRef} role="menu" aria-label="Edge actions" onKeyDown={handleMenuKeyDown}>
      <button
        className="edge-context-menu__item"
        role="menuitem"
        onClick={() => { onEditLabel(edgeId); onClose(); }}
      >
        Edit Label
      </button>

      <div className="edge-context-menu__separator" />

      <div className="edge-context-menu__section-label">Color</div>
      <div className="edge-context-menu__color-row">
        {EDGE_COLORS.map((c) => (
          <button
            key={c.key}
            className={`edge-context-menu__color-swatch${currentStyle.color === c.color ? ' active' : ''}`}
            style={{ background: c.color }}
            title={c.key}
            onClick={() => handleColorChange(c.color)}
          />
        ))}
      </div>

      <div className="edge-context-menu__separator" />

      <div className="edge-context-menu__section-label">Style</div>
      {PATH_TYPES.map((pt) => (
        <button
          key={pt.key}
          className={`edge-context-menu__item${(currentStyle.pathType || 'bezier') === pt.key ? ' active' : ''}`}
          role="menuitem"
          onClick={() => handlePathType(pt.key)}
        >
          {pt.label}
        </button>
      ))}

      <div className="edge-context-menu__separator" />

      <div className="edge-context-menu__section-label">Thickness</div>
      {THICKNESS_OPTIONS.map((t) => (
        <button
          key={t.key}
          className={`edge-context-menu__item${(currentStyle.strokeWidth || 1) === t.key ? ' active' : ''}`}
          role="menuitem"
          onClick={() => handleThickness(t.key)}
        >
          {t.label}
        </button>
      ))}

      <div className="edge-context-menu__separator" />

      <div className="edge-context-menu__section-label">Arrows</div>
      {ARROW_OPTIONS.map((a) => (
        <button
          key={a.key}
          className={`edge-context-menu__item${currentArrow === a.key ? ' active' : ''}`}
          role="menuitem"
          onClick={() => handleArrowDirection(a.key)}
        >
          {a.label}
        </button>
      ))}

      <div className="edge-context-menu__separator" />

      <button
        className="edge-context-menu__item"
        role="menuitem"
        onClick={() => { onReverse(edgeId); onClose(); }}
      >
        Reverse Direction
      </button>

      <button
        className="edge-context-menu__item edge-context-menu__item--danger"
        role="menuitem"
        onClick={() => { onDelete(edgeId); onClose(); }}
      >
        Delete
      </button>
    </div>
  );
}
