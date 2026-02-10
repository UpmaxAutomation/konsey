import { useState, useEffect, useCallback, useRef } from 'react';
import { createInboxItem, listInboxItems, processInboxItem, deleteCard } from '../../../api/boards.js';
import '../styles/InboxPanel.css';

export default function InboxPanel({ boardId, onClose, onFocusCard }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [captureText, setCaptureText] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    if (!boardId) return;
    setLoading(true);
    listInboxItems(boardId)
      .then((data) => setItems(data.items || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [boardId]);

  const handleCapture = useCallback(async () => {
    if (!captureText.trim()) return;
    try {
      const item = await createInboxItem(boardId, { content: captureText.trim() });
      setItems((prev) => [item, ...prev]);
      setCaptureText('');
      inputRef.current?.focus();
    } catch (err) {
      console.error('Failed to create inbox item:', err);
    }
  }, [boardId, captureText]);

  const handleProcess = useCallback(async (cardId) => {
    try {
      await processInboxItem(boardId, cardId);
      setItems((prev) => prev.filter((i) => i.id !== cardId));
      onFocusCard?.(cardId);
    } catch (err) {
      console.error('Failed to process inbox item:', err);
    }
  }, [boardId, onFocusCard]);

  const handleArchive = useCallback(async (cardId) => {
    try {
      await deleteCard(boardId, cardId);
      setItems((prev) => prev.filter((i) => i.id !== cardId));
    } catch (err) {
      console.error('Failed to archive inbox item:', err);
    }
  }, [boardId]);

  return (
    <div className="inbox-panel">
      <div className="inbox-panel__header">
        <h3 className="inbox-panel__title">
          Inbox
          {items.length > 0 && <span className="inbox-panel__badge">{items.length}</span>}
        </h3>
        <button className="inbox-panel__close" onClick={onClose} aria-label="Close inbox">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="inbox-panel__capture">
        <textarea
          ref={inputRef}
          className="inbox-panel__capture-input"
          placeholder="Quick capture... (Cmd+Enter to save)"
          value={captureText}
          onChange={(e) => setCaptureText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              handleCapture();
            }
          }}
          rows={2}
        />
        <button
          className="inbox-panel__capture-btn"
          onClick={handleCapture}
          disabled={!captureText.trim()}
        >
          Capture
        </button>
      </div>

      <div className="inbox-panel__list">
        {loading && <div className="inbox-panel__loading">Loading...</div>}
        {!loading && items.length === 0 && (
          <div className="inbox-panel__empty">Inbox is empty. Use quick capture above.</div>
        )}
        {items.map((item) => (
          <div key={item.id} className="inbox-panel__item">
            <div className="inbox-panel__item-content">
              {item.content?.slice(0, 120) || 'Empty'}
            </div>
            <div className="inbox-panel__item-actions">
              <button
                className="inbox-panel__item-btn inbox-panel__item-btn--process"
                onClick={() => handleProcess(item.id)}
                title="Process (keep on board)"
              >
                Process
              </button>
              <button
                className="inbox-panel__item-btn inbox-panel__item-btn--archive"
                onClick={() => handleArchive(item.id)}
                title="Archive (delete)"
              >
                Archive
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
