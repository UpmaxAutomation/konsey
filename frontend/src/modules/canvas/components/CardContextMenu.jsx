import { useEffect, useRef, useState, useCallback } from 'react';
import { CARD_COLORS } from '../utils.js';
import '../styles/CardContextMenu.css';

const AI_ACTIONS = [
  { key: 'summarize', label: 'Summarize', icon: '📋' },
  { key: 'expand', label: 'Expand', icon: '📖' },
  { key: 'key_points', label: 'Key Points', icon: '🎯' },
  { key: 'ask_council', label: 'Ask Council', icon: '🏛️' },
  { key: 'mind_map', label: 'Mind Map', icon: '🗺️' },
];

export default function CardContextMenu({ x, y, nodeId, cardType, isKnowledge, isLibrary, sourceCardId, hasMergeProvenance, onAction, onDelete, onToggleKnowledge, onClose, onEdit, onColorChange, onDiscuss, onUnlink, onGoToSource, onToggleLibrary, onDuplicate, onSplit }) {
  const [showCustomPrompt, setShowCustomPrompt] = useState(false);
  const [customPrompt, setCustomPrompt] = useState('');
  const menuRef = useRef(null);
  const inputRef = useRef(null);

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

  // Focus custom prompt input
  useEffect(() => {
    if (showCustomPrompt && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showCustomPrompt]);

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

  // Position adjustment to keep within viewport
  const style = {
    left: Math.min(x, window.innerWidth - 220),
    top: Math.min(y, window.innerHeight - 340),
  };

  const handleCustomSubmit = () => {
    if (customPrompt.trim()) {
      onAction(nodeId, 'custom', customPrompt.trim());
      setCustomPrompt('');
      setShowCustomPrompt(false);
    }
  };

  const isLinked = cardType === 'linked_card';
  const isEditable = (cardType === 'note' || cardType === 'link' || isKnowledge) && !isLinked;

  return (
    <div className="card-context-menu" style={style} ref={menuRef} role="menu" aria-label="Card actions" onKeyDown={handleMenuKeyDown}>
      {isEditable && onEdit && (
        <>
          <button
            className="card-context-menu__item"
            role="menuitem"
            onClick={() => { onEdit(nodeId); onClose(); }}
          >
            <span className="card-context-menu__item-icon">✏️</span>
            Edit
          </button>
          <div className="card-context-menu__divider" />
        </>
      )}
      {/* Color picker */}
      <div className="card-context-menu__section-label">Color</div>
      <div className="card-context-menu__colors">
        <button
          className="card-context-menu__color-btn card-context-menu__color-btn--none"
          onClick={() => { onColorChange?.(nodeId, null); onClose(); }}
          title="Remove color"
          aria-label="Remove color"
        />
        {CARD_COLORS.map((c) => (
          <button
            key={c.key}
            className="card-context-menu__color-btn"
            style={{ backgroundColor: c.color }}
            onClick={() => { onColorChange?.(nodeId, c.key); onClose(); }}
            title={c.label}
            aria-label={`Set color to ${c.label}`}
          />
        ))}
      </div>
      <div className="card-context-menu__divider" />

      <div className="card-context-menu__section-label">AI Actions</div>
      {AI_ACTIONS.map((action) => (
        <button
          key={action.key}
          className="card-context-menu__item"
          role="menuitem"
          onClick={() => onAction(nodeId, action.key)}
        >
          <span className="card-context-menu__item-icon">{action.icon}</span>
          {action.label}
        </button>
      ))}

      <button
        className="card-context-menu__item"
        role="menuitem"
        onClick={() => setShowCustomPrompt(!showCustomPrompt)}
      >
        <span className="card-context-menu__item-icon">✏️</span>
        Custom Prompt...
      </button>

      {showCustomPrompt && (
        <div className="card-context-menu__custom">
          <input
            ref={inputRef}
            className="card-context-menu__custom-input"
            type="text"
            placeholder="Enter your prompt..."
            value={customPrompt}
            onChange={(e) => setCustomPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCustomSubmit();
              if (e.key === 'Escape') { setShowCustomPrompt(false); setCustomPrompt(''); }
            }}
          />
          <button
            className="card-context-menu__custom-submit"
            onClick={handleCustomSubmit}
            disabled={!customPrompt.trim()}
          >
            Run
          </button>
        </div>
      )}

      {cardType === 'note' && onToggleKnowledge && (
        <>
          <div className="card-context-menu__divider" />
          <button
            className="card-context-menu__item"
            role="menuitem"
            onClick={() => { onToggleKnowledge(nodeId); onClose(); }}
          >
            <span className="card-context-menu__item-icon">{isKnowledge ? '📝' : '📚'}</span>
            {isKnowledge ? 'Remove Knowledge Flag' : 'Mark as Knowledge'}
          </button>
        </>
      )}

      <div className="card-context-menu__divider" />
      <button
        className="card-context-menu__item"
        role="menuitem"
        onClick={() => { onDiscuss?.(nodeId); onClose(); }}
      >
        <span className="card-context-menu__item-icon">💬</span>
        Discuss in Chat
      </button>

      {/* Linked card actions */}
      {isLinked && (
        <>
          <div className="card-context-menu__divider" />
          {onGoToSource && sourceCardId && (
            <button
              className="card-context-menu__item"
              role="menuitem"
              onClick={() => { onGoToSource(sourceCardId); onClose(); }}
            >
              <span className="card-context-menu__item-icon">↗️</span>
              Go to Source
            </button>
          )}
          {onUnlink && (
            <button
              className="card-context-menu__item"
              role="menuitem"
              onClick={() => { onUnlink(nodeId); onClose(); }}
            >
              <span className="card-context-menu__item-icon">🔓</span>
              Unlink Card
            </button>
          )}
        </>
      )}

      {/* Library toggle */}
      {onToggleLibrary && !isLinked && (
        <>
          <div className="card-context-menu__divider" />
          <button
            className="card-context-menu__item"
            role="menuitem"
            onClick={() => { onToggleLibrary(nodeId); onClose(); }}
          >
            <span className="card-context-menu__item-icon">{isLibrary ? '⭐' : '☆'}</span>
            {isLibrary ? 'Remove from Library' : 'Save to Library'}
          </button>
        </>
      )}

      {onDuplicate && (
        <>
          <div className="card-context-menu__divider" />
          <button
            className="card-context-menu__item"
            role="menuitem"
            onClick={() => { onDuplicate(nodeId); onClose(); }}
          >
            <span className="card-context-menu__item-icon">📋</span>
            Duplicate
          </button>
        </>
      )}

      {hasMergeProvenance && onSplit && (
        <>
          <div className="card-context-menu__divider" />
          <button
            className="card-context-menu__item"
            role="menuitem"
            onClick={() => { onSplit(nodeId); onClose(); }}
          >
            <span className="card-context-menu__item-icon">✂️</span>
            Split / Unmerge
          </button>
        </>
      )}

      <div className="card-context-menu__divider" />

      <button
        className="card-context-menu__item card-context-menu__item--danger"
        role="menuitem"
        onClick={() => onDelete(nodeId)}
      >
        <span className="card-context-menu__item-icon">🗑️</span>
        Delete
      </button>
    </div>
  );
}
