import { useState, useEffect, useMemo, useCallback } from 'react';
import { listBoards, createBoard, createChildBoard, deleteBoard } from '../../api/boards.js';
import './styles/BoardTree.css';

function TreeNode({ board, childrenMap, level, onSelect, onAddChild, onDelete, activeBoardId }) {
  const [expanded, setExpanded] = useState(level < 1);
  const [showActions, setShowActions] = useState(false);
  const children = childrenMap.get(board.id) || [];
  const hasChildren = children.length > 0;
  const isActive = board.id === activeBoardId;

  return (
    <div className="board-tree__node">
      <div
        className={`board-tree__item ${isActive ? 'board-tree__item--active' : ''}`}
        style={{ paddingLeft: `${12 + level * 16}px` }}
        onClick={() => onSelect(board.id)}
        onMouseEnter={() => setShowActions(true)}
        onMouseLeave={() => setShowActions(false)}
      >
        {/* Expand/collapse chevron */}
        {hasChildren ? (
          <button
            className="board-tree__chevron"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d={expanded ? 'M6 9l6 6 6-6' : 'M9 18l6-6-6-6'} />
            </svg>
          </button>
        ) : (
          <span className="board-tree__spacer" />
        )}

        {/* Board icon */}
        <span className="board-tree__icon">{board.icon || (hasChildren ? '\uD83D\uDCC2' : '\uD83D\uDCCB')}</span>

        {/* Board name */}
        <span className="board-tree__name">{board.name}</span>

        {/* Child count */}
        {hasChildren && (
          <span className="board-tree__count">{children.length}</span>
        )}

        {/* Hover actions */}
        {showActions && (
          <div className="board-tree__actions">
            <button
              className="board-tree__action-btn"
              onClick={(e) => { e.stopPropagation(); onAddChild(board.id); }}
              title="Add sub-board"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </button>
            <button
              className="board-tree__action-btn board-tree__action-btn--danger"
              onClick={(e) => { e.stopPropagation(); onDelete(board.id, board.name); }}
              title="Delete board"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Children */}
      {expanded && hasChildren && (
        <div className="board-tree__children">
          {children.map((child) => (
            <TreeNode
              key={child.id}
              board={child}
              childrenMap={childrenMap}
              level={level + 1}
              onSelect={onSelect}
              onAddChild={onAddChild}
              onDelete={onDelete}
              activeBoardId={activeBoardId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function BoardTree({ onSelectBoard, activeBoardId }) {
  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false); // true = root, or parentId string for sub-board
  const [newName, setNewName] = useState('');

  const loadBoards = useCallback(() => {
    setLoading(true);
    listBoards()
      .then((data) => setBoards(data.boards || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadBoards(); }, [loadBoards]);

  // Build tree from flat list
  const { roots, childrenMap } = useMemo(() => {
    const map = new Map();
    const rootBoards = [];
    boards.forEach((b) => {
      const parentId = b.parent_board_id;
      if (!parentId) {
        rootBoards.push(b);
      } else {
        if (!map.has(parentId)) map.set(parentId, []);
        map.get(parentId).push(b);
      }
    });
    return { roots: rootBoards, childrenMap: map };
  }, [boards]);

  // Create board (root or child)
  const handleCreate = async () => {
    const name = newName.trim() || 'Untitled Board';
    try {
      if (typeof creating === 'string') {
        // creating is the parent board id
        await createChildBoard(creating, { name });
      } else {
        await createBoard({ name });
      }
      setNewName('');
      setCreating(false);
      loadBoards();
    } catch (err) {
      console.error('Failed to create board:', err);
    }
  };

  const handleAddChild = (parentId) => {
    setCreating(parentId);
    setNewName('');
  };

  const handleDelete = async (boardId, boardName) => {
    if (!confirm(`Delete "${boardName}" and all its cards?`)) return;
    try {
      await deleteBoard(boardId);
      setBoards((prev) => prev.filter((b) => b.id !== boardId && b.parent_board_id !== boardId));
    } catch (err) {
      console.error('Failed to delete board:', err);
    }
  };

  return (
    <div className="board-tree">
      {/* Header */}
      <div className="board-tree__header">
        <span className="board-tree__header-title">Boards</span>
        <button
          className="board-tree__new-btn"
          onClick={() => { setCreating(true); setNewName(''); }}
          title="New board"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </div>

      {/* Inline create form */}
      {creating !== false && (
        <div className="board-tree__create">
          <input
            className="board-tree__create-input"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder={typeof creating === 'string' ? 'Sub-board name...' : 'Board name...'}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreate();
              if (e.key === 'Escape') setCreating(false);
            }}
            autoFocus
          />
          <button className="board-tree__create-ok" onClick={handleCreate}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </button>
          <button className="board-tree__create-cancel" onClick={() => setCreating(false)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && <div className="board-tree__loading">Loading boards...</div>}

      {/* Empty state */}
      {!loading && roots.length === 0 && creating === false && (
        <div className="board-tree__empty">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.3">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M9 21V9" />
          </svg>
          <p>No boards yet</p>
          <button className="board-tree__empty-btn" onClick={() => { setCreating(true); setNewName(''); }}>
            Create your first board
          </button>
        </div>
      )}

      {/* Tree */}
      {!loading && roots.length > 0 && (
        <div className="board-tree__list">
          {roots.map((board) => (
            <TreeNode
              key={board.id}
              board={board}
              childrenMap={childrenMap}
              level={0}
              onSelect={onSelectBoard}
              onAddChild={handleAddChild}
              onDelete={handleDelete}
              activeBoardId={activeBoardId}
            />
          ))}
        </div>
      )}

      {/* Footer link to full boards page */}
      {!loading && roots.length > 0 && (
        <button className="board-tree__view-all" onClick={() => onSelectBoard(null)}>
          View all boards
        </button>
      )}
    </div>
  );
}
