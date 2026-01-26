/**
 * User profile footer component
 * Shows user avatar, name, and settings dropdown
 */

import React, { useState } from 'react';

export default function UserProfile({
  user,
  onLogout,
  onOpenSettings,
  onOpenAPIKeys,
  onOpenTeam,
  theme,
  onToggleTheme,
}) {
  const [showMenu, setShowMenu] = useState(false);

  if (!user) return null;

  const initial = (user.name || user.email || 'U').charAt(0).toUpperCase();

  return (
    <div className="user-profile">
      <div
        className="user-profile-main"
        onClick={() => setShowMenu(!showMenu)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && setShowMenu(!showMenu)}
      >
        <div className="user-avatar">
          {user.avatar_url ? (
            <img src={user.avatar_url} alt={user.name || user.email} />
          ) : (
            <span className="avatar-initial">{initial}</span>
          )}
        </div>
        <div className="user-info">
          <div className="user-name">{user.name || 'User'}</div>
          <div className="user-plan">
            {user.is_admin ? 'Admin' : 'Pro'} Plan
          </div>
        </div>
        <svg
          className={`dropdown-chevron ${showMenu ? 'open' : ''}`}
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </div>

      {showMenu && (
        <>
          <div className="user-menu-backdrop" onClick={() => setShowMenu(false)} />
          <div className="user-menu">
            <button onClick={() => { onOpenSettings(); setShowMenu(false); }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
              Settings
            </button>
            <button onClick={() => { onOpenAPIKeys(); setShowMenu(false); }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"></path>
              </svg>
              API Keys
            </button>
            {user.is_admin && (
              <button onClick={() => { onOpenTeam(); setShowMenu(false); }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
                Team
              </button>
            )}
            <div className="menu-divider" />
            <button onClick={() => { onToggleTheme(); setShowMenu(false); }}>
              {theme === 'light' ? '🌙' : '☀️'}
              {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
            </button>
            <div className="menu-divider" />
            <button className="logout-btn" onClick={onLogout}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
              Sign Out
            </button>
          </div>
        </>
      )}
    </div>
  );
}
