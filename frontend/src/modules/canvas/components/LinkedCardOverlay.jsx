import { useCallback } from 'react';
import '../styles/LinkedCardOverlay.css';

/**
 * Overlay badge rendered on linked cards (card_type === 'linked_card').
 * Shows a chain-link icon and the source board name, positioned
 * at the top-right corner of the card.
 *
 * @param {Object} props
 * @param {string} props.sourceCardId - The ID of the original source card
 * @param {string} [props.sourceBoardName] - Display name of the board the card is linked from
 * @param {function} [props.onSync] - Callback to sync linked card with source
 * @param {boolean} [props.isSyncing] - Whether a sync operation is in progress
 */
export default function LinkedCardOverlay({ sourceCardId, sourceBoardName, onSync, isSyncing }) {
  const handleSyncClick = useCallback(
    (e) => {
      e.stopPropagation();
      e.preventDefault();
      if (onSync && !isSyncing) {
        onSync(sourceCardId);
      }
    },
    [onSync, isSyncing, sourceCardId]
  );

  return (
    <div className="linked-card-overlay" role="status" aria-label="Linked card">
      <span
        className="linked-card-overlay__badge"
        title={`Linked from ${sourceBoardName || 'another board'}`}
        aria-hidden="true"
      >
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
        </svg>
      </span>
      {sourceBoardName && (
        <span className="linked-card-overlay__source" title={sourceBoardName}>
          {sourceBoardName}
        </span>
      )}
      {onSync && (
        <button
          className="linked-card-overlay__sync nodrag"
          onClick={handleSyncClick}
          disabled={isSyncing}
          title="Sync with source card"
          aria-label="Sync linked card with source"
        >
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={isSyncing ? 'linked-card-overlay__sync-icon--spinning' : ''}
            aria-hidden="true"
          >
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
        </button>
      )}
    </div>
  );
}
