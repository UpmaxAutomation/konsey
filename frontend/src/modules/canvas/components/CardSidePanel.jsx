import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useReactFlow } from '@xyflow/react';
import TiptapEditor from '../editor/TiptapEditor';
import ColorPicker from './ColorPicker';
import { updateCard } from '../../../api/boards.js';
import { API_BASE, authFetch } from '../../../api/client.js';
import CardAttachments from './CardAttachments';
import '../styles/CardSidePanel.css';

const CARD_TYPES = [
  'note', 'query', 'council_response', 'council_synthesis',
  'board_ref', 'file_ref', 'link',
];

function formatDate(dateStr) {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
    + ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

/**
 * ContentTab - Full editor with title and auto-save
 */
function ContentTab({ card, boardId, onCardUpdated, onExtractToCard }) {
  const [title, setTitle] = useState(card.title || '');
  const [selectionPopup, setSelectionPopup] = useState(null);
  const saveTimerRef = useRef(null);
  const editorWrapperRef = useRef(null);
  const lastSelectionRef = useRef(null);

  // Sync title when switching cards
  useEffect(() => {
    setTitle(card.title || '');
  }, [card.id, card.title]);

  const debouncedSave = useCallback((updates) => {
    clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(async () => {
      try {
        await updateCard(boardId, card.id, updates);
        onCardUpdated?.(card.id, updates);
      } catch (err) {
        console.error('Side panel auto-save failed:', err);
      }
    }, 1000);
  }, [boardId, card.id, onCardUpdated]);

  useEffect(() => {
    return () => clearTimeout(saveTimerRef.current);
  }, []);

  const handleTitleChange = useCallback((e) => {
    const val = e.target.value;
    setTitle(val);
    debouncedSave({ title: val });
  }, [debouncedSave]);

  const handleContentChange = useCallback((md) => {
    debouncedSave({ content: md });
  }, [debouncedSave]);

  // Clear popup when clicking outside
  useEffect(() => {
    if (!selectionPopup) return;
    const handleDown = (e) => {
      if (!editorWrapperRef.current?.contains(e.target)) setSelectionPopup(null);
    };
    document.addEventListener('mousedown', handleDown);
    return () => document.removeEventListener('mousedown', handleDown);
  }, [selectionPopup]);

  const handleEditorMouseUp = useCallback(() => {
    if (!onExtractToCard) return;
    const sel = window.getSelection();
    const text = sel?.toString?.()?.trim();
    lastSelectionRef.current = text || null;
    if (!text || text.length < 3) { setSelectionPopup(null); return; }
    const range = sel.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    const wrapper = editorWrapperRef.current;
    if (!wrapper) return;
    const wrapperRect = wrapper.getBoundingClientRect();
    setSelectionPopup({
      text,
      x: rect.left - wrapperRect.left + rect.width / 2,
      y: rect.top - wrapperRect.top - 4,
    });
  }, [onExtractToCard]);

  return (
    <div className="card-side-panel__content-tab">
      <input
        className="card-side-panel__title-input"
        value={title}
        onChange={handleTitleChange}
        placeholder="Untitled"
        spellCheck={false}
      />
      <div className="card-side-panel__editor-wrapper" ref={editorWrapperRef} onMouseUp={handleEditorMouseUp}>
        {selectionPopup && onExtractToCard && (
          <div
            className="card-side-panel__extract-popup"
            style={{ left: selectionPopup.x, top: selectionPopup.y }}
          >
            <button
              className="card-side-panel__extract-btn"
              onMouseDown={(e) => {
                e.stopPropagation();
                e.preventDefault();
                onExtractToCard(selectionPopup.text, card.id);
                window.getSelection()?.removeAllRanges();
                setSelectionPopup(null);
              }}
            >
              Extract to Card
            </button>
            <span
              className="card-side-panel__extract-grip"
              draggable
              onDragStart={(e) => {
                e.stopPropagation();
                const payload = JSON.stringify({
                  text: selectionPopup.text,
                  title: selectionPopup.text.slice(0, 60),
                  sourceCardId: card.id,
                });
                e.dataTransfer.setData('application/x-council-card', payload);
                e.dataTransfer.setData('text/plain', selectionPopup.text);
                e.dataTransfer.effectAllowed = 'copy';
              }}
              title="Drag to place new card"
            >
              &#x2630;
            </span>
          </div>
        )}
        <TiptapEditor
          key={card.id}
          content={card.content || ''}
          cardId={card.id}
          onSave={() => {}}
          onCancel={() => {}}
          onContentChange={handleContentChange}
          placeholder="Start writing..."
          autoFocus={false}
        />
      </div>
      <div className="card-side-panel__meta">
        <span className="card-side-panel__type-badge">{card.card_type || 'note'}</span>
        <span>Created {formatDate(card.created_at)}</span>
        <span>Updated {formatDate(card.updated_at)}</span>
      </div>
    </div>
  );
}

/**
 * PropertiesTab - Card type, color, tags, timestamps
 */
function PropertiesTab({ card, boardId, onCardUpdated }) {
  const [cardType, setCardType] = useState(card.card_type || 'note');
  const [color, setColor] = useState(card.color || null);
  const [tags, setTags] = useState([]);
  const [loadingTags, setLoadingTags] = useState(false);

  // Sync state when switching cards
  useEffect(() => {
    setCardType(card.card_type || 'note');
    setColor(card.color || null);
  }, [card.id, card.card_type, card.color]);

  // Load tags
  useEffect(() => {
    let cancelled = false;
    setLoadingTags(true);
    authFetch(`${API_BASE}/boards/${boardId}/cards/${card.id}/tags`)
      .then(r => r.ok ? r.json() : { tags: [] })
      .then(data => { if (!cancelled) setTags(data.tags || []); })
      .catch(() => { if (!cancelled) setTags([]); })
      .finally(() => { if (!cancelled) setLoadingTags(false); });
    return () => { cancelled = true; };
  }, [boardId, card.id]);

  const handleTypeChange = useCallback(async (e) => {
    const newType = e.target.value;
    setCardType(newType);
    try {
      await updateCard(boardId, card.id, { card_type: newType });
      onCardUpdated?.(card.id, { card_type: newType });
    } catch (err) {
      console.error('Failed to update card type:', err);
    }
  }, [boardId, card.id, onCardUpdated]);

  const handleColorChange = useCallback(async (newColor) => {
    setColor(newColor);
    try {
      await updateCard(boardId, card.id, { color: newColor });
      onCardUpdated?.(card.id, { color: newColor });
    } catch (err) {
      console.error('Failed to update card color:', err);
    }
  }, [boardId, card.id, onCardUpdated]);

  const handleRemoveTag = useCallback(async (tagId) => {
    try {
      await authFetch(`${API_BASE}/boards/${boardId}/cards/${card.id}/tags/${tagId}`, { method: 'DELETE' });
      setTags(prev => prev.filter(t => t.id !== tagId));
    } catch (err) {
      console.error('Failed to remove tag:', err);
    }
  }, [boardId, card.id]);

  return (
    <div className="card-side-panel__props">
      <div className="card-side-panel__prop-group">
        <label className="card-side-panel__prop-label">Card Type</label>
        <select
          className="card-side-panel__prop-select"
          value={cardType}
          onChange={handleTypeChange}
        >
          {CARD_TYPES.map(t => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      <div className="card-side-panel__prop-group">
        <label className="card-side-panel__prop-label">Color</label>
        <ColorPicker selected={color} onSelect={handleColorChange} showRemove />
      </div>

      <div className="card-side-panel__prop-group">
        <label className="card-side-panel__prop-label">Tags</label>
        <div className="card-side-panel__tags">
          {loadingTags ? (
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>Loading...</span>
          ) : tags.length === 0 ? (
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>No tags</span>
          ) : tags.map(tag => (
            <span key={tag.id} className="card-side-panel__tag">
              {tag.name || tag.tag_name || tag.id}
              <button
                className="card-side-panel__tag-remove"
                onClick={() => handleRemoveTag(tag.id)}
                aria-label="Remove tag"
              >
                &times;
              </button>
            </span>
          ))}
        </div>
      </div>

      {card.section_id && (
        <div className="card-side-panel__prop-group">
          <label className="card-side-panel__prop-label">Section</label>
          <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>Section {card.section_id}</span>
        </div>
      )}

      <div className="card-side-panel__prop-group">
        <label className="card-side-panel__prop-label">Timestamps</label>
        <div className="card-side-panel__timestamps">
          <span>Created: {formatDate(card.created_at)}</span>
          <span>Updated: {formatDate(card.updated_at)}</span>
        </div>
      </div>

      <div className="card-side-panel__prop-group">
        <label className="card-side-panel__prop-label">Attachments</label>
        <CardAttachments cardId={card.id} />
      </div>
    </div>
  );
}

/**
 * BacklinksTab - Shows all connected cards (incoming and outgoing)
 */
function BacklinksTab({ cardId, edges, nodes, onNavigateToCard }) {
  const connections = useMemo(() => {
    const result = [];
    const titleMap = {};
    for (const n of nodes) {
      titleMap[n.id] = n.data?.title || n.data?.card_type || 'Card';
    }

    for (const edge of edges) {
      if (edge.target === cardId) {
        result.push({
          id: edge.id,
          cardId: edge.source,
          title: titleMap[edge.source] || 'Card',
          edgeType: edge.data?.edge_type || edge.label || 'related',
          direction: 'incoming',
        });
      } else if (edge.source === cardId) {
        result.push({
          id: edge.id,
          cardId: edge.target,
          title: titleMap[edge.target] || 'Card',
          edgeType: edge.data?.edge_type || edge.label || 'related',
          direction: 'outgoing',
        });
      }
    }
    return result;
  }, [cardId, edges, nodes]);

  if (connections.length === 0) {
    return (
      <div className="card-side-panel__backlinks-empty">
        No connections yet. Link cards by dragging edges between handles.
      </div>
    );
  }

  return (
    <div className="card-side-panel__backlinks">
      {connections.map(conn => (
        <div
          key={conn.id}
          className="card-side-panel__backlink"
          onClick={() => onNavigateToCard(conn.cardId)}
        >
          <span className="card-side-panel__backlink-arrow">
            {conn.direction === 'incoming' ? '\u2190' : '\u2192'}
          </span>
          <div className="card-side-panel__backlink-info">
            <span className="card-side-panel__backlink-title">{conn.title}</span>
            <span className="card-side-panel__backlink-type">
              {conn.edgeType.replace(/_/g, ' ')} &middot; {conn.direction}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * CardSidePanel - Rich side panel for card editing, properties, and backlinks.
 * Opens on double-click, slides in from the right.
 */
export default function CardSidePanel({
  card,
  boardId,
  edges,
  nodes,
  onClose,
  onCardUpdated,
  onNavigateToCard,
  onExtractToCard,
}) {
  const [activeTab, setActiveTab] = useState('content');
  const [panelWidth, setPanelWidth] = useState(420);
  const resizingRef = useRef(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(420);
  const reactFlow = useReactFlow();

  // Escape to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Navigate to card: center viewport + switch side panel
  const handleNavigateToCard = useCallback((targetCardId) => {
    const node = nodes.find(n => n.id === targetCardId);
    if (node) {
      reactFlow.setCenter(
        node.position.x + 140,
        node.position.y + 100,
        { zoom: 1.2, duration: 400 }
      );
    }
    onNavigateToCard?.(targetCardId);
  }, [nodes, reactFlow, onNavigateToCard]);

  // Resize handlers
  const handleResizeStart = useCallback((e) => {
    e.preventDefault();
    resizingRef.current = true;
    startXRef.current = e.clientX;
    startWidthRef.current = panelWidth;

    const handleResizeMove = (moveEvent) => {
      if (!resizingRef.current) return;
      const delta = startXRef.current - moveEvent.clientX;
      const newWidth = Math.max(320, Math.min(700, startWidthRef.current + delta));
      setPanelWidth(newWidth);
    };

    const handleResizeEnd = () => {
      resizingRef.current = false;
      document.removeEventListener('mousemove', handleResizeMove);
      document.removeEventListener('mouseup', handleResizeEnd);
    };

    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
  }, [panelWidth]);

  if (!card) return null;

  return (
    <div className="card-side-panel" style={{ width: panelWidth }}>
      <div
        className={`card-side-panel__resize-handle ${resizingRef.current ? 'card-side-panel__resize-handle--active' : ''}`}
        onMouseDown={handleResizeStart}
      />

      <div className="card-side-panel__header">
        <div className="card-side-panel__header-left">
          <span className="card-side-panel__type-badge">
            {(card.card_type || 'note').replace(/_/g, ' ')}
          </span>
        </div>
        <button
          className="card-side-panel__close-btn"
          onClick={onClose}
          aria-label="Close side panel"
        >
          &times;
        </button>
      </div>

      <div className="card-side-panel__tabs">
        {['content', 'properties', 'attachments', 'backlinks'].map(tab => (
          <button
            key={tab}
            className={`card-side-panel__tab ${activeTab === tab ? 'card-side-panel__tab--active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div className="card-side-panel__body">
        {activeTab === 'content' && (
          <ContentTab
            card={card}
            boardId={boardId}
            onCardUpdated={onCardUpdated}
            onExtractToCard={onExtractToCard}
          />
        )}
        {activeTab === 'properties' && (
          <PropertiesTab
            card={card}
            boardId={boardId}
            onCardUpdated={onCardUpdated}
          />
        )}
        {activeTab === 'attachments' && (
          <div className="card-side-panel__attachments-tab">
            <CardAttachments cardId={card.id} />
          </div>
        )}
        {activeTab === 'backlinks' && (
          <BacklinksTab
            cardId={card.id}
            edges={edges}
            nodes={nodes}
            onNavigateToCard={handleNavigateToCard}
          />
        )}
      </div>
    </div>
  );
}
