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
  onToggleAssets,
  onToggleMarketplace,
  onToggleExport,
  onToggleIntegrations,
  onAddPipelineNode = () => {},
  hasPipelineNodes = false,
  onRunPipeline = () => {},
  pipelineRunning = false,
  onAutoLayout,
  onTidyUp,
  recentCards = [],
  onRecentSelect,
  onCollapseAll,
  onExpandAll,
}) {
  const [isEditingName, setIsEditingName] = useState(false);
  const [editName, setEditName] = useState('');
  const [showAIMenu, setShowAIMenu] = useState(false);
  const [showTemplateMenu, setShowTemplateMenu] = useState(false);
  const [showCreateMenu, setShowCreateMenu] = useState(false);
  const [showToolsMenu, setShowToolsMenu] = useState(false);
  const [showShareMenu, setShowShareMenu] = useState(false);
  const [showLayoutSub, setShowLayoutSub] = useState(false);
  const [showRecentMenu, setShowRecentMenu] = useState(false);
  const aiMenuRef = useRef(null);
  const templateMenuRef = useRef(null);
  const createMenuRef = useRef(null);
  const toolsMenuRef = useRef(null);
  const shareMenuRef = useRef(null);
  const recentMenuRef = useRef(null);

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

  // Close create menu on outside click
  useEffect(() => {
    if (!showCreateMenu) return;
    function handleClick(e) {
      if (createMenuRef.current && !createMenuRef.current.contains(e.target)) {
        setShowCreateMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showCreateMenu]);

  // Close tools menu on outside click
  useEffect(() => {
    if (!showToolsMenu) return;
    function handleClick(e) {
      if (toolsMenuRef.current && !toolsMenuRef.current.contains(e.target)) {
        setShowToolsMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showToolsMenu]);

  // Close share menu on outside click
  useEffect(() => {
    if (!showShareMenu) return;
    function handleClick(e) {
      if (shareMenuRef.current && !shareMenuRef.current.contains(e.target)) {
        setShowShareMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showShareMenu]);

  // Close recent menu on outside click
  useEffect(() => {
    if (!showRecentMenu) return;
    function handleClick(e) {
      if (recentMenuRef.current && !recentMenuRef.current.contains(e.target)) {
        setShowRecentMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showRecentMenu]);

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
        {/* CREATE group */}
        <div className="board-toolbar__group" ref={createMenuRef}>
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
              <span>Note</span>
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
            <span>Link</span>
          </button>
          <button
            className="board-toolbar__group-trigger"
            onClick={() => setShowCreateMenu(!showCreateMenu)}
            title="More create options"
            aria-label="More create options"
            aria-expanded={showCreateMenu}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          {showCreateMenu && (
            <div className="board-toolbar__dropdown-menu" role="menu">
              <button
                className="board-toolbar__dropdown-item"
                role="menuitem"
                onClick={() => { setShowCreateMenu(false); onAddCard?.('knowledge'); }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
                Knowledge
              </button>
              <button
                className="board-toolbar__dropdown-item"
                role="menuitem"
                onClick={() => { setShowCreateMenu(false); onAddSection?.(); }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M3 9h18" />
                </svg>
                Section
              </button>
              <button
                className="board-toolbar__dropdown-item"
                role="menuitem"
                onClick={() => { setShowCreateMenu(false); onAddSubBoard?.(); }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                  <path d="M12 11v6M9 14h6" />
                </svg>
                Sub-board
              </button>
              <div className="board-toolbar__dropdown-divider" />
              <div className="board-toolbar__dropdown-heading">Pipeline</div>
              <button
                className="board-toolbar__dropdown-item"
                role="menuitem"
                onClick={() => { setShowCreateMenu(false); onAddPipelineNode('pl_input'); }}
              >
                <span className="board-toolbar__pipeline-dot" style={{ '--dot-color': '#10b981' }} />
                Input
              </button>
              <button
                className="board-toolbar__dropdown-item"
                role="menuitem"
                onClick={() => { setShowCreateMenu(false); onAddPipelineNode('pl_llm'); }}
              >
                <span className="board-toolbar__pipeline-dot" style={{ '--dot-color': '#3b82f6' }} />
                LLM
              </button>
              <button
                className="board-toolbar__dropdown-item"
                role="menuitem"
                onClick={() => { setShowCreateMenu(false); onAddPipelineNode('pl_council'); }}
              >
                <span className="board-toolbar__pipeline-dot" style={{ '--dot-color': '#8b5cf6' }} />
                Council
              </button>
              <button
                className="board-toolbar__dropdown-item"
                role="menuitem"
                onClick={() => { setShowCreateMenu(false); onAddPipelineNode('pl_transform'); }}
              >
                <span className="board-toolbar__pipeline-dot" style={{ '--dot-color': '#f59e0b' }} />
                Transform
              </button>
              <button
                className="board-toolbar__dropdown-item"
                role="menuitem"
                onClick={() => { setShowCreateMenu(false); onAddPipelineNode('pl_conditional'); }}
              >
                <span className="board-toolbar__pipeline-dot" style={{ '--dot-color': '#eab308' }} />
                Conditional
              </button>
              <button
                className="board-toolbar__dropdown-item"
                role="menuitem"
                onClick={() => { setShowCreateMenu(false); onAddPipelineNode('pl_output'); }}
              >
                <span className="board-toolbar__pipeline-dot" style={{ '--dot-color': '#64748b' }} />
                Output
              </button>
            </div>
          )}
        </div>

        {hasPipelineNodes && (
          <>
            <div className="board-toolbar__divider" />
            <button
              className="board-toolbar__btn board-toolbar__btn--pipeline-run"
              onClick={onRunPipeline}
              disabled={pipelineRunning}
              title="Run pipeline"
              aria-label="Run pipeline"
            >
              {pipelineRunning ? (
                <svg className="board-toolbar__spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              )}
              <span>Run</span>
            </button>
          </>
        )}

        <div className="board-toolbar__divider" />

        {/* AI group */}
        <div className="board-toolbar__group" ref={aiMenuRef}>
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
            <span>Council</span>
            {selectedCount > 0 && <span className="board-toolbar__badge">{selectedCount}</span>}
          </button>
          <button
            className="board-toolbar__btn board-toolbar__btn--ai board-toolbar__group-trigger"
            onClick={() => setShowAIMenu(!showAIMenu)}
            disabled={boardProcessing}
            title="AI actions on board"
            aria-label="AI actions on board"
            aria-expanded={showAIMenu}
          >
            {boardProcessing ? (
              <svg className="board-toolbar__spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
            ) : (
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 9l6 6 6-6" />
              </svg>
            )}
          </button>
          {showAIMenu && (
            <div className="board-toolbar__dropdown-menu" role="menu">
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => handleAIAction('summarize_board')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
                Summarize {selectedCount > 0 ? 'Selected' : 'Board'}
              </button>
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => handleAIAction('cluster_themes')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="6" cy="6" r="3" />
                  <circle cx="18" cy="6" r="3" />
                  <circle cx="12" cy="18" r="3" />
                  <line x1="6" y1="9" x2="12" y2="15" />
                  <line x1="18" y1="9" x2="12" y2="15" />
                </svg>
                Cluster by Theme
              </button>
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => handleAIAction('find_connections')}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                  <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                </svg>
                Find Connections
              </button>
              <div className="board-toolbar__dropdown-divider" />
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowAIMenu(false); onToggleWorkflows?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
                Workflows
              </button>
              <button
                className={`board-toolbar__dropdown-item${agentRunning ? ' board-toolbar__dropdown-item--active' : ''}`}
                role="menuitem"
                onClick={() => { setShowAIMenu(false); onToggleAgent?.(); }}
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
            </div>
          )}
        </div>

        <div className="board-toolbar__divider" />

        {/* TOOLS group */}
        <div className="board-toolbar__group" ref={toolsMenuRef}>
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
          <div className="board-toolbar__dropdown" ref={recentMenuRef}>
            <button
              className="board-toolbar__btn"
              onClick={() => setShowRecentMenu(!showRecentMenu)}
              title="Recent cards"
              aria-label="Recent cards"
              aria-expanded={showRecentMenu}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </button>
            {showRecentMenu && (
              <div className="board-toolbar__dropdown-menu board-toolbar__recent-menu" role="menu">
                {recentCards.length === 0 ? (
                  <div className="board-toolbar__dropdown-empty">No recent cards</div>
                ) : (
                  recentCards.map((rc) => (
                    <button
                      key={rc.id}
                      className="board-toolbar__dropdown-item"
                      role="menuitem"
                      onClick={() => {
                        setShowRecentMenu(false);
                        onRecentSelect?.(rc.id);
                      }}
                    >
                      <span className="board-toolbar__recent-type">{rc.card_type || 'note'}</span>
                      <span className="board-toolbar__recent-title">{rc.title || 'Untitled'}</span>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
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
          <button
            className="board-toolbar__group-trigger"
            onClick={() => setShowToolsMenu(!showToolsMenu)}
            title="More tools"
            aria-label="More tools"
            aria-expanded={showToolsMenu}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          {showToolsMenu && (
            <div className="board-toolbar__dropdown-menu" role="menu">
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowToolsMenu(false); onToggleJournal?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 19.5A2.5 2.5 0 016.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" />
                </svg>
                Journal
              </button>
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowToolsMenu(false); onToggleInbox?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
                  <path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z" />
                </svg>
                Inbox
              </button>
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowToolsMenu(false); onToggleMemory?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z" />
                  <path d="M12 12V8M12 16h.01" />
                </svg>
                Memory
                {memoryCount > 0 && <span className="board-toolbar__badge">{memoryCount}</span>}
              </button>
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowToolsMenu(false); onToggleHistory?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
                History
              </button>
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowToolsMenu(false); onToggleAssets?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
                Assets
              </button>
              <div className="board-toolbar__dropdown-divider" />
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowToolsMenu(false); onCollapseAll?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 12h16M4 6h16M4 18h16" />
                  <path d="M15 9l-3-3-3 3M15 15l-3 3-3-3" />
                </svg>
                Collapse All
              </button>
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowToolsMenu(false); onExpandAll?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 12h16M4 6h16M4 18h16" />
                  <path d="M15 3l-3 3-3-3M15 21l-3-3-3 3" />
                </svg>
                Expand All
              </button>
              <div className="board-toolbar__dropdown-divider" />
              <div
                className="board-toolbar__dropdown-item board-toolbar__dropdown-item--submenu"
                onMouseEnter={() => setShowLayoutSub(true)}
                onMouseLeave={() => setShowLayoutSub(false)}
                role="menuitem"
                aria-haspopup="true"
                aria-expanded={showLayoutSub}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="2" width="6" height="6" rx="1" />
                  <rect x="16" y="2" width="6" height="6" rx="1" />
                  <rect x="9" y="16" width="6" height="6" rx="1" />
                  <path d="M5 8v2a2 2 0 002 2h10a2 2 0 002-2V8" />
                  <path d="M12 12v4" />
                </svg>
                <span>Auto Layout</span>
                <span className="board-toolbar__submenu-arrow" aria-hidden="true">&rsaquo;</span>
                {showLayoutSub && (
                  <div className="board-toolbar__submenu" role="menu">
                    <button
                      className="board-toolbar__dropdown-item"
                      role="menuitem"
                      onClick={() => { onAutoLayout?.('TB'); setShowToolsMenu(false); setShowLayoutSub(false); }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 5v14M5 12l7 7 7-7" />
                      </svg>
                      Top-Down
                    </button>
                    <button
                      className="board-toolbar__dropdown-item"
                      role="menuitem"
                      onClick={() => { onAutoLayout?.('LR'); setShowToolsMenu(false); setShowLayoutSub(false); }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M5 12h14M12 5l7 7-7 7" />
                      </svg>
                      Left-Right
                    </button>
                    <button
                      className="board-toolbar__dropdown-item"
                      role="menuitem"
                      onClick={() => { onAutoLayout?.('BT'); setShowToolsMenu(false); setShowLayoutSub(false); }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 19V5M5 12l7-7 7 7" />
                      </svg>
                      Bottom-Up
                    </button>
                    <button
                      className="board-toolbar__dropdown-item"
                      role="menuitem"
                      onClick={() => { onAutoLayout?.('RL'); setShowToolsMenu(false); setShowLayoutSub(false); }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M19 12H5M12 5l-7 7 7 7" />
                      </svg>
                      Right-Left
                    </button>
                  </div>
                )}
              </div>
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowToolsMenu(false); onTidyUp?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="7" height="7" rx="1" />
                  <rect x="14" y="3" width="7" height="7" rx="1" />
                  <rect x="3" y="14" width="7" height="7" rx="1" />
                  <rect x="14" y="14" width="7" height="7" rx="1" />
                </svg>
                Tidy Up
              </button>
            </div>
          )}
        </div>

        <div className="board-toolbar__divider" />

        {/* SHARE group */}
        <div className="board-toolbar__group" ref={shareMenuRef}>
          <button
            className="board-toolbar__btn"
            onClick={onToggleExport}
            title="Export board"
            aria-label="Export board"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            <span>Export</span>
          </button>
          <button
            className="board-toolbar__group-trigger"
            onClick={() => setShowShareMenu(!showShareMenu)}
            title="More sharing options"
            aria-label="More sharing options"
            aria-expanded={showShareMenu}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          {showShareMenu && (
            <div className="board-toolbar__dropdown-menu" role="menu">
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowShareMenu(false); onToggleMarketplace?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M6 2L3 7v13a2 2 0 002 2h14a2 2 0 002-2V7l-3-5z" />
                  <line x1="3" y1="7" x2="21" y2="7" />
                  <path d="M16 11a4 4 0 01-8 0" />
                </svg>
                Marketplace
              </button>
              <button className="board-toolbar__dropdown-item" role="menuitem" onClick={() => { setShowShareMenu(false); onToggleIntegrations?.(); }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M15 7h3a5 5 0 010 10h-3M9 17H6a5 5 0 010-10h3" />
                  <line x1="8" y1="12" x2="16" y2="12" />
                </svg>
                Integrations
              </button>
            </div>
          )}
        </div>
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
        <button
          className={`board-toolbar__view-btn${activeView === 'timeline' ? ' board-toolbar__view-btn--active' : ''}`}
          onClick={() => onViewChange?.('timeline')}
          title="Timeline view"
          aria-label="Timeline view"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="4" width="14" height="4" rx="1" />
            <rect x="5" y="10" width="16" height="4" rx="1" />
            <rect x="7" y="16" width="10" height="4" rx="1" />
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
