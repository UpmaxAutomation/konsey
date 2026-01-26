/**
 * Recent conversations section
 * Shows last 15 conversations sorted by last activity
 */

import React from 'react';

function formatTimeAgo(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export default function RecentsSection({
  conversations,
  currentId,
  isCollapsed,
  onToggle,
  onSelect,
  onStar,
  onDelete,
  isStarred,
}) {
  if (conversations.length === 0) return null;

  return (
    <div className="sidebar-section recents-section">
      <div
        className="section-header"
        onClick={onToggle}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onToggle()}
      >
        <div className="section-header-left">
          <svg
            className={`section-chevron ${isCollapsed ? 'collapsed' : ''}`}
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          <span className="section-title">Recents</span>
        </div>
        <span className="section-count">{conversations.length}</span>
      </div>

      {!isCollapsed && (
        <div className="section-items">
          {conversations.map(conv => (
            <div
              key={conv.id}
              className={`sidebar-item ${conv.id === currentId ? 'active' : ''}`}
              onClick={() => onSelect(conv.id)}
            >
              <span className="item-icon">💬</span>
              <div className="item-content">
                <span className="item-title" title={conv.title}>
                  {conv.title || 'New Conversation'}
                </span>
                <span className="item-meta">
                  {formatTimeAgo(conv.updated_at || conv.created_at)}
                </span>
              </div>
              <div className="item-actions">
                <button
                  className={`item-action star-btn ${isStarred(conv.id) ? 'starred' : ''}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onStar(conv.id);
                  }}
                  title={isStarred(conv.id) ? 'Unstar' : 'Star'}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill={isStarred(conv.id) ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                  </svg>
                </button>
                <button
                  className="item-action delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Delete this conversation?')) {
                      onDelete(conv.id);
                    }
                  }}
                  title="Delete"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18"></path>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
