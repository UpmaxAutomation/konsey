import { useState, useEffect, useRef, useCallback } from 'react';
import './Projects.css';
import { api } from '../api';

export default function Projects({ isOpen, onClose, onProjectSelect, currentProjectId }) {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    system_prompt: '',
    council_models: null,
    chairman_model: null,
  });
  const [knowledgeFile, setKnowledgeFile] = useState({ filename: '', content: '' });
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [activeTab, setActiveTab] = useState('instructions'); // 'instructions', 'knowledge', 'memory'
  const [memoryContext, setMemoryContext] = useState('');
  const [memoryStats, setMemoryStats] = useState(null);
  const [newFact, setNewFact] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      loadProjects();
    }
  }, [isOpen]);

  useEffect(() => {
    if (currentProjectId && projects.length > 0) {
      const project = projects.find(p => p.id === currentProjectId);
      if (project) {
        loadProjectDetails(project.id);
      }
    }
  }, [currentProjectId, projects]);

  const loadProjects = async () => {
    try {
      const projectsList = await api.listProjects();
      setProjects(projectsList);
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  const loadProjectDetails = async (projectId) => {
    try {
      const project = await api.getProject(projectId);
      setSelectedProject(project);
      setFormData({
        name: project.name,
        description: project.description || '',
        system_prompt: project.system_prompt || '',
        council_models: project.council_config?.council_models || null,
        chairman_model: project.council_config?.chairman_model || null,
      });
      // Load memory
      loadProjectMemory(projectId);
    } catch (error) {
      console.error('Failed to load project details:', error);
    }
  };

  const loadProjectMemory = async (projectId) => {
    try {
      const [contextRes, statsRes] = await Promise.all([
        api.getProjectMemory(projectId),
        api.getProjectMemoryStats(projectId)
      ]);
      setMemoryContext(contextRes.context || 'No memories stored yet.');
      setMemoryStats(statsRes.stats);
    } catch (error) {
      console.error('Failed to load project memory:', error);
    }
  };

  const handleCreateProject = async () => {
    if (!formData.name.trim()) {
      alert('Project name is required');
      return;
    }

    setLoading(true);
    try {
      const project = await api.createProject(formData);
      setProjects([...projects, project]);
      setSelectedProject(project);
      setIsCreating(false);
      resetForm();
    } catch (error) {
      console.error('Failed to create project:', error);
      alert('Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProject = async () => {
    if (!selectedProject) return;

    setLoading(true);
    try {
      const updated = await api.updateProject(selectedProject.id, {
        name: formData.name,
        description: formData.description,
        system_prompt: formData.system_prompt,
        council_config: {
          council_models: formData.council_models,
          chairman_model: formData.chairman_model,
        },
      });
      setSelectedProject(updated);
      setProjects(projects.map(p => p.id === updated.id ? updated : p));
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to update project:', error);
      alert('Failed to update project');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProject = async (projectId) => {
    if (!confirm('Are you sure you want to delete this project?')) return;

    setLoading(true);
    try {
      await api.deleteProject(projectId);
      setProjects(projects.filter(p => p.id !== projectId));
      if (selectedProject?.id === projectId) {
        setSelectedProject(null);
      }
    } catch (error) {
      console.error('Failed to delete project:', error);
      alert('Failed to delete project');
    } finally {
      setLoading(false);
    }
  };

  const handleAddKnowledge = async () => {
    if (!selectedProject || !knowledgeFile.filename || !knowledgeFile.content) {
      alert('Filename and content are required');
      return;
    }

    setLoading(true);
    try {
      await api.addKnowledgeToProject(selectedProject.id, knowledgeFile);
      await loadProjectDetails(selectedProject.id);
      setKnowledgeFile({ filename: '', content: '' });
    } catch (error) {
      console.error('Failed to add knowledge:', error);
      alert('Failed to add knowledge file');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveKnowledge = async (fileId) => {
    if (!selectedProject) return;

    setLoading(true);
    try {
      await api.removeKnowledgeFromProject(selectedProject.id, fileId);
      await loadProjectDetails(selectedProject.id);
    } catch (error) {
      console.error('Failed to remove knowledge:', error);
      alert('Failed to remove knowledge file');
    } finally {
      setLoading(false);
    }
  };

  // File upload handlers
  const handleFileSelect = useCallback(async (files) => {
    if (!selectedProject || !files.length) return;

    setLoading(true);
    for (const file of files) {
      try {
        const content = await file.text();
        await api.addKnowledgeToProject(selectedProject.id, {
          filename: file.name,
          content,
          file_type: getFileType(file.name),
        });
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
      }
    }
    await loadProjectDetails(selectedProject.id);
    setLoading(false);
  }, [selectedProject]);

  const getFileType = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    const types = {
      md: 'markdown',
      txt: 'text',
      js: 'javascript',
      ts: 'typescript',
      py: 'python',
      json: 'json',
      html: 'html',
      css: 'css',
    };
    return types[ext] || 'text';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f =>
      f.type.startsWith('text/') ||
      f.name.endsWith('.md') ||
      f.name.endsWith('.txt') ||
      f.name.endsWith('.json') ||
      f.name.endsWith('.js') ||
      f.name.endsWith('.ts') ||
      f.name.endsWith('.py')
    );
    if (files.length) {
      handleFileSelect(files);
    }
  }, [handleFileSelect]);

  // Memory handlers
  const handleAddFact = async () => {
    if (!selectedProject || !newFact.trim()) return;

    setLoading(true);
    try {
      await api.addProjectFact(selectedProject.id, newFact.trim());
      await loadProjectMemory(selectedProject.id);
      setNewFact('');
    } catch (error) {
      console.error('Failed to add fact:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClearMemory = async () => {
    if (!selectedProject) return;
    if (!confirm('Clear all project memories? This cannot be undone.')) return;

    setLoading(true);
    try {
      await api.clearProjectMemory(selectedProject.id);
      await loadProjectMemory(selectedProject.id);
    } catch (error) {
      console.error('Failed to clear memory:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = async () => {
    if (!selectedProject) return;

    try {
      const response = await api.createConversationInProject(selectedProject.id);
      onProjectSelect(selectedProject.id);
      onClose();
    } catch (error) {
      console.error('Failed to create conversation:', error);
      alert('Failed to create conversation');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      system_prompt: '',
      council_models: null,
      chairman_model: null,
    });
  };

  if (!isOpen) return null;

  return (
    <div className="projects-modal-overlay" onClick={onClose}>
      <div className="projects-modal" onClick={(e) => e.stopPropagation()}>
        <div className="projects-header">
          <h2>📁 Projects</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="projects-content">
          <div className="projects-sidebar">
            <button
              className="new-project-btn"
              onClick={() => {
                setIsCreating(true);
                setSelectedProject(null);
                resetForm();
              }}
            >
              + New Project
            </button>

            <div className="projects-list">
              {projects.map((project) => (
                <div
                  key={project.id}
                  className={`project-item ${selectedProject?.id === project.id ? 'active' : ''}`}
                  onClick={() => loadProjectDetails(project.id)}
                >
                  <div className="project-name">{project.name}</div>
                  <div className="project-meta">
                    {new Date(project.created_at).toLocaleDateString()}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="projects-main">
            {isCreating ? (
              <div className="project-form">
                <h3>Create New Project</h3>

                <label>
                  Project Name *
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="My Project"
                  />
                </label>

                <label>
                  Description
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Project description..."
                    rows="3"
                  />
                </label>

                <label>
                  System Instructions
                  <textarea
                    value={formData.system_prompt}
                    onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                    placeholder="Custom instructions for all conversations in this project...&#10;&#10;Example: You are an expert in React and TypeScript. Always provide code examples."
                    rows="6"
                  />
                </label>

                <div className="form-actions">
                  <button onClick={handleCreateProject} disabled={loading}>
                    {loading ? 'Creating...' : 'Create Project'}
                  </button>
                  <button onClick={() => { setIsCreating(false); resetForm(); }} disabled={loading}>
                    Cancel
                  </button>
                </div>
              </div>
            ) : selectedProject ? (
              <div className="project-details">
                {isEditing ? (
                  <div className="project-form">
                    <h3>Edit Project</h3>

                    <label>
                      Project Name *
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      />
                    </label>

                    <label>
                      Description
                      <textarea
                        value={formData.description}
                        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                        rows="3"
                      />
                    </label>

                    <label>
                      System Instructions
                      <textarea
                        value={formData.system_prompt}
                        onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                        rows="6"
                      />
                    </label>

                    <div className="form-actions">
                      <button onClick={handleUpdateProject} disabled={loading}>
                        {loading ? 'Saving...' : 'Save Changes'}
                      </button>
                      <button onClick={() => setIsEditing(false)} disabled={loading}>
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="project-header">
                      <div>
                        <h3>{selectedProject.name}</h3>
                        <p className="project-description">{selectedProject.description}</p>
                      </div>
                      <div className="project-actions">
                        <button onClick={() => setIsEditing(true)}>Edit</button>
                        <button onClick={() => handleDeleteProject(selectedProject.id)}>Delete</button>
                        <button className="primary" onClick={handleNewConversation}>
                          + New Chat
                        </button>
                      </div>
                    </div>

                    {/* Tabs */}
                    <div className="project-tabs">
                      <button
                        className={`tab ${activeTab === 'instructions' ? 'active' : ''}`}
                        onClick={() => setActiveTab('instructions')}
                      >
                        📝 Instructions
                      </button>
                      <button
                        className={`tab ${activeTab === 'knowledge' ? 'active' : ''}`}
                        onClick={() => setActiveTab('knowledge')}
                      >
                        📚 Knowledge ({selectedProject.knowledge_base?.length || 0})
                      </button>
                      <button
                        className={`tab ${activeTab === 'memory' ? 'active' : ''}`}
                        onClick={() => setActiveTab('memory')}
                      >
                        🧠 Memory
                      </button>
                    </div>

                    {/* Instructions Tab */}
                    {activeTab === 'instructions' && (
                      <div className="project-section">
                        <div className="section-header">
                          <h4>System Instructions</h4>
                          <span className="section-hint">These instructions are prepended to every conversation</span>
                        </div>
                        <div className="system-prompt-display">
                          {selectedProject.system_prompt || (
                            <em className="empty-state">
                              No instructions set. Click "Edit" to add custom instructions.
                            </em>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Knowledge Tab */}
                    {activeTab === 'knowledge' && (
                      <div className="project-section">
                        <div className="section-header">
                          <h4>Knowledge Base</h4>
                          <span className="section-hint">Files are included as context in all conversations</span>
                        </div>

                        {/* Drag and Drop Zone */}
                        <div
                          className={`drop-zone ${isDragging ? 'dragging' : ''}`}
                          onDragOver={handleDragOver}
                          onDragLeave={handleDragLeave}
                          onDrop={handleDrop}
                          onClick={() => fileInputRef.current?.click()}
                        >
                          <input
                            ref={fileInputRef}
                            type="file"
                            multiple
                            accept=".txt,.md,.json,.js,.ts,.py,.html,.css"
                            style={{ display: 'none' }}
                            onChange={(e) => handleFileSelect(Array.from(e.target.files))}
                          />
                          <div className="drop-zone-content">
                            <span className="drop-icon">📄</span>
                            <p>Drag & drop files here or click to upload</p>
                            <span className="drop-hint">.txt, .md, .json, .js, .ts, .py supported</span>
                          </div>
                        </div>

                        {/* Manual Add Form */}
                        <div className="knowledge-add-form">
                          <input
                            type="text"
                            placeholder="Filename (e.g., notes.md)"
                            value={knowledgeFile.filename}
                            onChange={(e) => setKnowledgeFile({ ...knowledgeFile, filename: e.target.value })}
                          />
                          <textarea
                            placeholder="Paste content here..."
                            value={knowledgeFile.content}
                            onChange={(e) => setKnowledgeFile({ ...knowledgeFile, content: e.target.value })}
                            rows="4"
                          />
                          <button onClick={handleAddKnowledge} disabled={loading}>
                            Add File
                          </button>
                        </div>

                        {/* Knowledge List */}
                        <div className="knowledge-list">
                          {selectedProject.knowledge_base?.length > 0 ? (
                            selectedProject.knowledge_base.map((file) => (
                              <div key={file.id} className="knowledge-item">
                                <div className="knowledge-info">
                                  <strong>{file.filename}</strong>
                                  <span className="knowledge-meta">
                                    {file.file_type} • {(file.size / 1024).toFixed(1)} KB
                                  </span>
                                </div>
                                <button
                                  className="remove-btn"
                                  onClick={() => handleRemoveKnowledge(file.id)}
                                >
                                  ×
                                </button>
                              </div>
                            ))
                          ) : (
                            <em className="empty-state">No files in knowledge base</em>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Memory Tab */}
                    {activeTab === 'memory' && (
                      <div className="project-section">
                        <div className="section-header">
                          <h4>Project Memory</h4>
                          <span className="section-hint">Facts and decisions remembered for this project</span>
                        </div>

                        {/* Memory Stats */}
                        {memoryStats && (
                          <div className="memory-stats">
                            <span>📝 {memoryStats.facts_count} facts</span>
                            <span>📋 {memoryStats.decisions_count} decisions</span>
                            <span>⚙️ {memoryStats.preferences_count} preferences</span>
                          </div>
                        )}

                        {/* Add Fact */}
                        <div className="add-fact-form">
                          <input
                            type="text"
                            placeholder="Add a fact to remember..."
                            value={newFact}
                            onChange={(e) => setNewFact(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleAddFact()}
                          />
                          <button onClick={handleAddFact} disabled={loading || !newFact.trim()}>
                            + Add
                          </button>
                        </div>

                        {/* Memory Content */}
                        <div className="memory-content">
                          <pre>{memoryContext}</pre>
                        </div>

                        {/* Memory Actions */}
                        <div className="memory-actions">
                          <button
                            className="refresh-btn"
                            onClick={() => loadProjectMemory(selectedProject.id)}
                          >
                            🔄 Refresh
                          </button>
                          <button
                            className="clear-btn"
                            onClick={handleClearMemory}
                          >
                            🗑️ Clear All
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            ) : (
              <div className="project-empty-state">
                <div className="empty-icon">📁</div>
                <p>Select a project or create a new one</p>
                <span>Projects help you organize conversations with shared context</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
