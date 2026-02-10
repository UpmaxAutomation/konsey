import { useState, useRef, useEffect } from 'react';
import { CARD_TEMPLATES } from '../editor/CardTemplates';
import '../styles/BoardToolbar.css';

export default function BoardToolbar({
  board,
  onAddCard,
  onAddSection,
  onAddSubBoard,
  onBack,
  onRenameBoard,
  selectedCount = 0,
  onRunCouncil,
  onDeleteSelected,
  onToggleSearch,
  onBoardAIAction,
  boardProcessing,
  onToggleMemory,
  memoryCount = 0,
  onToggleJournal,
  onToggleInbox,
  onToggleWorkflows,
  onToggleAgent,
  agentRunning = false,
  activeView = 'canvas',
  onViewChange,
  canUndo = false,
  canRedo = false,
  onUndo,
  onRedo,
  onToggleHistory,
  boardUsers = [],
}) {
  const [isEditingName, setIsEditingName] = useState(false);
  const [editName, setEditName] = useState('');
  const [showAIMenu, setShowAIMenu] = useState(false);
  const [showTemplateMenu, setShowTemplateMenu] = useState(false);
  const aiMenuRef = useRef(null);
  const templateMenuRef = useRef(null);

  const handleStartRename = () => {
    setEditName(board?.name || '');
    setIsEditingName(true);
  };

  const handleSaveRename = () => {
    if (editName.trim() && onRenameBoard) {
      onRenameBoard(editName.trim());
    }
    setIsEditingName(false);
  };

  // Close AI menu on outside click
  useEffect(() => {
    if (!showAIMenu) return;
    function handleClick(e) {
      if (aiMenuRef.current && !aiMenuRef.current.contains(e.target)) {
        setShowAIMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showAIMenu]);

  // Close template menu on outside click
  useEffect(() => {
    if (!showTemplateMenu) return;
    function handleClick(e) {
      if (templateMenuRef.current && !templateMenuRef.current.contains(e.target)) {
        setShowTemplateMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showTemplateMenu]);

  const handleAIAction = (action) => {
    setShowAIMenu(false);
    onBoardAIAction?.(action);
  };

  return (
    <div className="board-toolbar">
      <div className="board-toolbar__left">
        <button className="board-toolbar__back" onClick={onBack} title="Back to boards" aria-label="Back to boards">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>

        {isEditingName ? (
          <input
            className="board-toolbar__name-input"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            onBlur={handleSaveRename}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSaveRename();
              if (e.key === 'Escape') setIsEditingName(false);
            }}
            autoFocus
          />
        ) : (
          <h2 className="board-toolbar__name" onClick={handleStartRename}>
            {board?.name || 'Board'}
          </h2>
        )}
      </div>

      <div className="board-toolbar__center">
        <button
          className="board-toolbar__btn"
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo (Cmd+Z)"
          aria-label="Undo"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 10h10a5 5 0 0 1 0 10H9" />
            <path d="M3 10l4-4M3 10l4 4" />
          </svg>
        </button>
        <button
          className="board-toolbar__btn"
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo (Cmd+Shift+Z)"
          aria-label="Redo"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 10H11a5 5 0 0 0 0 10h4" />
            <path d="M21 10l-4-4M21 10l-4 4" />
          </svg>
        </button>

        <div className="board-toolbar__divider" />

        <div className="board-toolbar__dropdown" ref={templateMenuRef}>
          <button
            className="board-toolbar__btn"
            onClick={() => onAddCard?.('note')}
            title="Add note (N)"
            aria-label="Add note"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12h14" />
            </svg>
            Note
          </button>
          <button
            className="board-toolbar__btn board-toolbar__btn--dropdown-arrow"
            onClick={() => setShowTemplateMenu(!showTemplateMenu)}
            title="Card templates (T)"
            aria-label="Card templates"
            aria-expanded={showTemplateMenu}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          {showTemplateMenu && (
            <div className="board-toolbar__dropdown-menu" role="menu">
              {CARD_TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  className="board-toolbar__dropdown-item"
                  role="menuitem"
                  onClick={() => {
                    setShowTemplateMenu(false);
                    onAddCard?.('note', t);
                  }}
                >
                  <span>{t.icon}</span> {t.name}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          className="board-toolbar__btn"
          onClick={() => onAddCard?.('link')}
          title="Add link"
          aria-label="Add link"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
          Link
        </button>
        <button
          className="board-toolbar__btn"
          onClick={() => onAddCard?.('knowledge')}
          title="Add knowledge card (K)"
          aria-label="Add knowledge card"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
          </svg>
          Knowledge
        </button>
        <button
          className="board-toolbar__btn"
          onClick={onAddSection}
          title="Add section (Cmd+G)"
          aria-label="Add section"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18" />
          </svg>
          Section
        </button>
        <button
          className="board-toolbar__btn"
          onClick={onAddSubBoard}
          title="Create sub-board (Cmd+Shift+B)"
          aria-label="Create sub-board"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            <path d="M12 11v6M9 14h6" />
          </svg>
          Sub-board
        </button>

        <div className="board-toolbar__divider" />

        <button
          className="board-toolbar__btn board-toolbar__btn--council"
          onClick={onRunCouncil}
          disabled={!onRunCouncil}
          title={selectedCount > 0 ? `Run council with ${selectedCount} cards as context` : 'Select cards to use as council context'}
          aria-label={selectedCount > 0 ? `Run council with ${selectedCount} cards as context` : 'Run council'}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4M12 8h.01" />
          </svg>
          Council
          {selectedCount > 0 && <span className="board-toolbar__badge">{selectedCount}</span>}
        </button>

        <div className="board-toolbar__divider" />

        {/* AI Actions dropdown */}
        <div className="board-toolbar__dropdown" ref={aiMenuRef}>
          <button
            className="board-toolbar__btn board-toolbar__btn--ai"
            onClick={() => setShowAIMenu(!showAIMenu)}
            disabled={boardProcessing}
            title="AI actions on board"
            aria-label="AI actions on board"
            aria-expanded={showAIMenu}
          >
            {boardProcessing ? (
              <svg className="board-toolbar__spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5M2 12l10 5 10-5" />
              </svg>
            )}
            AI
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          {showAIMenu && (
            <div className="board-toolbar__dropdown-menu">
              <button className="board-toolbar__dropdown-item" onClick={() => handleAIAction('summarize_board')}>
                <span>📋</span> Summarize {selectedCount > 0 ? 'Selected' : 'Board'}
              </button>
              <button className="board-toolbar__dropdown-item" onClick={() => handleAIAction('cluster_themes')}>
                <span>🎨</span> Cluster by Theme
              </button>
              <button className="board-toolbar__dropdown-item" onClick={() => handleAIAction('find_connections')}>
                <span>🔗</span> Find Connections
              </button>
            </div>
          )}
        </div>

        <button
          className="board-toolbar__btn"
          onClick={onToggleSearch}
          title="Search cards (Cmd+F)"
          aria-label="Search cards"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </button>

        <button
          className="board-toolbar__btn"
          onClick={onToggleMemory}
          title="Board memory"
          aria-label="Board memory"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z" />
            <path d="M12 12V8M12 16h.01" />
          </svg>
          Memory
          {memoryCount > 0 && <span className="board-toolbar__badge">{memoryCount}</span>}
        </button>

        <button
          className="board-toolbar__btn"
          onClick={onToggleJournal}
          title="Journal (Cmd+J)"
          aria-label="Journal"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
          </svg>
          Journal
        </button>

        <button
          className="board-toolbar__btn"
          onClick={onToggleInbox}
          title="Inbox"
          aria-label="Inbox"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
            <path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z" />
          </svg>
          Inbox
        </button>

        <div className="board-toolbar__divider" />

        <button
          className="board-toolbar__btn"
          onClick={onToggleWorkflows}
          title="Workflows"
          aria-label="Workflows"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
          Workflows
        </button>

        <button
          className={`board-toolbar__btn${agentRunning ? ' board-toolbar__btn--active' : ''}`}
          onClick={onToggleAgent}
          title="AI Agent"
          aria-label="AI Agent"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="10" rx="2" />
            <circle cx="9" cy="16" r="1" />
            <circle cx="15" cy="16" r="1" />
            <path d="M8 11V7a4 4 0 018 0v4" />
          </svg>
          Agent
          {agentRunning && <span className="board-toolbar__badge board-toolbar__badge--pulse">...</span>}
        </button>

        <div className="board-toolbar__divider" />

        <button
          className="board-toolbar__btn"
          onClick={onToggleHistory}
          title="Version history"
          aria-label="Version history"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          History
        </button>
      </div>

      <div className="board-toolbar__view-toggle">
          <button
            className={`board-toolbar__view-btn${activeView === 'canvas' ? ' board-toolbar__view-btn--active' : ''}`}
            onClick={() => onViewChange?.('canvas')}
            title="Canvas view"
            aria-label="Canvas view"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
            </svg>
          </button>
          <button
            className={`board-toolbar__view-btn${activeView === 'table' ? ' board-toolbar__view-btn--active' : ''}`}
            onClick={() => onViewChange?.('table')}
            title="Table view"
            aria-label="Table view"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 3h18v18H3zM3 9h18M3 15h18M9 3v18M15 3v18" />
            </svg>
          </button>
          <button
            className={`board-toolbar__view-btn${activeView === 'kanban' ? ' board-toolbar__view-btn--active' : ''}`}
            onClick={() => onViewChange?.('kanban')}
            title="Kanban view"
            aria-label="Kanban view"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="5" height="18" rx="1" />
              <rect x="10" y="3" width="5" height="12" rx="1" />
              <rect x="17" y="3" width="5" height="15" rx="1" />
            </svg>
          </button>
        </div>

      <div className="board-toolbar__right">
        {boardUsers.length > 0 && (
          <div className="board-toolbar__presence">
            {boardUsers.slice(0, 4).map((user) => (
              <div
                key={user.user_id}
                className="board-toolbar__avatar"
                style={{ backgroundColor: user.color || '#4a90e2' }}
                title={user.name || 'User'}
              >
                {(user.name || 'U')[0].toUpperCase()}
              </div>
            ))}
            {boardUsers.length > 4 && (
              <div className="board-toolbar__avatar board-toolbar__avatar--more">
                +{boardUsers.length - 4}
              </div>
            )}
          </div>
        )}
        {selectedCount > 0 && (
          <>
            <span className="board-toolbar__selection">{selectedCount} selected</span>
            <button
              className="board-toolbar__btn board-toolbar__btn--danger"
              onClick={onDeleteSelected}
              title="Delete selected"
              aria-label="Delete selected cards"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2" />
              </svg>
            </button>
          </>
        )}
      </div>
    </div>
  );
}
