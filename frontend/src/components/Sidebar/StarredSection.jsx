/**
 * Starred conversations section
 * Displays user's starred/favorite conversations
 */

import React from 'react';

export default function StarredSection({
  conversations,
  currentId,
  isCollapsed,
  onToggle,
  onSelect,
  onUnstar,
}) {
  if (conversations.length === 0) return null;

  return (
    <div className="sidebar-section starred-section">
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
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
          </svg>
          <span className="section-title">Starred</span>
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
              <span className="item-icon">★</span>
              <span className="item-title" title={conv.title}>
                {conv.title || 'New Conversation'}
              </span>
              <button
                className="item-action unstar-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onUnstar(conv.id);
                }}
                title="Unstar"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
