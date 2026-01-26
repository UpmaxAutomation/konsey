/**
 * ClaudeSidebar - Claude AI style sidebar with projects section and search
 * Features: starred projects, project search, keyboard shortcuts
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import './ClaudeSidebar.css';
import Settings from './Settings';
import SearchModal from './SearchModal';
import ProjectSettings from './ProjectSettings';
import NewProjectModal from './NewProjectModal';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { listProjects, createProject } from '../api';

// LocalStorage keys
const STARRED_PROJECTS_KEY = 'llm-council-starred-projects';

// Group conversations by time period
function groupByTime(conversations) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const lastWeek = new Date(today);
  lastWeek.setDate(lastWeek.getDate() - 7);
  const lastMonth = new Date(today);
  lastMonth.setDate(lastMonth.getDate() - 30);

  const groups = {
    today: [],
    yesterday: [],
    lastWeek: [],
    lastMonth: [],
    older: [],
  };

  conversations.forEach((conv) => {
    const date = new Date(conv.updated_at || conv.created_at);
    if (date >= today) {
      groups.today.push(conv);
    } else if (date >= yesterday) {
      groups.yesterday.push(conv);
    } else if (date >= lastWeek) {
      groups.lastWeek.push(conv);
    } else if (date >= lastMonth) {
      groups.lastMonth.push(conv);
    } else {
      groups.older.push(conv);
    }
  });

  return groups;
}

// Default project for when no projects exist
const DEFAULT_PROJECT = { id: 'all', name: 'All Chats', icon: '💬', description: 'All conversations' };

// Icon options for projects
const PROJECT_ICONS = ['📁', '💼', '🔬', '💻', '📚', '🎯', '🚀', '🔧', '📊', '🎨'];

export default function ClaudeSidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isMobileOpen,
  onToggleMobile,
  isCreatingConversation = false,
  onProjectChange,
  onProjectSelect,
  onMoveToProject,
}) {
  const [showSettings, setShowSettings] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showProjectSettings, setShowProjectSettings] = useState(false);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [moveMenuOpen, setMoveMenuOpen] = useState(null); // conversation id with open move menu
  const [selectedProjectForSettings, setSelectedProjectForSettings] = useState(null);
  const [projectsExpanded, setProjectsExpanded] = useState(true);
  const [currentProject, setCurrentProject] = useState(DEFAULT_PROJECT);
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [projectSearch, setProjectSearch] = useState('');
  const [starredProjects, setStarredProjects] = useState(() => {
    try {
      const stored = localStorage.getItem(STARRED_PROJECTS_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Save starred projects to localStorage
  useEffect(() => {
    localStorage.setItem(STARRED_PROJECTS_KEY, JSON.stringify(starredProjects));
  }, [starredProjects]);

  // Toggle star on a project
  const toggleStarProject = (projectId) => {
    setStarredProjects((prev) =>
      prev.includes(projectId)
        ? prev.filter((id) => id !== projectId)
        : [...prev, projectId]
    );
  };

  // Filter projects by search
  const filteredProjects = useMemo(() => {
    if (!projectSearch.trim()) return projects;
    const search = projectSearch.toLowerCase();
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(search) ||
        p.description?.toLowerCase().includes(search)
    );
  }, [projects, projectSearch]);

  // Sort projects: starred first, then by name
  const sortedProjects = useMemo(() => {
    return [...filteredProjects].sort((a, b) => {
      const aStarred = starredProjects.includes(a.id);
      const bStarred = starredProjects.includes(b.id);
      if (aStarred && !bStarred) return -1;
      if (!aStarred && bStarred) return 1;
      return a.name.localeCompare(b.name);
    });
  }, [filteredProjects, starredProjects]);

  // Load projects from backend
  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoadingProjects(true);
      const data = await listProjects();
      // Add icon to projects that don't have one
      const projectsWithIcons = (data.projects || data || []).map((p, i) => ({
        ...p,
        icon: p.icon || PROJECT_ICONS[i % PROJECT_ICONS.length],
      }));
      setProjects(projectsWithIcons);
    } catch (err) {
      console.error('Failed to load projects:', err);
    } finally {
      setLoadingProjects(false);
    }
  };

  // Handle project selection
  const handleProjectSelect = (project) => {
    setCurrentProject(project);
    onProjectChange?.(project.id === 'all' ? null : project.id);
    // Open ProjectView for actual projects (not "All Chats")
    if (project.id !== 'all') {
      onProjectSelect?.(project);
    } else {
      onProjectSelect?.(null);
    }
  };

  // Create new project via modal
  const handleCreateProject = async (projectData) => {
    const newProject = await createProject({
      name: projectData.name,
      description: projectData.description || '',
      system_prompt: projectData.system_prompt || projectData.instructions || '',
    });
    // Add icon from modal
    newProject.icon = projectData.icon || PROJECT_ICONS[projects.length % PROJECT_ICONS.length];
    setProjects((prev) => [...prev, newProject]);
    // Select the new project
    handleProjectSelect(newProject);
  };

  // Open project settings
  const handleProjectSettings = (e, project) => {
    e.stopPropagation();
    setSelectedProjectForSettings(project);
    setShowProjectSettings(true);
  };

  // Handle project update from settings
  const handleProjectUpdate = (updatedProject) => {
    setProjects((prev) =>
      prev.map((p) => (p.id === updatedProject.id ? { ...p, ...updatedProject } : p))
    );
    if (currentProject.id === updatedProject.id) {
      setCurrentProject((prev) => ({ ...prev, ...updatedProject }));
    }
  };

  // Handle project delete from settings
  const handleProjectDelete = (projectId) => {
    setProjects((prev) => prev.filter((p) => p.id !== projectId));
    if (currentProject.id === projectId) {
      setCurrentProject(DEFAULT_PROJECT);
      onProjectChange?.(null);
    }
  };

  // Sort conversations by updated_at descending
  const sortedConversations = useMemo(() => {
    return [...conversations].sort((a, b) => {
      const dateA = new Date(a.updated_at || a.created_at);
      const dateB = new Date(b.updated_at || b.created_at);
      return dateB - dateA;
    });
  }, [conversations]);

  // Group by time
  const groupedConversations = useMemo(() => {
    return groupByTime(sortedConversations);
  }, [sortedConversations]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd/Ctrl + K - Search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowSearch(true);
      }
      // Cmd/Ctrl + N - New conversation
      if ((e.metaKey || e.ctrlKey) && e.key === 'n' && !e.shiftKey) {
        e.preventDefault();
        onNewConversation();
      }
      // Cmd/Ctrl + Shift + N - New project
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'N') {
        e.preventDefault();
        setShowNewProjectModal(true);
      }
      // Cmd/Ctrl + Shift + P - Toggle projects section
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'P') {
        e.preventDefault();
        setProjectsExpanded((prev) => !prev);
      }
      // Escape - Close modals/sidebar
      if (e.key === 'Escape') {
        if (showNewProjectModal) setShowNewProjectModal(false);
        else if (showSettings) setShowSettings(false);
        else if (showSearch) setShowSearch(false);
        else if (showProjectSettings) setShowProjectSettings(false);
        else if (isMobileOpen && onToggleMobile) onToggleMobile();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [showSettings, showSearch, showProjectSettings, showNewProjectModal, isMobileOpen, onNewConversation, onToggleMobile]);

  // Close sidebar on mobile when selecting conversation
  const handleSelect = useCallback(
    (id) => {
      onSelectConversation(id);
      if (window.innerWidth <= 768 && onToggleMobile) {
        onToggleMobile();
      }
    },
    [onSelectConversation, onToggleMobile]
  );

  // Handle move to project
  const handleMoveToProject = async (conversationId, projectId) => {
    setMoveMenuOpen(null);
    if (onMoveToProject) {
      await onMoveToProject(conversationId, projectId);
    }
  };

  // Render a conversation item
  const renderConversation = (conv) => (
    <div
      key={conv.id}
      className={`claude-conv-item ${conv.id === currentConversationId ? 'active' : ''}`}
      onClick={() => handleSelect(conv.id)}
    >
      <svg className="claude-conv-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
      <span className="claude-conv-title">{conv.title || 'New conversation'}</span>
      {conv.project_id && (
        <span className="claude-conv-project-badge" title="In project">
          📁
        </span>
      )}
      <div className="claude-conv-actions">
        {/* Move to project button */}
        {onMoveToProject && projects.length > 0 && (
          <div className="claude-move-menu-wrapper">
            <button
              className="claude-conv-action-btn move"
              onClick={(e) => {
                e.stopPropagation();
                setMoveMenuOpen(moveMenuOpen === conv.id ? null : conv.id);
              }}
              title="Move to project"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                <path d="M12 11v6M9 14l3-3 3 3" />
              </svg>
            </button>
            {moveMenuOpen === conv.id && (
              <>
                <div className="claude-move-menu-backdrop" onClick={(e) => { e.stopPropagation(); setMoveMenuOpen(null); }} />
                <div className="claude-move-menu">
                  <div className="claude-move-menu-header">Move to project</div>
                  {conv.project_id && (
                    <button
                      className="claude-move-menu-item remove"
                      onClick={(e) => { e.stopPropagation(); handleMoveToProject(conv.id, null); }}
                    >
                      <span className="move-item-icon">🚫</span>
                      Remove from project
                    </button>
                  )}
                  {projects.map((project) => (
                    <button
                      key={project.id}
                      className={`claude-move-menu-item ${conv.project_id === project.id ? 'current' : ''}`}
                      onClick={(e) => { e.stopPropagation(); handleMoveToProject(conv.id, project.id); }}
                      disabled={conv.project_id === project.id}
                    >
                      <span className="move-item-icon">{project.icon}</span>
                      {project.name}
                      {conv.project_id === project.id && <span className="current-badge">current</span>}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
        <button
          className="claude-conv-action-btn delete"
          onClick={(e) => {
            e.stopPropagation();
            if (confirm('Delete this conversation?')) {
              onDeleteConversation(conv.id);
            }
          }}
          title="Delete"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>
    </div>
  );

  // Render a time group
  const renderGroup = (label, convs) => {
    if (convs.length === 0) return null;
    return (
      <div className="claude-time-group" key={label}>
        <div className="claude-time-label">{label}</div>
        {convs.map(renderConversation)}
      </div>
    );
  };

  // Get user initials
  const getInitials = () => {
    if (!user) return '?';
    if (user.full_name) {
      return user.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    return user.email?.[0]?.toUpperCase() || '?';
  };

  return (
    <>
      {/* Mobile overlay */}
      <div
        className={`claude-sidebar-overlay ${isMobileOpen ? 'visible' : ''}`}
        onClick={onToggleMobile}
      />

      <div className={`claude-sidebar ${isMobileOpen ? 'open' : ''}`}>
        {/* Header with new chat and search */}
        <div className="claude-sidebar-header">
          <button
            className="claude-new-chat-btn"
            onClick={onNewConversation}
            disabled={isCreatingConversation}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 5v14M5 12h14" />
            </svg>
            {isCreatingConversation ? 'Creating...' : 'New chat'}
          </button>

          <button className="claude-search-btn" onClick={() => setShowSearch(true)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            Search chats
            <span className="claude-search-shortcut">⌘K</span>
          </button>
        </div>

        {/* Projects Section */}
        <div className="claude-projects-section">
          <div className="claude-projects-header">
            <button
              className="claude-projects-toggle"
              onClick={() => setProjectsExpanded(!projectsExpanded)}
            >
              <svg
                className={`claude-projects-chevron ${projectsExpanded ? 'expanded' : ''}`}
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M9 18l6-6-6-6" />
              </svg>
              <span className="claude-projects-title">Projects</span>
            </button>
            <button
              className="claude-projects-settings"
              onClick={() => setShowSettings(true)}
              title="Settings"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
          </div>

          {projectsExpanded && (
            <div className="claude-projects-list">
              {/* Project search (shows when more than 3 projects) */}
              {projects.length > 3 && (
                <div className="claude-project-search">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <path d="m21 21-4.35-4.35" />
                  </svg>
                  <input
                    type="text"
                    placeholder="Search projects..."
                    value={projectSearch}
                    onChange={(e) => setProjectSearch(e.target.value)}
                    className="claude-project-search-input"
                  />
                  {projectSearch && (
                    <button
                      className="claude-project-search-clear"
                      onClick={() => setProjectSearch('')}
                    >
                      ×
                    </button>
                  )}
                </div>
              )}

              {/* Loading state */}
              {loadingProjects && (
                <div className="claude-projects-loading">Loading projects...</div>
              )}

              {/* User projects (sorted: starred first) */}
              {!loadingProjects && sortedProjects.map((project) => (
                <button
                  key={project.id}
                  className={`claude-project-item ${project.id === currentProject.id ? 'active' : ''} ${starredProjects.includes(project.id) ? 'starred' : ''}`}
                  onClick={() => handleProjectSelect(project)}
                >
                  <span className="claude-project-icon">{project.icon}</span>
                  <span className="claude-project-name">{project.name}</span>
                  <button
                    className={`claude-project-star-btn ${starredProjects.includes(project.id) ? 'starred' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleStarProject(project.id);
                    }}
                    title={starredProjects.includes(project.id) ? 'Unstar project' : 'Star project'}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill={starredProjects.includes(project.id) ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                    </svg>
                  </button>
                  <button
                    className="claude-project-edit-btn"
                    onClick={(e) => handleProjectSettings(e, project)}
                    title="Project settings"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="1" />
                      <circle cx="12" cy="5" r="1" />
                      <circle cx="12" cy="19" r="1" />
                    </svg>
                  </button>
                  {project.id === currentProject.id && (
                    <svg className="claude-project-check" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                </button>
              ))}

              {/* No results message */}
              {!loadingProjects && projectSearch && sortedProjects.length === 0 && (
                <div className="claude-projects-empty">No projects found</div>
              )}

              {/* New project button */}
              <button
                className="claude-new-project-btn"
                onClick={() => setShowNewProjectModal(true)}
                title="Create new project (Cmd+Shift+N)"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 5v14M5 12h14" />
                </svg>
                <span>New project</span>
                <span className="claude-shortcut-hint">&#8679;&#8984;N</span>
              </button>
            </div>
          )}
        </div>

        {/* Conversation list */}
        <div className="claude-conversation-list">
          {conversations.length === 0 ? (
            <div className="claude-empty-state">
              <div className="claude-empty-icon">💬</div>
              <div className="claude-empty-title">No conversations</div>
              <div className="claude-empty-text">Start a new chat to begin</div>
            </div>
          ) : (
            <>
              {renderGroup('Today', groupedConversations.today)}
              {renderGroup('Yesterday', groupedConversations.yesterday)}
              {renderGroup('Previous 7 days', groupedConversations.lastWeek)}
              {renderGroup('Previous 30 days', groupedConversations.lastMonth)}
              {renderGroup('Older', groupedConversations.older)}
            </>
          )}
        </div>

        {/* Footer with user info */}
        <div className="claude-sidebar-footer">
          <div className="claude-user-section">
            <div className="claude-user-avatar">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt={user.full_name || 'User'} />
              ) : (
                getInitials()
              )}
            </div>
            <div className="claude-user-info">
              <div className="claude-user-name">{user?.full_name || user?.email || 'User'}</div>
              <div className="claude-user-plan">Free plan</div>
            </div>
            {/* Settings button */}
            <button
              className="claude-settings-btn"
              onClick={() => setShowSettings(true)}
              title="Settings & API Keys"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="3" />
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
              </svg>
            </button>
            {/* Logout button */}
            <button
              className="claude-logout-btn"
              onClick={() => {
                logout();
                navigate('/login');
              }}
              title="Log out"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Modals */}
      <SearchModal
        isOpen={showSearch}
        onClose={() => setShowSearch(false)}
        onSelectConversation={onSelectConversation}
      />
      <Settings isOpen={showSettings} onClose={() => setShowSettings(false)} />
      <ProjectSettings
        isOpen={showProjectSettings}
        onClose={() => {
          setShowProjectSettings(false);
          setSelectedProjectForSettings(null);
        }}
        project={selectedProjectForSettings}
        onProjectUpdate={handleProjectUpdate}
        onProjectDelete={handleProjectDelete}
      />
      <NewProjectModal
        isOpen={showNewProjectModal}
        onClose={() => setShowNewProjectModal(false)}
        onCreateProject={handleCreateProject}
      />
    </>
  );
}
