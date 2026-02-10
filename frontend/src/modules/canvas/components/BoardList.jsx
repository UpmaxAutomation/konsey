import { useState, useEffect, useMemo } from 'react';
import { listBoards, createBoard, deleteBoard } from '../../../api/boards.js';
import '../styles/BoardList.css';

export default function BoardList({ projectId = null, onSelectBoard, onClose }) {
  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newBoardName, setNewBoardName] = useState('');
  const [error, setError] = useState(null);
  const [expandedParents, setExpandedParents] = useState(new Set());

  useEffect(() => {
    loadBoards();
  }, [projectId]);

  async function loadBoards() {
    try {
      setLoading(true);
      const data = await listBoards(projectId);
      setBoards(data.boards || []);
    } catch (err) {
      console.error('Failed to load boards:', err);
    } finally {
      setLoading(false);
    }
  }

  // Group boards into root and children
  const { rootBoards, childrenMap } = useMemo(() => {
    const roots = [];
    const map = new Map();
    boards.forEach((b) => {
      if (!b.parent_board_id) {
        roots.push(b);
      } else {
        if (!map.has(b.parent_board_id)) map.set(b.parent_board_id, []);
        map.get(b.parent_board_id).push(b);
      }
    });
    return { rootBoards: roots, childrenMap: map };
  }, [boards]);

  function toggleParent(boardId) {
    setExpandedParents((prev) => {
      const next = new Set(prev);
      if (next.has(boardId)) next.delete(boardId);
      else next.add(boardId);
      return next;
    });
  }

  async function handleCreate() {
    const name = newBoardName.trim() || 'Untitled Board';
    setError(null);
    try {
      const board = await createBoard({ name, project_id: projectId });
      setBoards((prev) => [board, ...prev]);
      setNewBoardName('');
      setCreating(false);
      onSelectBoard?.(board.id);
    } catch (err) {
      console.error('Failed to create board:', err);
      setError('Failed to create board. Please try again.');
    }
  }

  async function handleDelete(e, boardId) {
    e.stopPropagation();
    if (!confirm('Delete this board and all its cards?')) return;
    try {
      await deleteBoard(boardId);
      setBoards((prev) => prev.filter((b) => b.id !== boardId));
    } catch (err) {
      console.error('Failed to delete board:', err);
    }
  }

  return (
    <div className="board-list">
      <div className="board-list__header">
        <h2 className="board-list__title">
          {projectId ? 'Project Boards' : 'All Boards'}
        </h2>
        <div className="board-list__actions">
          {!creating && (
            <button className="board-list__create-btn" onClick={() => setCreating(true)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
              New Board
            </button>
          )}
          {onClose && (
            <button className="board-list__close-btn" onClick={onClose}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {creating && (
        <div className="board-list__create-form">
          <input
            className="board-list__create-input"
            value={newBoardName}
            onChange={(e) => setNewBoardName(e.target.value)}
            placeholder="Board name..."
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreate();
              if (e.key === 'Escape') setCreating(false);
            }}
            autoFocus
          />
          <button className="board-list__create-confirm" onClick={handleCreate}>Create</button>
          <button className="board-list__create-cancel" onClick={() => { setCreating(false); setError(null); }}>Cancel</button>
          {error && <div className="board-list__error">{error}</div>}
        </div>
      )}

      {loading ? (
        <div className="board-list__loading">Loading boards...</div>
      ) : boards.length === 0 ? (
        <div className="board-list__empty">
          <div className="board-list__empty-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.3">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <path d="M3 9h18M9 21V9" />
            </svg>
          </div>
          <p>No boards yet</p>
          <button className="board-list__create-btn" onClick={() => setCreating(true)}>
            Create your first board
          </button>
        </div>
      ) : (
        <div className="board-list__grid">
          {rootBoards.map((board) => {
            const children = childrenMap.get(board.id) || [];
            const hasChildren = children.length > 0;
            const isExpanded = expandedParents.has(board.id);

            return (
              <div key={board.id} className="board-list__group">
                <div
                  className="board-list__card"
                  onClick={() => onSelectBoard?.(board.id)}
                >
                  <div className="board-list__card-icon">
                    {board.icon ? (
                      <span className="board-list__card-emoji">{board.icon}</span>
                    ) : (
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2" />
                        <path d="M3 9h18M9 21V9" />
                      </svg>
                    )}
                  </div>
                  <div className="board-list__card-info">
                    <h3 className="board-list__card-name">
                      {board.name}
                      {hasChildren && (
                        <span className="board-list__child-count">{children.length}</span>
                      )}
                    </h3>
                    {board.description && (
                      <p className="board-list__card-desc">{board.description}</p>
                    )}
                    <span className="board-list__card-date">
                      {new Date(board.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                  {hasChildren && (
                    <button
                      className="board-list__expand-btn"
                      onClick={(e) => { e.stopPropagation(); toggleParent(board.id); }}
                      title={isExpanded ? 'Collapse' : 'Expand children'}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d={isExpanded ? 'M6 9l6 6 6-6' : 'M9 18l6-6-6-6'} />
                      </svg>
                    </button>
                  )}
                  <button
                    className="board-list__card-delete"
                    onClick={(e) => handleDelete(e, board.id)}
                    title="Delete board"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                    </svg>
                  </button>
                </div>

                {/* Child boards indented under parent */}
                {hasChildren && isExpanded && (
                  <div className="board-list__children">
                    {children.map((child) => (
                      <div
                        key={child.id}
                        className="board-list__card board-list__card--child"
                        onClick={() => onSelectBoard?.(child.id)}
                      >
                        <div className="board-list__card-icon">
                          {child.icon ? (
                            <span className="board-list__card-emoji">{child.icon}</span>
                          ) : (
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                              <rect x="3" y="3" width="18" height="18" rx="2" />
                              <path d="M3 9h18M9 21V9" />
                            </svg>
                          )}
                        </div>
                        <div className="board-list__card-info">
                          <h3 className="board-list__card-name">{child.name}</h3>
                          {child.description && (
                            <p className="board-list__card-desc">{child.description}</p>
                          )}
                          <span className="board-list__card-date">
                            {new Date(child.updated_at).toLocaleDateString()}
                          </span>
                        </div>
                        <button
                          className="board-list__card-delete"
                          onClick={(e) => handleDelete(e, child.id)}
                          title="Delete board"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
