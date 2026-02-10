import { useEffect, useRef, useState } from 'react';
import { CARD_COLORS } from '../utils.js';
import '../styles/CardContextMenu.css';

const AI_ACTIONS = [
  { key: 'summarize', label: 'Summarize', icon: '📋' },
  { key: 'expand', label: 'Expand', icon: '📖' },
  { key: 'key_points', label: 'Key Points', icon: '🎯' },
  { key: 'ask_council', label: 'Ask Council', icon: '🏛️' },
  { key: 'mind_map', label: 'Mind Map', icon: '🗺️' },
];

export default function CardContextMenu({ x, y, nodeId, cardType, isKnowledge, onAction, onDelete, onToggleKnowledge, onClose, onEdit, onColorChange, onDiscuss }) {
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

  const isEditable = cardType === 'note' || cardType === 'link' || isKnowledge;

  return (
    <div className="card-context-menu" style={style} ref={menuRef}>
      {isEditable && onEdit && (
        <>
          <button
            className="card-context-menu__item"
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
          onClick={() => onAction(nodeId, action.key)}
        >
          <span className="card-context-menu__item-icon">{action.icon}</span>
          {action.label}
        </button>
      ))}

      <button
        className="card-context-menu__item"
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
        onClick={() => { onDiscuss?.(nodeId); onClose(); }}
      >
        <span className="card-context-menu__item-icon">💬</span>
        Discuss in Chat
      </button>

      <div className="card-context-menu__divider" />

      <button
        className="card-context-menu__item card-context-menu__item--danger"
        onClick={() => onDelete(nodeId)}
      >
        <span className="card-context-menu__item-icon">🗑️</span>
        Delete
      </button>
    </div>
  );
}
