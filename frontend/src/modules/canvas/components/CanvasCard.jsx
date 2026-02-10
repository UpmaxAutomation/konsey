import { useState, useRef, useEffect, useCallback, Component } from 'react';
import { Handle, Position } from '@xyflow/react';
import SafeMarkdown from '../../../shared/components/SafeMarkdown';
import CardEditor from './CardEditor';
import SynthesisExpander from './SynthesisExpander';
import { useBoardActions } from '../BoardContext.js';
import '../styles/CanvasCard.css';

/** Inline error boundary for card editor — prevents full-page crash */
class EditorErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(err) { console.error('CardEditor crash:', err); }
  render() {
    if (this.state.error) {
      return (
        <div className="canvas-card__editor-error" style={{ padding: 12, color: '#e74c3c', fontSize: 12 }}>
          <strong>Editor error:</strong> {this.state.error.message}
          <button onClick={() => this.setState({ error: null })} style={{ marginLeft: 8, cursor: 'pointer' }}>
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

/** Heptabase-inspired accent color system per card type. */
const TYPE_CONFIG = {
  note:              { label: 'Note',      accent: '#6366f1', headerTint: 'rgba(99,102,241,0.04)',  icon: '\u270E' },
  knowledge:         { label: 'Knowledge', accent: '#8b5cf6', headerTint: 'rgba(139,92,246,0.06)',  icon: '\u25C8' },
  query:             { label: 'Query',     accent: '#f59e0b', headerTint: 'rgba(245,158,11,0.05)',  icon: '?' },
  council_response:  { label: 'Response',  accent: '#06b6d4', headerTint: 'rgba(6,182,212,0.04)',   icon: '\u25B7' },
  council_synthesis: { label: 'Synthesis', accent: '#10b981', headerTint: 'rgba(16,185,129,0.06)',  icon: '\u2726' },
  file_ref:          { label: 'File',      accent: '#64748b', headerTint: 'rgba(100,116,139,0.04)', icon: '\u25A1' },
  link:              { label: 'Link',      accent: '#3b82f6', headerTint: 'rgba(59,130,246,0.04)',  icon: '\u2197' },
  board_ref:         { label: 'Board',     accent: '#8b5cf6', headerTint: 'rgba(139,92,246,0.04)',  icon: '\uD83D\uDCC1' },
  workflow_output:   { label: 'Workflow',  accent: '#a855f7', headerTint: 'rgba(168,85,247,0.05)',  icon: '\u2699' },
};

const EDITABLE_TYPES = new Set(['note', 'link']);

function wordCount(text) {
  return text ? text.trim().split(/\s+/).filter(Boolean).length : 0;
}

function formatDate(dateStr) {
  if (!dateStr) return null;
  try {
    const diff = Date.now() - new Date(dateStr).getTime();
    const min = Math.floor(diff / 60000);
    if (min < 1) return 'just now';
    if (min < 60) return `${min}m ago`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}h ago`;
    const day = Math.floor(hr / 24);
    if (day < 7) return `${day}d ago`;
    return new Date(dateStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch { return null; }
}

function CanvasCard({ data, selected }) {
  const [collapsed, setCollapsed] = useState(false);
  const [showThinking, setShowThinking] = useState(false);
  const [showBacklinks, setShowBacklinks] = useState(false);
  const [showMore, setShowMore] = useState(false);
  const [isOverflowing, setIsOverflowing] = useState(false);
  const [cardWidth, setCardWidth] = useState(data.width || null);
  const contentRef = useRef(null);
  const resizeRef = useRef(null);

  // Use board context for editing actions — always available, no injection timing issues
  const board = useBoardActions();

  const isKnowledge = data.extra?.is_knowledge;
  const config = isKnowledge ? TYPE_CONFIG.knowledge : (TYPE_CONFIG[data.card_type] || TYPE_CONFIG.note);
  const modelName = data.extra?.model?.split('/').pop();
  const hasThinking = data.extra?.thinking?.trim?.().length > 0;
  const isEditable = EDITABLE_TYPES.has(data.card_type) || isKnowledge;
  const isEditing = isEditable && board?.editingCardId === data.cardId;

  const { isDimmed, isProcessing } = data;
  const backlinks = data.backlinks || [];

  useEffect(() => {
    const el = contentRef.current;
    if (!el || collapsed || isEditing) {
      setIsOverflowing(false);
      return;
    }
    const check = () => setIsOverflowing(el.scrollHeight > el.clientHeight + 2);
    check();
    const timer = setTimeout(check, 200);
    return () => clearTimeout(timer);
  }, [data.content, collapsed, isEditing, showMore]);

  // Auto-save: persist data without closing editor
  const handleAutoSave = useCallback((title, content) => {
    (board?.updateCard || data.onUpdateCard)?.(data.cardId, { title, content });
  }, [board, data.onUpdateCard, data.cardId]);

  // Explicit save (Cmd+Enter): persist data AND close editor
  const handleEditorSave = useCallback((title, content) => {
    (board?.updateCard || data.onUpdateCard)?.(data.cardId, { title, content });
    (board?.clearEditing || data.onClearEditing)?.();
  }, [board, data.onUpdateCard, data.cardId, data.onClearEditing]);

  const handleEditorCancel = useCallback(() => {
    (board?.clearEditing || data.onClearEditing)?.();
  }, [board, data.onClearEditing]);

  const handleCardDoubleClick = useCallback((e) => {
    if (!isEditable || isEditing) return;
    e.stopPropagation();
    (board?.startEditing || data.onStartEditing)?.(data.cardId);
  }, [isEditable, isEditing, board, data.onStartEditing, data.cardId]);

  const handleResizeStart = useCallback((e) => {
    e.stopPropagation();
    e.preventDefault();
    const startX = e.clientX;
    const el = e.target.closest('.canvas-card');
    const startWidth = el ? el.offsetWidth : 280;

    const handleMouseMove = (moveEvent) => {
      const delta = moveEvent.clientX - startX;
      const raw = Math.min(600, Math.max(200, startWidth + delta));
      const snapped = Math.round(raw / 16) * 16;
      setCardWidth(snapped);
      resizeRef.current = snapped;
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      if (resizeRef.current) {
        data.onUpdateCard?.(data.cardId, { width: resizeRef.current });
      }
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [data.onUpdateCard, data.cardId]);

  const createdLabel = formatDate(data.extra?.created_at);
  const words = wordCount(data.content);

  const classNames = [
    'canvas-card',
    `canvas-card--${data.card_type}`,
    isKnowledge && 'canvas-card--knowledge',
    selected && 'canvas-card--selected',
    collapsed && 'canvas-card--collapsed',
    isEditing && 'canvas-card--editing',
    isDimmed && 'canvas-card--dimmed',
    isProcessing && 'canvas-card--processing',
    data.color && 'canvas-card--colored',
  ].filter(Boolean).join(' ');

  return (
    <div
      className={classNames}
      style={{
        '--card-accent': data.color ? `var(--card-${data.color})` : config.accent,
        ...(data.color ? { '--card-color-bg': `var(--card-${data.color}-bg)` } : {}),
        ...(cardWidth ? { width: `${cardWidth}px`, minWidth: `${cardWidth}px`, maxWidth: `${cardWidth}px` } : {}),
      }}
      onDoubleClick={handleCardDoubleClick}
    >
      <Handle type="source" position={Position.Top} id="top" className="canvas-card__handle" />
      <Handle type="target" position={Position.Top} id="top" className="canvas-card__handle" />
      <Handle type="source" position={Position.Left} id="left" className="canvas-card__handle" />
      <Handle type="target" position={Position.Left} id="left" className="canvas-card__handle" />
      <Handle type="source" position={Position.Right} id="right" className="canvas-card__handle" />
      <Handle type="target" position={Position.Right} id="right" className="canvas-card__handle" />

      <div className="canvas-card__header">
        <span className="canvas-card__icon" style={{ color: config.accent }}>{config.icon}</span>
        <span className="canvas-card__type">{config.label}</span>
        {modelName && <span className="canvas-card__model">{modelName}</span>}
        {hasThinking && (
          <button
            className="canvas-card__thinking-toggle nodrag"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); setShowThinking(!showThinking); }}
            title="Toggle reasoning"
            aria-label="Toggle reasoning"
          >
            {'\u{1F9E0}'}
          </button>
        )}
        {isEditable && !collapsed && !isEditing && (
          <button
            className="canvas-card__edit-btn nodrag"
            onPointerDown={(e) => {
              e.stopPropagation();
            }}
            onClick={(e) => {
              e.stopPropagation();
              (board?.startEditing || data.onStartEditing)?.(data.cardId);
            }}
            title="Edit card"
            aria-label="Edit card"
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
        )}
        <button
          className="canvas-card__collapse nodrag"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => { e.stopPropagation(); setCollapsed(!collapsed); }}
          title={collapsed ? 'Expand' : 'Collapse'}
          aria-label={collapsed ? 'Expand card' : 'Collapse card'}
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d={collapsed ? 'M6 9l6 6 6-6' : 'M18 15l-6-6-6 6'} />
          </svg>
        </button>
      </div>

      {!collapsed && isEditing ? (
        <EditorErrorBoundary>
          <CardEditor
            title={data.title || ''}
            content={data.content || ''}
            onSave={handleEditorSave}
            onAutoSave={handleAutoSave}
            onCancel={handleEditorCancel}
            cardType={data.card_type}
            boardCards={data.boardCards || []}
          />
        </EditorErrorBoundary>
      ) : (
        <>
          {data.title && !collapsed && (
            <div
              className={`canvas-card__title${isEditable ? ' nodrag' : ''}`}
              style={isEditable ? { cursor: 'text' } : undefined}
            >
              {data.title}
            </div>
          )}

          {!collapsed && (
            <>
              {hasThinking && showThinking && (
                <div className="canvas-card__thinking">
                  <div className="canvas-card__thinking-label">Reasoning:</div>
                  <SafeMarkdown>{data.extra.thinking}</SafeMarkdown>
                </div>
              )}

              <div
                ref={contentRef}
                className={`canvas-card__content${showMore ? ' canvas-card__content--expanded' : ''}${isEditable ? ' nodrag' : ''}`}
                style={isEditable ? { cursor: 'text' } : undefined}
              >
                {data.card_type === 'board_ref' ? (
                  <div className="canvas-card__board-ref">
                    <span className="canvas-card__board-ref-icon">{'\uD83D\uDCC1'}</span>
                    <span className="canvas-card__board-ref-name">{data.title || 'Sub-board'}</span>
                    <span className="canvas-card__board-ref-hint">Double-click to open</span>
                  </div>
                ) : data.card_type === 'file_ref' ? (
                  <div className="canvas-card__file">
                    <span className="canvas-card__file-icon">{'\u25A1'}</span>
                    <span>{data.extra?.filename || data.title || 'File'}</span>
                  </div>
                ) : data.card_type === 'link' ? (
                  <a
                    href={data.extra?.url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="canvas-card__link"
                  >
                    {data.extra?.url || data.content || 'Link'}
                  </a>
                ) : (
                  <div className="canvas-card__markdown">
                    <SafeMarkdown>{data.content || ''}</SafeMarkdown>
                  </div>
                )}
              </div>

              {(isOverflowing || showMore) && (
                <button
                  className="canvas-card__show-more nodrag"
                  onClick={(e) => { e.stopPropagation(); setShowMore(!showMore); }}
                  aria-label={showMore ? 'Show less content' : 'Show more content'}
                >
                  {showMore ? 'Show less' : 'Show more'}
                </button>
              )}

              {data.card_type === 'council_synthesis' && data.extra?.stage1 && (
                <SynthesisExpander extra={data.extra} />
              )}
            </>
          )}
        </>
      )}

      {!collapsed && !isEditing && (createdLabel || words > 0) && (
        <div className="canvas-card__footer">
          {createdLabel && <span className="canvas-card__footer-date">{createdLabel}</span>}
          {words > 0 && (
            <span className="canvas-card__footer-words">
              {words < 100 ? `${words} words` : `~${Math.max(1, Math.round(words / 200))} min read`}
            </span>
          )}
        </div>
      )}

      {!collapsed && !isEditing && data.propertyBadges?.length > 0 && (
        <div className="canvas-card__badges">
          {data.propertyBadges.map((badge) => (
            <span key={badge.id} className="canvas-card__badge" title={badge.name}>
              {badge.display}
            </span>
          ))}
        </div>
      )}

      {!collapsed && !isEditing && data.tags?.length > 0 && (
        <div className="canvas-card__tags">
          {data.tags.map((tag) => (
            <span
              key={tag.id}
              className="canvas-card__tag"
              style={{ '--tag-color': tag.color || '#94a3b8' }}
            >
              {tag.name}
            </span>
          ))}
        </div>
      )}

      {!collapsed && backlinks.length > 0 && (
        <div className="canvas-card__backlinks">
          <button
            className="canvas-card__backlinks-toggle nodrag"
            onClick={(e) => { e.stopPropagation(); setShowBacklinks(!showBacklinks); }}
            aria-label={`${backlinks.length} backlink${backlinks.length !== 1 ? 's' : ''}, ${showBacklinks ? 'collapse' : 'expand'}`}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            {backlinks.length} backlink{backlinks.length !== 1 ? 's' : ''}
            <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginLeft: 'auto' }}>
              <path d={showBacklinks ? 'M18 15l-6-6-6 6' : 'M6 9l6 6 6-6'} />
            </svg>
          </button>
          {showBacklinks && (
            <div className="canvas-card__backlinks-list nodrag nowheel">
              {backlinks.map((bl) => (
                <div
                  key={bl.sourceId}
                  className="canvas-card__backlink-item"
                  onClick={(e) => { e.stopPropagation(); data.onFocusCard?.(bl.sourceId); }}
                >
                  <span className={`canvas-card__backlink-type canvas-card__backlink-type--${bl.edgeType}`}>
                    {bl.edgeType.replace(/_/g, ' ')}
                  </span>
                  <span className="canvas-card__backlink-title">{bl.sourceTitle}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!collapsed && (
        <div
          className="canvas-card__resize-handle nodrag"
          onMouseDown={handleResizeStart}
          title="Drag to resize"
          aria-label="Resize card"
        />
      )}

      <Handle type="source" position={Position.Bottom} id="bottom" className="canvas-card__handle" />
      <Handle type="target" position={Position.Bottom} id="bottom" className="canvas-card__handle" />
    </div>
  );
}

export default CanvasCard;
