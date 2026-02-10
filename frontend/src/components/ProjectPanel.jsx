/**
 * ProjectPanel - Right panel showing project details when a project is selected
 * Features: Instructions, Memory (facts/preferences), Knowledge Base files
 */

import { useState, useEffect } from 'react';
import { api } from '../api';
import './ProjectPanel.css';

export default function ProjectPanel({ projectId, onClose }) {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('instructions');
  const [memory, setMemory] = useState(null);
  const [memoryStats, setMemoryStats] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedInstructions, setEditedInstructions] = useState('');
  const [newFact, setNewFact] = useState('');
  const [addingFact, setAddingFact] = useState(false);

  // Load project details
  useEffect(() => {
    if (projectId) {
      loadProject();
      loadMemory();
    }
  }, [projectId]);

  const loadProject = async () => {
    try {
      setLoading(true);
      const data = await api.getProject(projectId);
      setProject(data);
      setEditedInstructions(data.system_prompt || '');
    } catch (err) {
      console.error('Failed to load project:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadMemory = async () => {
    try {
      const [memoryData, statsData] = await Promise.all([
        api.getProjectMemory(projectId),
        api.getProjectMemoryStats(projectId),
      ]);
      setMemory(memoryData);
      setMemoryStats(statsData);
    } catch (err) {
      console.error('Failed to load memory:', err);
    }
  };

  const handleSaveInstructions = async () => {
    try {
      await api.updateProject(projectId, { system_prompt: editedInstructions });
      setProject((prev) => ({ ...prev, system_prompt: editedInstructions }));
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to save instructions:', err);
    }
  };

  const handleAddFact = async () => {
    if (!newFact.trim()) return;
    setAddingFact(true);
    try {
      await api.addProjectFact(projectId, newFact.trim());
      setNewFact('');
      loadMemory(); // Reload memory to show new fact
    } catch (err) {
      console.error('Failed to add fact:', err);
    } finally {
      setAddingFact(false);
    }
  };

  const handleRemoveKnowledge = async (fileId) => {
    if (!confirm('Remove this file from knowledge base?')) return;
    try {
      await api.removeKnowledgeFromProject(projectId, fileId);
      setProject((prev) => ({
        ...prev,
        knowledge_base: prev.knowledge_base.filter((f) => f.id !== fileId),
      }));
    } catch (err) {
      console.error('Failed to remove knowledge:', err);
    }
  };

  const handleClearMemory = async () => {
    if (!confirm('Clear all memory for this project? This cannot be undone.')) return;
    try {
      await api.clearProjectMemory(projectId);
      loadMemory();
    } catch (err) {
      console.error('Failed to clear memory:', err);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="project-panel">
        <div className="project-panel-loading">
          <div className="spinner"></div>
          Loading project...
        </div>
      </div>
    );
  }

  if (!project) {
    return null;
  }

  return (
    <div className="project-panel">
      {/* Header */}
      <div className="project-panel-header">
        <div className="project-panel-title">
          <span className="project-panel-icon">{project.icon || '📁'}</span>
          <h2>{project.name}</h2>
        </div>
        <button className="project-panel-close" onClick={onClose} title="Close panel">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>

      {/* Tabs */}
      <div className="project-panel-tabs">
        <button
          className={`project-panel-tab ${activeTab === 'instructions' ? 'active' : ''}`}
          onClick={() => setActiveTab('instructions')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          Instructions
        </button>
        <button
          className={`project-panel-tab ${activeTab === 'memory' ? 'active' : ''}`}
          onClick={() => setActiveTab('memory')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 16v-4M12 8h.01"/>
          </svg>
          Memory
          {memoryStats?.total_items > 0 && (
            <span className="project-panel-badge">{memoryStats.total_items}</span>
          )}
        </button>
        <button
          className={`project-panel-tab ${activeTab === 'files' ? 'active' : ''}`}
          onClick={() => setActiveTab('files')}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
            <polyline points="13 2 13 9 20 9"/>
          </svg>
          Files
          {project.knowledge_base?.length > 0 && (
            <span className="project-panel-badge">{project.knowledge_base.length}</span>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="project-panel-content">
        {/* Instructions Tab */}
        {activeTab === 'instructions' && (
          <div className="project-panel-instructions">
            <div className="instructions-header">
              <h3>Custom Instructions</h3>
              {!isEditing && (
                <button className="edit-btn" onClick={() => setIsEditing(true)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                  Edit
                </button>
              )}
            </div>
            {isEditing ? (
              <div className="instructions-edit">
                <textarea
                  value={editedInstructions}
                  onChange={(e) => setEditedInstructions(e.target.value)}
                  placeholder="Enter custom instructions that will be applied to all conversations in this project..."
                  rows={8}
                />
                <div className="instructions-edit-actions">
                  <button className="btn-cancel" onClick={() => {
                    setIsEditing(false);
                    setEditedInstructions(project.system_prompt || '');
                  }}>
                    Cancel
                  </button>
                  <button className="btn-save" onClick={handleSaveInstructions}>
                    Save
                  </button>
                </div>
              </div>
            ) : (
              <div className="instructions-content">
                {project.system_prompt ? (
                  <pre>{project.system_prompt}</pre>
                ) : (
                  <p className="empty-state">No custom instructions set. Click Edit to add instructions.</p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Memory Tab */}
        {activeTab === 'memory' && (
          <div className="project-panel-memory">
            <div className="memory-header">
              <h3>Project Memory</h3>
              {memoryStats?.total_items > 0 && (
                <button className="clear-btn" onClick={handleClearMemory}>
                  Clear All
                </button>
              )}
            </div>

            {/* Add new fact */}
            <div className="memory-add">
              <input
                type="text"
                value={newFact}
                onChange={(e) => setNewFact(e.target.value)}
                placeholder="Add a fact to remember..."
                onKeyDown={(e) => e.key === 'Enter' && handleAddFact()}
              />
              <button onClick={handleAddFact} disabled={addingFact || !newFact.trim()}>
                {addingFact ? '...' : 'Add'}
              </button>
            </div>

            {/* Memory context */}
            {memory?.context ? (
              <div className="memory-context">
                <pre>{memory.context}</pre>
              </div>
            ) : (
              <p className="empty-state">No memory stored yet. Add facts or let Claude learn from conversations.</p>
            )}

            {/* Memory stats */}
            {memoryStats && (
              <div className="memory-stats">
                <div className="stat">
                  <span className="stat-label">Facts</span>
                  <span className="stat-value">{memoryStats.facts_count || 0}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Decisions</span>
                  <span className="stat-value">{memoryStats.decisions_count || 0}</span>
                </div>
                <div className="stat">
                  <span className="stat-label">Preferences</span>
                  <span className="stat-value">{memoryStats.preferences_count || 0}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Files Tab */}
        {activeTab === 'files' && (
          <div className="project-panel-files">
            <div className="files-header">
              <h3>Knowledge Base</h3>
              <span className="files-count">
                {project.knowledge_base?.length || 0} files
              </span>
            </div>

            {project.knowledge_base?.length > 0 ? (
              <div className="files-list">
                {project.knowledge_base.map((file) => (
                  <div key={file.id} className="file-item">
                    <div className="file-icon">
                      {file.file_type === 'code' ? '💻' : file.file_type === 'document' ? '📄' : '📝'}
                    </div>
                    <div className="file-info">
                      <span className="file-name">{file.filename}</span>
                      <span className="file-meta">
                        {formatFileSize(file.size || 0)} • Added {new Date(file.added_at).toLocaleDateString()}
                      </span>
                    </div>
                    <button
                      className="file-remove"
                      onClick={() => handleRemoveKnowledge(file.id)}
                      title="Remove file"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="files-empty">
                <div className="empty-icon">📚</div>
                <p>No files in knowledge base</p>
                <span className="empty-hint">
                  Add files to give Claude context about your project
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
