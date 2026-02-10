import { useState } from 'react';
import { useSnapshots, useCreateSnapshot, useRestoreSnapshot, useDeleteSnapshot } from '../../../api/queries/snapshotQueries.js';
import '../styles/VersionHistoryPanel.css';

function formatRelativeTime(timestamp) {
  const now = Date.now();
  const diff = now - new Date(timestamp).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function triggerBadge(trigger) {
  const map = {
    manual: 'Manual',
    auto: 'Auto',
    restore: 'Pre-restore',
  };
  return map[trigger] || trigger;
}

export default function VersionHistoryPanel({ boardId, onClose, onRestore }) {
  const [snapshotName, setSnapshotName] = useState('');
  const [confirmingRestore, setConfirmingRestore] = useState(null);

  const { data: snapshotsData, isLoading } = useSnapshots(boardId);
  const createMutation = useCreateSnapshot(boardId);
  const restoreMutation = useRestoreSnapshot(boardId);
  const deleteMutation = useDeleteSnapshot(boardId);

  const snapshots = snapshotsData?.snapshots || snapshotsData || [];

  const handleSave = () => {
    if (!snapshotName.trim()) return;
    createMutation.mutate({ name: snapshotName.trim(), trigger: 'manual' }, {
      onSuccess: () => setSnapshotName(''),
    });
  };

  const handleRestore = (snapshotId) => {
    restoreMutation.mutate(snapshotId, {
      onSuccess: (data) => {
        setConfirmingRestore(null);
        onRestore?.(data);
      },
    });
  };

  const handleDelete = (snapshotId) => {
    deleteMutation.mutate(snapshotId);
  };

  return (
    <div className="version-history-panel">
      <div className="version-history-panel__header">
        <h3 className="version-history-panel__title">Version History</h3>
        <button
          className="version-history-panel__close"
          onClick={onClose}
          aria-label="Close version history"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="version-history-panel__save">
        <input
          className="version-history-panel__input"
          type="text"
          placeholder="Version name..."
          value={snapshotName}
          onChange={(e) => setSnapshotName(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); }}
        />
        <button
          className="version-history-panel__save-btn"
          onClick={handleSave}
          disabled={!snapshotName.trim() || createMutation.isPending}
        >
          {createMutation.isPending ? 'Saving...' : 'Save'}
        </button>
      </div>

      <div className="version-history-panel__list">
        {isLoading && <p className="version-history-panel__empty">Loading...</p>}
        {!isLoading && snapshots.length === 0 && (
          <p className="version-history-panel__empty">No versions saved yet.</p>
        )}
        {snapshots.map((snap) => (
          <div key={snap.id} className="version-history-panel__item">
            <div className="version-history-panel__item-header">
              <span className="version-history-panel__item-name">
                {snap.name || 'Auto-save'}
              </span>
              <span className="version-history-panel__item-time">
                {formatRelativeTime(snap.created_at)}
              </span>
            </div>
            <div className="version-history-panel__item-meta">
              <span className={`version-history-panel__badge version-history-panel__badge--${snap.trigger || 'manual'}`}>
                {triggerBadge(snap.trigger)}
              </span>
              {snap.card_count != null && (
                <span className="version-history-panel__item-counts">
                  {snap.card_count} cards, {snap.edge_count || 0} edges
                </span>
              )}
            </div>
            <div className="version-history-panel__item-actions">
              {confirmingRestore === snap.id ? (
                <div className="version-history-panel__confirm">
                  <span className="version-history-panel__confirm-text">
                    Replace current board state?
                  </span>
                  <button
                    className="version-history-panel__confirm-btn version-history-panel__confirm-btn--yes"
                    onClick={() => handleRestore(snap.id)}
                    disabled={restoreMutation.isPending}
                  >
                    {restoreMutation.isPending ? 'Restoring...' : 'Yes, restore'}
                  </button>
                  <button
                    className="version-history-panel__confirm-btn version-history-panel__confirm-btn--no"
                    onClick={() => setConfirmingRestore(null)}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <>
                  <button
                    className="version-history-panel__action-btn"
                    onClick={() => setConfirmingRestore(snap.id)}
                    title="Restore this version"
                  >
                    Restore
                  </button>
                  <button
                    className="version-history-panel__action-btn version-history-panel__action-btn--danger"
                    onClick={() => handleDelete(snap.id)}
                    disabled={deleteMutation.isPending}
                    title="Delete this version"
                  >
                    Delete
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
