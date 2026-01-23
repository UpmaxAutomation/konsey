import { useState, useEffect, useCallback, useRef } from 'react';
import './Sidebar.css';
import Settings from './Settings';
import Analytics from './Analytics';
import Projects from './Projects';
import BatchProcessor from './BatchProcessor';
import SearchModal from './SearchModal';
import AdminPanel from './AdminPanel';
import { api } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001') + '/api';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onConversationsChange,
  isMobileOpen,
  onToggleMobile,
  isCreatingConversation = false,
}) {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'light';
  });
  const [showSettings, setShowSettings] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showProjects, setShowProjects] = useState(false);
  const [showBatch, setShowBatch] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showAdminPanel, setShowAdminPanel] = useState(false);
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const [currentProjectId, setCurrentProjectId] = useState(null);

  // Folder and tag state
  const [folders, setFolders] = useState([]);
  const [collapsedFolders, setCollapsedFolders] = useState({});
  const [allTags, setAllTags] = useState([]);
  const [selectedTags, setSelectedTags] = useState([]);
  const [draggedConversation, setDraggedConversation] = useState(null);
  const [editingTags, setEditingTags] = useState(null);
  const [tagInput, setTagInput] = useState('');
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const importFileRef = useRef(null);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Handle file import
  const handleImportClick = () => {
    importFileRef.current?.click();
  };

  const handleImportFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsImporting(true);
    try {
      const text = await file.text();
      const data = JSON.parse(text);

      // Validate the imported data has messages
      if (!data.messages || !Array.isArray(data.messages)) {
        throw new Error('Invalid conversation file: missing messages array');
      }

      // Import the conversation
      const imported = await api.importConversation({
        title: data.title,
        messages: data.messages,
        created_at: data.created_at,
        folder_id: data.folder_id,
        tags: data.tags,
      });

      // Refresh conversations list and select the imported one
      if (onConversationsChange) {
        await onConversationsChange();
      }
      onSelectConversation(imported.id);

      alert(`Imported "${imported.title}" with ${data.messages.length} messages`);
    } catch (error) {
      console.error('Failed to import conversation:', error);
      alert(`Failed to import: ${error.message}`);
    } finally {
      setIsImporting(false);
      // Reset file input
      if (importFileRef.current) {
        importFileRef.current.value = '';
      }
    }
  };

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd/Ctrl + K: Search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowSearch(true);
      }

      // Cmd/Ctrl + N: New conversation
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        onNewConversation();
      }

      // Cmd/Ctrl + /: Toggle sidebar
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        if (onToggleMobile) {
          onToggleMobile();
        }
      }

      // Escape: Close modals and mobile sidebar
      if (e.key === 'Escape') {
        if (showSettings) setShowSettings(false);
        else if (showAnalytics) setShowAnalytics(false);
        else if (showProjects) setShowProjects(false);
        else if (showBatch) setShowBatch(false);
        else if (showSearch) setShowSearch(false);
        else if (isMobileOpen && onToggleMobile) onToggleMobile();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showSettings, showAnalytics, showProjects, showBatch, showSearch, isMobileOpen, onNewConversation, onToggleMobile]);

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  const loadFolders = async () => {
    try {
      const { authFetch } = await import('../api/client.js');
      const response = await authFetch(`${API_BASE}/folders`);
      const data = await response.json();
      setFolders(data.folders || []);
    } catch (error) {
      console.error('Failed to load folders:', error);
    }
  };

  const loadTags = useCallback(async () => {
    try {
      const { authFetch } = await import('../api/client.js');
      const response = await authFetch(`${API_BASE}/tags`);
      const data = await response.json();
      setAllTags(data.tags || []);
    } catch (error) {
      console.error('Failed to load tags:', error);
    }
  }, []);

  // Load folders and tags on mount
  useEffect(() => {
    loadFolders();
    loadTags();
  }, [loadTags]);

  // Reload tags when conversations change
  useEffect(() => {
    loadTags();
  }, [conversations, loadTags]);

  const toggleFolder = (folderId) => {
    setCollapsedFolders(prev => ({
      ...prev,
      [folderId]: !prev[folderId]
    }));
  };

  const handleDragStart = (e, conversation) => {
    setDraggedConversation(conversation);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDropOnFolder = async (e, folderId) => {
    e.preventDefault();
    if (!draggedConversation) return;

    try {
      const { authFetch } = await import('../api/client.js');
      await authFetch(`${API_BASE}/conversations/${draggedConversation.id}/folder`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_id: folderId })
      });

      // Update local state
      if (onConversationsChange) {
        onConversationsChange();
      }
    } catch (error) {
      console.error('Failed to move conversation:', error);
    }

    setDraggedConversation(null);
  };

  const handleDropOnUncategorized = async (e) => {
    e.preventDefault();
    if (!draggedConversation) return;

    try {
      const { authFetch } = await import('../api/client.js');
      await authFetch(`${API_BASE}/conversations/${draggedConversation.id}/folder`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_id: null })
      });

      if (onConversationsChange) {
        onConversationsChange();
      }
    } catch (error) {
      console.error('Failed to move conversation:', error);
    }

    setDraggedConversation(null);
  };

  const updateConversationTags = async (conversationId, tags) => {
    try {
      const { authFetch } = await import('../api/client.js');
      await authFetch(`${API_BASE}/conversations/${conversationId}/tags`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags })
      });

      if (onConversationsChange) {
        onConversationsChange();
      }
      loadTags();
    } catch (error) {
      console.error('Failed to update tags:', error);
    }
  };

  const handleTagClick = (e, conversationId, tag) => {
    e.stopPropagation();
    const conversation = conversations.find(c => c.id === conversationId);
    if (!conversation) return; // Safety check
    const newTags = (conversation.tags || []).filter(t => t !== tag);
    updateConversationTags(conversationId, newTags);
  };

  const handleAddTag = (conversationId) => {
    if (!tagInput.trim()) return;

    const conversation = conversations.find(c => c.id === conversationId);
    if (!conversation) return; // Safety check
    const newTags = [...(conversation.tags || []), tagInput.trim()];
    updateConversationTags(conversationId, newTags);
    setTagInput('');
    setEditingTags(null);
  };

  const toggleTagFilter = (tag) => {
    setSelectedTags(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;

    try {
      const { authFetch } = await import('../api/client.js');
      await authFetch(`${API_BASE}/folders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newFolderName.trim() })
      });

      setNewFolderName('');
      setShowNewFolder(false);
      loadFolders();
    } catch (error) {
      console.error('Failed to create folder:', error);
    }
  };

  const handleDeleteFolder = async (e, folderId) => {
    e.stopPropagation();
    if (!confirm('Delete this folder? Conversations will be moved to Uncategorized.')) return;

    try {
      const { authFetch } = await import('../api/client.js');
      await authFetch(`${API_BASE}/folders/${folderId}`, {
        method: 'DELETE'
      });

      loadFolders();
      if (onConversationsChange) {
        onConversationsChange();
      }
    } catch (error) {
      console.error('Failed to delete folder:', error);
    }
  };

  // Filter conversations by selected tags
  const filteredConversations = selectedTags.length > 0
    ? conversations.filter(conv =>
        selectedTags.some(tag => conv.tags?.includes(tag))
      )
    : conversations;

  // Group conversations by folder
  const conversationsByFolder = {};
  const uncategorized = [];

  filteredConversations.forEach(conv => {
    if (conv.folder_id) {
      if (!conversationsByFolder[conv.folder_id]) {
        conversationsByFolder[conv.folder_id] = [];
      }
      conversationsByFolder[conv.folder_id].push(conv);
    } else {
      uncategorized.push(conv);
    }
  });

  const renderConversationItem = (conv) => (
    <div
      key={conv.id}
      className={`conversation-item ${
        conv.id === currentConversationId ? 'active' : ''
      }`}
      onClick={() => handleSelectConversation(conv.id)}
      draggable
      onDragStart={(e) => handleDragStart(e, conv)}
    >
      <div className="conversation-content">
        <div className="conversation-title">
          {conv.title || 'New Conversation'}
        </div>
        <div className="conversation-meta">
          {conv.message_count} messages
        </div>
        {conv.tags && conv.tags.length > 0 && (
          <div className="conversation-tags">
            {conv.tags.map(tag => (
              <span
                key={tag}
                className="tag"
                onClick={(e) => handleTagClick(e, conv.id, tag)}
                title="Click to remove"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
        {editingTags === conv.id && (
          <div className="tag-input-container" onClick={(e) => e.stopPropagation()}>
            <input
              type="text"
              className="tag-input"
              placeholder="Add tag..."
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleAddTag(conv.id);
                }
              }}
              list="tag-suggestions"
              autoFocus
            />
            <datalist id="tag-suggestions">
              {allTags.map(tag => (
                <option key={tag} value={tag} />
              ))}
            </datalist>
            <button
              className="tag-add-btn"
              onClick={() => handleAddTag(conv.id)}
            >
              +
            </button>
          </div>
        )}
      </div>
      <div className="conversation-actions">
        <button
          className="tag-conversation-btn"
          onClick={(e) => {
            e.stopPropagation();
            setEditingTags(editingTags === conv.id ? null : conv.id);
            setTagInput('');
          }}
          title="Add tag"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"></path>
            <line x1="7" y1="7" x2="7.01" y2="7"></line>
          </svg>
        </button>
        <button
          className="delete-conversation-btn"
          onClick={(e) => {
            e.stopPropagation();
            if (confirm('Delete this conversation?')) {
              onDeleteConversation(conv.id);
            }
          }}
          title="Delete conversation"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 6h18"></path>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
            <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
          </svg>
        </button>
      </div>
    </div>
  );

  const getFolderIcon = (iconName) => {
    const icons = {
      briefcase: <path d="M20 7h-4V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2zM10 5h4v2h-4V5z"></path>,
      users: <><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></>,
      archive: <><polyline points="21 8 21 21 3 21 3 8"></polyline><rect x="1" y="3" width="22" height="5"></rect><line x1="10" y1="12" x2="14" y2="12"></line></>,
      star: <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>,
      folder: <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
    };
    return icons[iconName] || icons.folder;
  };

  // Close sidebar when selecting conversation on mobile
  const handleSelectConversation = (id) => {
    onSelectConversation(id);
    if (window.innerWidth <= 768 && onToggleMobile) {
      onToggleMobile();
    }
  };

  return (
    <>
      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${isMobileOpen ? 'visible' : ''}`}
        onClick={onToggleMobile}
      />

      <div className={`sidebar ${isMobileOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-header-top">
            <h1>AI Konsey</h1>
            <div className="header-buttons">
              {/* Search - always visible */}
              <button
                className="header-btn"
                onClick={() => setShowSearch(true)}
                title="Search (Cmd/Ctrl+K)"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8"></circle>
                  <path d="m21 21-4.35-4.35"></path>
                </svg>
              </button>

              {/* Settings - always visible */}
              <button
                className="header-btn"
                onClick={() => setShowSettings(true)}
                title="Settings"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
              </button>

              {/* More menu dropdown */}
              <div className="more-menu-container">
                <button
                  className={`header-btn ${showMoreMenu ? 'open' : ''}`}
                  onClick={() => setShowMoreMenu(!showMoreMenu)}
                  title="More options"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="1"></circle>
                    <circle cx="12" cy="5" r="1"></circle>
                    <circle cx="12" cy="19" r="1"></circle>
                  </svg>
                </button>

                {showMoreMenu && (
                  <>
                    <div className="more-menu-backdrop" onClick={() => setShowMoreMenu(false)} />
                    <div className="more-menu">
                      <button onClick={() => { setShowProjects(true); setShowMoreMenu(false); }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                        </svg>
                        Projects
                      </button>
                      <button onClick={() => { setShowBatch(true); setShowMoreMenu(false); }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                          <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
                        </svg>
                        Batch Processing
                      </button>
                      <button onClick={() => { setShowAnalytics(true); setShowMoreMenu(false); }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <line x1="12" y1="20" x2="12" y2="10"></line>
                          <line x1="18" y1="20" x2="18" y2="4"></line>
                          <line x1="6" y1="20" x2="6" y2="16"></line>
                        </svg>
                        Analytics
                      </button>
                      {user?.is_admin && (
                        <button onClick={() => { setShowAdminPanel(true); setShowMoreMenu(false); }}>
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                            <circle cx="9" cy="7" r="4"></circle>
                            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                          </svg>
                          Admin Panel
                        </button>
                      )}
                      <div className="more-menu-divider" />
                      <button onClick={() => { toggleTheme(); setShowMoreMenu(false); }}>
                        {theme === 'light' ? '🌙' : '☀️'}
                        {theme === 'light' ? 'Dark Mode' : 'Light Mode'}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="conversation-actions-row">
            <button
              className="new-conversation-btn ripple"
              onClick={onNewConversation}
              disabled={isCreatingConversation}
              title="Create new chat (Cmd/Ctrl+N)"
            >
              {isCreatingConversation ? (
                <>
                  <span className="import-spinner" style={{ marginRight: '8px' }} />
                  Creating...
                </>
              ) : (
                '+ New Chat'
              )}
            </button>
            <button
              className="import-btn"
              onClick={handleImportClick}
              disabled={isImporting}
              title="Import conversation from JSON"
            >
              {isImporting ? (
                <span className="import-spinner" />
              ) : (
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              )}
            </button>
            <input
              ref={importFileRef}
              type="file"
              accept=".json"
              onChange={handleImportFile}
              style={{ display: 'none' }}
            />
          </div>
        </div>

        {allTags.length > 0 && (
          <div className="tag-filter-section">
            <div className="tag-filter-label">Filter by tags:</div>
            <div className="tag-filter-list">
              {allTags.map(tag => (
                <button
                  key={tag}
                  className={`tag-filter ${selectedTags.includes(tag) ? 'active' : ''}`}
                  onClick={() => toggleTagFilter(tag)}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="conversation-list">
          {/* New folder input */}
          {showNewFolder && (
            <div className="new-folder-container">
              <input
                type="text"
                className="new-folder-input"
                placeholder="Folder name..."
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    handleCreateFolder();
                  }
                }}
                autoFocus
              />
              <button className="new-folder-btn" onClick={handleCreateFolder}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h14"></path>
                  <path d="M12 5v14"></path>
                </svg>
              </button>
              <button className="cancel-folder-btn" onClick={() => {
                setShowNewFolder(false);
                setNewFolderName('');
              }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18"></path>
                  <path d="M6 6l12 12"></path>
                </svg>
              </button>
            </div>
          )}

          {/* Add folder button */}
          {!showNewFolder && selectedTags.length === 0 && (
            <button className="add-folder-btn" onClick={() => setShowNewFolder(true)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              <span>New Folder</span>
            </button>
          )}

          {filteredConversations.length === 0 ? (
            <div className="no-conversations">
              {selectedTags.length > 0 ? 'No conversations with selected tags' : 'No conversations yet'}
            </div>
          ) : (
            <>
              {/* All Conversations section */}
              {selectedTags.length === 0 && (
                <div className="folder-section">
                  <div className="folder-header" onClick={() => toggleFolder('all')}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 3h18v18H3z"></path>
                    </svg>
                    <span className="folder-name">All Conversations</span>
                    <span className="folder-count">{conversations.length}</span>
                  </div>
                  {!collapsedFolders['all'] && conversations.map(renderConversationItem)}
                </div>
              )}

              {/* Folder sections */}
              {folders.map(folder => {
                const folderConvs = conversationsByFolder[folder.id] || [];
                if (folderConvs.length === 0 && selectedTags.length > 0) return null;

                return (
                  <div
                    key={folder.id}
                    className="folder-section"
                    onDragOver={handleDragOver}
                    onDrop={(e) => handleDropOnFolder(e, folder.id)}
                  >
                    <div
                      className="folder-header"
                      onClick={() => toggleFolder(folder.id)}
                      style={{ borderLeftColor: folder.color }}
                    >
                      <svg
                        className={`folder-icon ${collapsedFolders[folder.id] ? 'collapsed' : ''}`}
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke={folder.color}
                        strokeWidth="2"
                      >
                        {getFolderIcon(folder.icon)}
                      </svg>
                      <span className="folder-name">{folder.name}</span>
                      <span className="folder-count">{folderConvs.length}</span>
                      <button
                        className="delete-folder-btn"
                        onClick={(e) => handleDeleteFolder(e, folder.id)}
                        title="Delete folder"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M3 6h18"></path>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
                          <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                        </svg>
                      </button>
                    </div>
                    {!collapsedFolders[folder.id] && folderConvs.map(renderConversationItem)}
                  </div>
                );
              })}

              {/* Uncategorized section */}
              {uncategorized.length > 0 && (
                <div
                  className="folder-section"
                  onDragOver={handleDragOver}
                  onDrop={handleDropOnUncategorized}
                >
                  <div
                    className="folder-header"
                    onClick={() => toggleFolder('uncategorized')}
                  >
                    <svg
                      className={`folder-icon ${collapsedFolders['uncategorized'] ? 'collapsed' : ''}`}
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <span className="folder-name">Uncategorized</span>
                    <span className="folder-count">{uncategorized.length}</span>
                  </div>
                  {!collapsedFolders['uncategorized'] && uncategorized.map(renderConversationItem)}
                </div>
              )}
            </>
          )}
        </div>
        
        {/* Sidebar Footer with User Info */}
        <div className="sidebar-footer">
          {user && (
            <div className="user-info">
              <div className="user-avatar">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt={user.name || user.email} />
                ) : (
                  <span className="avatar-initial">
                    {(user.name || user.email || 'U').charAt(0).toUpperCase()}
                  </span>
                )}
              </div>
              <div className="user-details">
                <div className="user-name">{user.name || 'User'}</div>
                <div className="user-email">{user.email}</div>
              </div>
            </div>
          )}
          <button
            className="logout-btn"
            onClick={() => {
              logout();
              navigate('/login');
            }}
            title="Logout"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
          </button>
        </div>
      </div>

      <SearchModal
        isOpen={showSearch}
        onClose={() => setShowSearch(false)}
        onSelectConversation={onSelectConversation}
      />
      <Projects
        isOpen={showProjects}
        onClose={() => setShowProjects(false)}
        onProjectSelect={setCurrentProjectId}
        currentProjectId={currentProjectId}
      />
      <BatchProcessor isOpen={showBatch} onClose={() => setShowBatch(false)} />
      <Settings isOpen={showSettings} onClose={() => setShowSettings(false)} />
      <Analytics isOpen={showAnalytics} onClose={() => setShowAnalytics(false)} />
      <AdminPanel isOpen={showAdminPanel} onClose={() => setShowAdminPanel(false)} />
    </>
  );
}
