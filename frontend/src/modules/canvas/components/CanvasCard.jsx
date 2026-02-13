import { useState, useRef, useEffect, useCallback, Component, memo } from 'react';
import { Handle, Position, NodeResizer } from '@xyflow/react';
import SafeMarkdown from '../../../shared/components/SafeMarkdown';
import CardEditor from './CardEditor';
import CardAttachments from './CardAttachments';
import { useUploadAttachment } from '../../../api/queries/cardAttachmentQueries';
import BoardRefPreview from './BoardRefPreview';
import SynthesisExpander from './SynthesisExpander';
import LinkedCardOverlay from './LinkedCardOverlay';
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
  linked_card:       { label: 'Linked',   accent: '#06b6d4', headerTint: 'rgba(6,182,212,0.04)',   icon: '\uD83D\uDD17' },
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

const TYPE_LABELS = {
  note: 'Note', knowledge: 'Knowledge', query: 'Query',
  council_response: 'Response', council_synthesis: 'Synthesis',
  file_ref: 'File', link: 'Link', board_ref: 'Board',
  workflow_output: 'Workflow', linked_card: 'Linked',
};

function CanvasCard({ data, selected, dragging }) {
  const [collapsed, setCollapsed] = useState(data.extra?.collapsed ?? false);
  const [showThinking, setShowThinking] = useState(false);
  const [showBacklinks, setShowBacklinks] = useState(false);
  const uploadMutation = useUploadAttachment(data.cardId);
  const [isDropTarget, setIsDropTarget] = useState(false);
  const [selectionPopup, setSelectionPopup] = useState(null);
  const [showPeek, setShowPeek] = useState(false);
  const contentRef = useRef(null);
  const lastSelectionRef = useRef(null);
  const peekTimerRef = useRef(null);

  // Use board context for editing actions — always available, no injection timing issues
  const board = useBoardActions();

  const isKnowledge = data.extra?.is_knowledge;
  const isLinked = data.card_type === 'linked_card';
  const config = isKnowledge ? TYPE_CONFIG.knowledge : (TYPE_CONFIG[data.card_type] || TYPE_CONFIG.note);
  const modelName = data.extra?.model?.split('/').pop();
  const hasThinking = data.extra?.thinking?.trim?.().length > 0;
  const isEditable = !isLinked && (EDITABLE_TYPES.has(data.card_type) || isKnowledge);
  const isEditing = isEditable && board?.editingCardId === data.cardId;

  const { isDimmed, isProcessing } = data;
  const backlinks = data.backlinks || [];

  // Clear extract popup on click outside or selection clear
  useEffect(() => {
    if (!selectionPopup) return;
    const handleDown = (e) => {
      if (!contentRef.current?.contains(e.target)) setSelectionPopup(null);
    };
    document.addEventListener('mousedown', handleDown);
    return () => document.removeEventListener('mousedown', handleDown);
  }, [selectionPopup]);

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

  const toggleCollapsed = useCallback(() => {
    const next = !collapsed;
    setCollapsed(next);
    const updateFn = board?.updateCard || data.onUpdateCard;
    if (updateFn) {
      updateFn(data.cardId, { extra: { ...(data.extra || {}), collapsed: next } });
    }
  }, [collapsed, board, data.onUpdateCard, data.cardId, data.extra]);

  const handleResizeEnd = useCallback((_event, { width, height }) => {
    const updateFn = board?.updateCard || data.onUpdateCard;
    if (updateFn) {
      updateFn(data.cardId, {
        width: Math.round(width),
        extra: { ...(data.extra || {}), height: Math.round(height) },
      });
    }
  }, [board, data.onUpdateCard, data.cardId, data.extra]);

  // Fit-to-content: double-click the resize handle to auto-size the card
  const handleResizeHandleDoubleClick = useCallback((e) => {
    e.stopPropagation();
    const el = contentRef.current;
    if (!el) return;
    const fitHeight = Math.max(80, el.scrollHeight + 80); // +80 for header/footer
    const updateFn = board?.updateCard || data.onUpdateCard;
    if (updateFn) {
      updateFn(data.cardId, {
        extra: { ...(data.extra || {}), height: Math.round(fitHeight) },
      });
    }
  }, [board, data.onUpdateCard, data.cardId, data.extra]);

  // Build a card-shaped drag ghost element for setDragImage
  const buildDragGhost = useCallback((text) => {
    const ghost = document.createElement('div');
    ghost.textContent = text.slice(0, 80) + (text.length > 80 ? '\u2026' : '');
    Object.assign(ghost.style, {
      position: 'fixed', top: '-1000px', left: '-1000px',
      width: '200px', padding: '10px 14px',
      background: '#fff', border: '1px solid #e2e8f0',
      borderTop: '2.5px solid ' + (config.accent || '#6366f1'),
      borderRadius: '8px', fontSize: '12px', lineHeight: '1.5',
      color: '#1e293b', fontFamily: 'Inter, system-ui, sans-serif',
      boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
      overflow: 'hidden', maxHeight: '60px',
    });
    document.body.appendChild(ghost);
    return ghost;
  }, [config.accent]);

  // Drag selected text from content area to canvas (creates a new linked card)
  const handleContentDragStart = useCallback((e) => {
    // Browsers may clear window.getSelection() on dragstart for draggable elements,
    // so fall back to the last known selection captured on mouseup.
    const sel = window.getSelection();
    const selectedText = sel?.toString?.()?.trim() || lastSelectionRef.current || '';
    if (!selectedText || selectedText.length < 5) {
      e.preventDefault();
      return;
    }
    // Stop propagation to prevent ReactFlow from intercepting the drag
    e.stopPropagation();
    const payload = JSON.stringify({
      text: selectedText,
      title: selectedText.slice(0, 60),
      sourceCardId: data.cardId,
    });
    e.dataTransfer.setData('application/x-council-card', payload);
    e.dataTransfer.setData('text/plain', selectedText);
    e.dataTransfer.effectAllowed = 'copy';
    // Show a card-shaped drag ghost instead of the default browser preview
    const ghost = buildDragGhost(selectedText);
    e.dataTransfer.setDragImage(ghost, 100, 20);
    requestAnimationFrame(() => ghost.remove());
  }, [data.cardId, buildDragGhost]);

  // Show floating "Extract to Card" button on text selection in read mode
  const cardRef = useRef(null);
  const handleContentMouseUp = useCallback(() => {
    if (isEditing) return; // bubble toolbar handles this in edit mode
    const sel = window.getSelection();
    const text = sel?.toString?.()?.trim();
    // Persist selection text so handleContentDragStart can use it even if
    // the browser clears the native selection when drag begins.
    lastSelectionRef.current = text || null;
    if (!text || text.length < 3) {
      setSelectionPopup(null);
      return;
    }
    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const card = cardRef.current;
    if (!card) return;
    const cardRect = card.getBoundingClientRect();
    setSelectionPopup({
      text,
      x: rect.left - cardRect.left + rect.width / 2,
      y: rect.top - cardRect.top - 4,
    });
  }, [isEditing]);

  // File drop onto card — triggers attachment upload
  const handleCardDragOver = useCallback((e) => {
    if (e.dataTransfer.types.includes('Files')) {
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = 'copy';
      setIsDropTarget(true);
    }
  }, []);

  const handleCardDragLeave = useCallback((e) => {
    // Only clear if leaving the card entirely
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setIsDropTarget(false);
    }
  }, []);

  const handleCardDrop = useCallback((e) => {
    setIsDropTarget(false);
    const files = e.dataTransfer?.files;
    if (!files?.length) return;
    e.preventDefault();
    e.stopPropagation();
    // Upload files as attachments via React Query mutation
    for (const file of files) {
      uploadMutation.mutate(file);
    }
  }, [uploadMutation]);

  // Peek tooltip: show on hover after 300ms, hide on leave or if editing/dragging
  const handlePeekEnter = useCallback(() => {
    if (isEditing || dragging) return;
    peekTimerRef.current = setTimeout(() => setShowPeek(true), 300);
  }, [isEditing, dragging]);

  const handlePeekLeave = useCallback(() => {
    clearTimeout(peekTimerRef.current);
    setShowPeek(false);
  }, []);

  // Clear peek on editing or dragging changes
  useEffect(() => {
    if (isEditing || dragging) {
      clearTimeout(peekTimerRef.current);
      setShowPeek(false);
    }
  }, [isEditing, dragging]);

  // Cleanup timer on unmount
  useEffect(() => () => clearTimeout(peekTimerRef.current), []);

  const peekSnippet = data.content
    ? data.content.replace(/[#*`>\[\]]/g, '').slice(0, 100) + (data.content.length > 100 ? '\u2026' : '')
    : '';

  const createdLabel = formatDate(data.extra?.created_at);
  const words = wordCount(data.content);

  const classNames = [
    'canvas-card',
    `canvas-card--${data.card_type}`,
    isKnowledge && 'canvas-card--knowledge',
    isLinked && 'canvas-card--linked',
    data.is_library && 'canvas-card--library',
    selected && 'canvas-card--selected',
    collapsed && 'canvas-card--collapsed',
    isEditing && 'canvas-card--editing',
    isDimmed && 'canvas-card--dimmed',
    isProcessing && 'canvas-card--processing',
    data.color && 'canvas-card--colored',
  ].filter(Boolean).join(' ');

  return (
    <div
      ref={cardRef}
      className={`${classNames}${isDropTarget ? ' canvas-card--drop-target' : ''}`}
      style={{
        '--card-accent': data.color ? `var(--card-${data.color})` : config.accent,
        ...(data.color ? { '--card-color-bg': `var(--card-${data.color}-bg)` } : {}),
      }}
      onDragOver={handleCardDragOver}
      onDragLeave={handleCardDragLeave}
      onDrop={handleCardDrop}
      onMouseEnter={handlePeekEnter}
      onMouseLeave={handlePeekLeave}
    >
      <NodeResizer
        minWidth={200}
        maxWidth={700}
        minHeight={80}
        isVisible={selected}
        lineClassName="canvas-card__resize-line"
        handleClassName="canvas-card__resize-control"
        onResizeEnd={handleResizeEnd}
      />
      {/* Invisible double-click target on bottom-right corner for fit-to-content */}
      {selected && (
        <div
          className="canvas-card__fit-handle nodrag"
          onDoubleClick={handleResizeHandleDoubleClick}
          title="Double-click to fit content"
        />
      )}

      {showPeek && !isEditing && !collapsed && (
        <div className="canvas-card__peek">
          <div className="canvas-card__peek-title">{data.title || 'Untitled'}</div>
          {peekSnippet && <div className="canvas-card__peek-content">{peekSnippet}</div>}
          <span className="canvas-card__peek-badge">{TYPE_LABELS[data.card_type] || data.card_type}</span>
        </div>
      )}

      <Handle type="source" position={Position.Top} id="top" className="canvas-card__handle" />
      <Handle type="target" position={Position.Top} id="top" className="canvas-card__handle" />
      <Handle type="source" position={Position.Left} id="left" className="canvas-card__handle" />
      <Handle type="target" position={Position.Left} id="left" className="canvas-card__handle" />
      <Handle type="source" position={Position.Right} id="right" className="canvas-card__handle" />
      <Handle type="target" position={Position.Right} id="right" className="canvas-card__handle" />

      {isLinked && (
        <LinkedCardOverlay
          sourceCardId={data.source_card_id}
          sourceBoardName={data.extra?.source_board_name}
        />
      )}

      <div className="canvas-card__header">
        <span className="canvas-card__icon" style={{ color: config.accent }}>{config.icon}</span>
        <span className="canvas-card__type">{config.label}</span>
        {data.is_library && (
          <span className="canvas-card__library-star" title="Library card">{'\u2B50'}</span>
        )}
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
          onClick={(e) => { e.stopPropagation(); toggleCollapsed(); }}
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
            cardId={data.cardId}
            onSave={handleEditorSave}
            onAutoSave={handleAutoSave}
            onCancel={handleEditorCancel}
            cardType={data.card_type}
            boardCards={data.boardCards || []}
            onExtractToCard={board?.extractToCard}
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
                className="canvas-card__content nodrag nopan"
                style={{ cursor: 'text', userSelect: 'text', WebkitUserSelect: 'text' }}
                draggable
                onDragStart={handleContentDragStart}
                onMouseUp={handleContentMouseUp}
              >
                {data.card_type === 'board_ref' ? (
                  <BoardRefPreview boardId={data.extra?.board_id} title={data.title} />
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

      {!collapsed && !isEditing && (
        <CardAttachments cardId={data.cardId} compact />
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

      <Handle type="source" position={Position.Bottom} id="bottom" className="canvas-card__handle" />
      <Handle type="target" position={Position.Bottom} id="bottom" className="canvas-card__handle" />

      {selectionPopup && !isEditing && (
        <div
          className="canvas-card__extract-popup nodrag"
          style={{ left: selectionPopup.x, top: selectionPopup.y }}
        >
          <button
            className="canvas-card__extract-btn"
            onMouseDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
              board?.extractToCard?.(selectionPopup.text, data.cardId);
              window.getSelection()?.removeAllRanges();
              setSelectionPopup(null);
            }}
          >
            Extract to Card
          </button>
          <span
            className="canvas-card__extract-grip nodrag"
            draggable
            onDragStart={(e) => {
              e.stopPropagation();
              const payload = JSON.stringify({
                text: selectionPopup.text,
                title: selectionPopup.text.slice(0, 60),
                sourceCardId: data.cardId,
              });
              e.dataTransfer.setData('application/x-council-card', payload);
              e.dataTransfer.setData('text/plain', selectionPopup.text);
              e.dataTransfer.effectAllowed = 'copy';
              const ghost = buildDragGhost(selectionPopup.text);
              e.dataTransfer.setDragImage(ghost, 100, 20);
              requestAnimationFrame(() => ghost.remove());
            }}
            onDragEnd={() => {
              window.getSelection()?.removeAllRanges();
              setSelectionPopup(null);
            }}
            title="Drag to canvas to place new card"
          >
            {'\u2630'}
          </span>
        </div>
      )}
    </div>
  );
}

export default memo(CanvasCard, (prev, next) =>
  prev.data === next.data && prev.selected === next.selected
);
