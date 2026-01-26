/**
 * ProjectSettings - Modal for managing project settings like Claude Projects
 * Includes: name, description, custom instructions, knowledge base (file uploads)
 * Features: drag-drop upload, context usage indicator, icon picker
 */

import { useState, useEffect, useRef } from 'react';
import './ProjectSettings.css';
import {
  getProject,
  updateProject,
  deleteProject,
  addKnowledgeToProject,
  removeKnowledgeFromProject,
} from '../api';

// Available icons for projects
const PROJECT_ICONS = [
  '📁', '💼', '🔬', '💻', '📚', '🎯', '🚀', '🔧', '📊', '🎨',
  '📝', '🧪', '🎮', '🌐', '🔐', '📈', '🎵', '📸', '🏠', '💡',
  '🤖', '⚡', '🔥', '💎', '🌟', '🎪', '🧠', '📱', '🛠️', '🎁',
];

// Context window limit (200K tokens ≈ ~500 pages)
const CONTEXT_LIMIT = 200000;
const CHARS_PER_TOKEN = 4; // Approximate

export default function ProjectSettings({
  isOpen,
  onClose,
  project,
  onProjectUpdate,
  onProjectDelete,
}) {
  const [activeTab, setActiveTab] = useState('instructions');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [selectedIcon, setSelectedIcon] = useState('📁');
  const [knowledgeBase, setKnowledgeBase] = useState([]);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showIconPicker, setShowIconPicker] = useState(false);
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

  // Load project data when opened
  useEffect(() => {
    if (isOpen && project?.id) {
      loadProject();
    }
  }, [isOpen, project?.id]);

  // Reset state when closed
  useEffect(() => {
    if (!isOpen) {
      setActiveTab('instructions');
      setError(null);
    }
  }, [isOpen]);

  const loadProject = async () => {
    try {
      const data = await getProject(project.id);
      setName(data.name || '');
      setDescription(data.description || '');
      setSystemPrompt(data.system_prompt || '');
      setSelectedIcon(data.icon || project.icon || '📁');
      setKnowledgeBase(data.knowledge_base || []);
    } catch (err) {
      console.error('Failed to load project:', err);
      setError('Failed to load project details');
    }
  };

  // Calculate context usage
  const calculateContextUsage = () => {
    let totalChars = systemPrompt.length;
    knowledgeBase.forEach(file => {
      totalChars += file.size || 0;
    });
    const estimatedTokens = Math.ceil(totalChars / CHARS_PER_TOKEN);
    const percentage = Math.min((estimatedTokens / CONTEXT_LIMIT) * 100, 100);
    return { tokens: estimatedTokens, percentage, limit: CONTEXT_LIMIT };
  };

  const contextUsage = calculateContextUsage();

  // Drag and drop handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    // Only set dragging to false if we're leaving the drop zone entirely
    if (!dropZoneRef.current?.contains(e.relatedTarget)) {
      setIsDragging(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      await processFiles(files);
    }
  };

  const processFiles = async (files) => {
    setUploading(true);
    setError(null);

    for (const file of files) {
      try {
        const content = await readFileContent(file);
        const fileType = getFileType(file.name);

        const result = await addKnowledgeToProject(project.id, {
          filename: file.name,
          content,
          file_type: fileType,
        });

        setKnowledgeBase((prev) => [...prev, { ...result, size: file.size }]);
      } catch (err) {
        console.error('Failed to upload file:', err);
        setError(`Failed to upload ${file.name}`);
      }
    }

    setUploading(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateProject(project.id, {
        name,
        description,
        system_prompt: systemPrompt,
        icon: selectedIcon,
      });
      onProjectUpdate?.({ ...updated, icon: selectedIcon });
      onClose();
    } catch (err) {
      console.error('Failed to save project:', err);
      setError('Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete project "${name}"? This cannot be undone.`)) {
      return;
    }
    try {
      await deleteProject(project.id);
      onProjectDelete?.(project.id);
      onClose();
    } catch (err) {
      console.error('Failed to delete project:', err);
      setError('Failed to delete project');
    }
  };

  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    await processFiles(files);

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const readFileContent = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = reject;
      reader.readAsText(file);
    });
  };

  const getFileType = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    const typeMap = {
      pdf: 'pdf',
      doc: 'document',
      docx: 'document',
      txt: 'text',
      md: 'markdown',
      js: 'code',
      jsx: 'code',
      ts: 'code',
      tsx: 'code',
      py: 'code',
      css: 'code',
      html: 'code',
      json: 'code',
      csv: 'csv',
    };
    return typeMap[ext] || 'text';
  };

  const handleRemoveFile = async (fileId) => {
    try {
      await removeKnowledgeFromProject(project.id, fileId);
      setKnowledgeBase((prev) => prev.filter((f) => f.id !== fileId));
    } catch (err) {
      console.error('Failed to remove file:', err);
      setError('Failed to remove file');
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (fileType) => {
    const icons = {
      pdf: '📄',
      document: '📝',
      text: '📃',
      markdown: '📋',
      code: '💻',
      csv: '📊',
    };
    return icons[fileType] || '📎';
  };

  if (!isOpen || !project) return null;

  return (
    <div className="project-settings-overlay" onClick={onClose}>
      <div className="project-settings-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="project-settings-header">
          <div className="project-settings-title">
            <div className="icon-picker-wrapper">
              <button
                className="project-icon-btn"
                onClick={() => setShowIconPicker(!showIconPicker)}
                title="Change icon"
              >
                {selectedIcon}
              </button>
              {showIconPicker && (
                <div className="icon-picker-popover">
                  <div className="icon-picker-grid">
                    {PROJECT_ICONS.map((icon, idx) => (
                      <button
                        key={idx}
                        className={`icon-picker-option ${icon === selectedIcon ? 'selected' : ''}`}
                        onClick={() => {
                          setSelectedIcon(icon);
                          setShowIconPicker(false);
                        }}
                      >
                        {icon}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="project-name-input"
              placeholder="Project name"
            />
          </div>
          <button className="project-settings-close" onClick={onClose}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="project-settings-tabs">
          <button
            className={`project-settings-tab ${activeTab === 'instructions' ? 'active' : ''}`}
            onClick={() => setActiveTab('instructions')}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            Custom Instructions
          </button>
          <button
            className={`project-settings-tab ${activeTab === 'knowledge' ? 'active' : ''}`}
            onClick={() => setActiveTab('knowledge')}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            Project Knowledge
            {knowledgeBase.length > 0 && (
              <span className="tab-badge">{knowledgeBase.length}</span>
            )}
          </button>
        </div>

        {/* Content */}
        <div className="project-settings-content">
          {error && (
            <div className="project-settings-error">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              {error}
            </div>
          )}

          {activeTab === 'instructions' && (
            <div className="project-instructions-tab">
              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of this project"
                  className="project-input"
                />
              </div>

              <div className="form-group">
                <label>
                  Custom Instructions
                  <span className="label-hint">Applied to all conversations in this project</span>
                </label>
                <textarea
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="Enter custom instructions for the AI in this project. For example:&#10;&#10;- You are a helpful coding assistant&#10;- Always respond in a formal tone&#10;- Focus on Python and JavaScript"
                  className="project-textarea"
                  rows={10}
                />
                <div className="textarea-hint">
                  These instructions will be included in every conversation within this project.
                </div>
              </div>
            </div>
          )}

          {activeTab === 'knowledge' && (
            <div className="project-knowledge-tab">
              {/* Context Usage Indicator */}
              <div className="context-usage">
                <div className="context-usage-header">
                  <span className="context-usage-label">Context Usage</span>
                  <span className="context-usage-value">
                    {contextUsage.tokens.toLocaleString()} / {(contextUsage.limit / 1000).toFixed(0)}K tokens
                  </span>
                </div>
                <div className="context-usage-bar">
                  <div
                    className={`context-usage-fill ${contextUsage.percentage > 80 ? 'warning' : ''} ${contextUsage.percentage > 95 ? 'danger' : ''}`}
                    style={{ width: `${contextUsage.percentage}%` }}
                  />
                </div>
                <div className="context-usage-hint">
                  ~{Math.round(contextUsage.tokens / 400)} pages of context available
                </div>
              </div>

              {/* Drag-Drop Upload Zone */}
              <div
                ref={dropZoneRef}
                className={`knowledge-dropzone ${isDragging ? 'dragging' : ''}`}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                {uploading ? (
                  <div className="dropzone-uploading">
                    <span className="upload-spinner-large"></span>
                    <p>Uploading files...</p>
                  </div>
                ) : isDragging ? (
                  <div className="dropzone-active">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <p>Drop files here</p>
                  </div>
                ) : (
                  <div className="dropzone-idle">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="17 8 12 3 7 8" />
                      <line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                    <p>Drag & drop files here</p>
                    <span>or click to browse</span>
                    <div className="dropzone-formats">
                      PDF, TXT, MD, DOC, DOCX, CSV, JS, PY, TS, and more
                    </div>
                  </div>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".txt,.md,.pdf,.doc,.docx,.csv,.js,.jsx,.ts,.tsx,.py,.css,.html,.json,.yml,.yaml,.xml,.sql,.sh,.bash,.go,.rs,.rb,.php,.java,.c,.cpp,.h,.hpp"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </div>

              {/* File List */}
              {knowledgeBase.length > 0 && (
                <div className="knowledge-list">
                  <div className="knowledge-list-header">
                    <span>{knowledgeBase.length} file{knowledgeBase.length !== 1 ? 's' : ''}</span>
                  </div>
                  {knowledgeBase.map((file) => (
                    <div key={file.id} className="knowledge-file">
                      <span className="file-icon">{getFileIcon(file.file_type)}</span>
                      <div className="file-info">
                        <div className="file-name">{file.filename}</div>
                        <div className="file-meta">
                          {file.file_type} • {formatFileSize(file.size)}
                          {file.added_at && (
                            <> • Added {new Date(file.added_at).toLocaleDateString()}</>
                          )}
                        </div>
                      </div>
                      <button
                        className="file-remove-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRemoveFile(file.id);
                        }}
                        title="Remove file"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="project-settings-footer">
          <button className="project-delete-btn" onClick={handleDelete}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
            Delete Project
          </button>
          <div className="project-footer-actions">
            <button className="project-cancel-btn" onClick={onClose}>
              Cancel
            </button>
            <button
              className="project-save-btn"
              onClick={handleSave}
              disabled={saving || !name.trim()}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
