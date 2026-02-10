/**
 * Projects section for sidebar
 * Shows projects as collapsible groups with their conversations
 */

import React from 'react';

export default function ProjectsSection({
  projects,
  conversations,
  currentId,
  currentProjectId,
  collapsedProjects,
  onToggleProject,
  onSelectProject,
  onSelectConversation,
  onOpenProjectSettings,
}) {
  if (!projects || projects.length === 0) return null;

  // Group conversations by project
  const getProjectConversations = (projectId) => {
    return conversations.filter(conv => conv.project_id === projectId);
  };

  return (
    <div className="sidebar-section projects-section">
      <div className="section-label">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
        </svg>
        <span>Projects</span>
      </div>

      {projects.map(project => {
        const projectConvs = getProjectConversations(project.id);
        const isCollapsed = collapsedProjects?.[project.id];
        const isActive = currentProjectId === project.id;

        return (
          <div key={project.id} className="project-group">
            <div
              className={`project-header ${isActive ? 'active' : ''}`}
              onClick={() => onToggleProject(project.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && onToggleProject(project.id)}
            >
              <div className="project-header-left">
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
                <span className="project-icon">📁</span>
                <span className="project-name" title={project.name}>
                  {project.name}
                </span>
              </div>
              <div className="project-header-right">
                <span className="project-count">{projectConvs.length}</span>
                <button
                  className="project-settings-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenProjectSettings(project);
                  }}
                  title="Project settings"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="1"></circle>
                    <circle cx="19" cy="12" r="1"></circle>
                    <circle cx="5" cy="12" r="1"></circle>
                  </svg>
                </button>
              </div>
            </div>

            {!isCollapsed && projectConvs.length > 0 && (
              <div className="project-conversations">
                {projectConvs.map(conv => (
                  <div
                    key={conv.id}
                    className={`sidebar-item project-conversation ${conv.id === currentId ? 'active' : ''}`}
                    onClick={() => onSelectConversation(conv.id)}
                  >
                    <span className="item-icon">💬</span>
                    <span className="item-title" title={conv.title}>
                      {conv.title || 'New Conversation'}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {!isCollapsed && projectConvs.length === 0 && (
              <div className="project-empty">
                No conversations yet
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
