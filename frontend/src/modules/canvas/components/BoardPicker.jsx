import { useState, useEffect, useRef } from 'react';
import { listBoards, createBoard } from '../../../api/boards.js';
import '../styles/BoardPicker.css';

export default function BoardPicker({ onSelect, onClose, projectId = null }) {
  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    loadBoards();
  }, []);

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        onClose?.();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  async function loadBoards() {
    try {
      const data = await listBoards(projectId);
      setBoards(data.boards || []);
    } catch (err) {
      console.error('Failed to load boards:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate() {
    const name = newName.trim() || 'Untitled Board';
    try {
      const board = await createBoard({ name, project_id: projectId });
      onSelect?.(board.id, board.name);
    } catch (err) {
      console.error('Failed to create board:', err);
    }
  }

  return (
    <div className="board-picker" ref={ref}>
      <div className="board-picker__header">
        <span className="board-picker__title">Add to board</span>
        <button className="board-picker__close" onClick={onClose}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {loading ? (
        <div className="board-picker__loading">Loading...</div>
      ) : (
        <div className="board-picker__list">
          {boards.map((board) => (
            <button
              key={board.id}
              className="board-picker__item"
              onClick={() => onSelect?.(board.id, board.name)}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M3 9h18M9 21V9" />
              </svg>
              <span>{board.name}</span>
            </button>
          ))}
        </div>
      )}

      <div className="board-picker__footer">
        {creating ? (
          <div className="board-picker__create-form">
            <input
              className="board-picker__input"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Board name..."
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreate();
                if (e.key === 'Escape') setCreating(false);
              }}
              autoFocus
            />
            <button className="board-picker__create-btn" onClick={handleCreate}>
              Create
            </button>
          </div>
        ) : (
          <button className="board-picker__new" onClick={() => setCreating(true)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12h14" />
            </svg>
            New board
          </button>
        )}
      </div>
    </div>
  );
}
