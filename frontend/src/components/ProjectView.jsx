/**
 * ProjectView - Dedicated project page like Claude AI
 * Shows project conversations on left, Memory/Instructions/Files on right
 */

import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { useToast } from '../shared/components/Toast';
import { useRAGStatus, useEmbedAll } from '../api/queries/ragQueries.js';
import {
  useProjectLayers,
  useCreateLayer,
  useUpdateLayer,
  useDeleteLayer,
  useAssignDocuments,
} from '../api/queries/layerQueries.js';
import ChatInterface from '../modules/chat/components/ChatInterface';
import './ProjectView.css';

export default function ProjectView({
  project,
  conversations,
  currentConversationId,
  currentConversation,
  onSelectConversation,
  onNewConversation,
  onBack,
  onDeleteConversation,
  onProjectUpdate,
  onSendMessage,
  isLoading,
  onStopCouncil,
  onConversationUpdate,
  councilProgress,
}) {
  const [memory, setMemory] = useState(null);
  const [memoryStats, setMemoryStats] = useState(null);
  const [isEditingInstructions, setIsEditingInstructions] = useState(false);
  const [editedInstructions, setEditedInstructions] = useState('');
  const [newFact, setNewFact] = useState('');
  const [addingFact, setAddingFact] = useState(false);
  const [expandedSections, setExpandedSections] = useState({
    memory: true,
    instructions: true,
    layers: true,
    files: true,
  });
  const [newLayerForm, setNewLayerForm] = useState(false);
  const [editingLayerId, setEditingLayerId] = useState(null);
  const [newLayerData, setNewLayerData] = useState({
    name: '',
    description: '',
    color: 'blue',
    icon: 'book',
    persona_prompt: '',
    methodology_prompt: '',
  });
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const toast = useToast();
  const inputRef = useRef(null);
  const { data: ragStatus } = useRAGStatus(project?.id);
  const embedAllMutation = useEmbedAll();
  const { data: layers } = useProjectLayers(project?.id);
  const createLayerMutation = useCreateLayer();
  const updateLayerMutation = useUpdateLayer();
  const deleteLayerMutation = useDeleteLayer();
  const assignDocumentsMutation = useAssignDocuments();

  const LAYER_COLORS = ['blue', 'green', 'red', 'purple', 'orange', 'yellow', 'pink', 'teal'];
  const LAYER_COLOR_MAP = {
    blue: '#3b82f6',
    green: '#22c55e',
    red: '#ef4444',
    purple: '#a855f7',
    orange: '#f97316',
    yellow: '#eab308',
    pink: '#ec4899',
    teal: '#14b8a6',
  };

  // Load memory when project changes
  useEffect(() => {
    if (project?.id) {
      loadMemory();
      setEditedInstructions(project.system_prompt || '');
    }
  }, [project?.id]);

  const loadMemory = async () => {
    try {
      const [memoryData, statsData] = await Promise.all([
        api.getProjectMemory(project.id),
        api.getProjectMemoryStats(project.id),
      ]);
      setMemory(memoryData);
      setMemoryStats(statsData);
    } catch (err) {
      console.error('Failed to load memory:', err);
    }
  };

  const handleSaveInstructions = async () => {
    try {
      await api.updateProject(project.id, { system_prompt: editedInstructions });
      onProjectUpdate?.({ ...project, system_prompt: editedInstructions });
      setIsEditingInstructions(false);
      toast.success('Instructions saved');
    } catch (err) {
      console.error('Failed to save instructions:', err);
      toast.error('Failed to save instructions');
    }
  };

  const handleAddFact = async () => {
    if (!newFact.trim()) return;
    setAddingFact(true);
    try {
      await api.addProjectFact(project.id, newFact.trim());
      setNewFact('');
      loadMemory();
      toast.success('Memory added');
    } catch (err) {
      console.error('Failed to add fact:', err);
      toast.error('Failed to add memory');
    } finally {
      setAddingFact(false);
    }
  };

  const handleRemoveKnowledge = async (fileId) => {
    if (!confirm('Remove this file from the project?')) return;
    try {
      await api.removeKnowledgeFromProject(project.id, fileId);
      onProjectUpdate?.({
        ...project,
        knowledge_base: project.knowledge_base?.filter((f) => f.id !== fileId),
      });
      toast.success('File removed');
    } catch (err) {
      console.error('Failed to remove file:', err);
      toast.error('Failed to remove file');
    }
  };

  const handleEmbedAll = async () => {
    try {
      await embedAllMutation.mutateAsync({ projectId: project.id });
      toast.success('All documents embedded for RAG');
    } catch (err) {
      console.error('Failed to embed documents:', err);
      toast.error('Failed to embed documents');
    }
  };

  const handleCreateLayer = async () => {
    if (!newLayerData.name.trim()) return;
    try {
      await createLayerMutation.mutateAsync({
        project_id: project.id,
        name: newLayerData.name.trim(),
        description: newLayerData.description.trim() || null,
        color: newLayerData.color,
        icon: newLayerData.icon.trim() || 'book',
        persona_prompt: newLayerData.persona_prompt.trim() || null,
        methodology_prompt: newLayerData.methodology_prompt.trim() || null,
      });
      setNewLayerForm(false);
      setNewLayerData({ name: '', description: '', color: 'blue', icon: 'book', persona_prompt: '', methodology_prompt: '' });
      toast.success('Layer created');
    } catch (err) {
      console.error('Failed to create layer:', err);
      toast.error('Failed to create layer');
    }
  };

  const handleUpdateLayer = async (layerId, updates) => {
    try {
      await updateLayerMutation.mutateAsync({ layerId, updates });
      setEditingLayerId(null);
      toast.success('Layer updated');
    } catch (err) {
      console.error('Failed to update layer:', err);
      toast.error('Failed to update layer');
    }
  };

  const handleDeleteLayer = async (layerId) => {
    if (!confirm('Delete this knowledge layer?')) return;
    try {
      await deleteLayerMutation.mutateAsync(layerId);
      toast.success('Layer deleted');
    } catch (err) {
      console.error('Failed to delete layer:', err);
      toast.error('Failed to delete layer');
    }
  };

  const handleAssignFileToLayer = async (fileId, layerId) => {
    try {
      await assignDocumentsMutation.mutateAsync({
        layerId,
        documentIds: [fileId],
        projectId: project.id,
      });
      toast.success('File assigned to layer');
    } catch (err) {
      console.error('Failed to assign file:', err);
      toast.error('Failed to assign file to layer');
    }
  };

  const getLayerDocumentCount = (layerId) => {
    if (!ragStatus?.documents) return 0;
    return Object.values(ragStatus.documents).filter(
      (doc) => doc.layer_id === layerId
    ).length;
  };

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  const formatTimeAgo = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
    return `${Math.floor(diffDays / 365)} years ago`;
  };

  const calculateCapacity = () => {
    const totalChars = (project.knowledge_base || []).reduce(
      (acc, file) => acc + (file.size || 0),
      0
    );
    const maxChars = 200000 * 4; // 200K tokens * ~4 chars per token
    const percentage = Math.min((totalChars / maxChars) * 100, 100);
    return Math.round(percentage);
  };

  const getFileIcon = (fileType) => {
    switch (fileType) {
      case 'code': return '💻';
      case 'document': return '📄';
      case 'pdf': return '📕';
      case 'html': return '🌐';
      default: return '📝';
    }
  };

  const getFileExtension = (filename) => {
    const ext = filename?.split('.').pop()?.toUpperCase();
    return ext || 'TEXT';
  };

  if (!project) return null;

  return (
    <div className="project-view">
      {/* Left Side - Sidebar with conversations */}
      <div className="project-view-sidebar-left">
        {/* Header */}
        <div className="project-view-header">
          <button className="project-back-btn" onClick={onBack}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
            All projects
          </button>
        </div>

        {/* Project Title */}
        <div className="project-sidebar-title">
          <span className="project-view-icon">{project.icon || '📁'}</span>
          <span>{project.name}</span>
        </div>

        {/* New Chat Button */}
        <button className="project-new-chat-btn" onClick={onNewConversation}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          New chat
        </button>

        {/* Conversations List */}
        <div className="project-conversations-list">
          {conversations.length === 0 ? (
            <div className="project-empty-state">
              <p>No conversations yet</p>
            </div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                className={`project-conv-item ${conv.id === currentConversationId ? 'active' : ''}`}
                onClick={() => onSelectConversation(conv.id)}
              >
                <div className="project-conv-title">
                  {conv.title || 'Untitled'}
                </div>
                <div className="project-conv-meta">
                  {formatTimeAgo(conv.updated_at || conv.created_at)}
                </div>
                {confirmDeleteId === conv.id ? (
                  <span className="project-conv-confirm" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="project-conv-confirm-yes"
                      onClick={(e) => { e.stopPropagation(); onDeleteConversation(conv.id); setConfirmDeleteId(null); }}
                    >
                      Delete
                    </button>
                    <button
                      type="button"
                      className="project-conv-confirm-no"
                      onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(null); }}
                    >
                      Cancel
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="project-conv-delete"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setConfirmDeleteId(conv.id);
                    }}
                    title="Delete conversation"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Middle - Chat Interface */}
      <div className="project-view-main">
        <ChatInterface
          conversation={currentConversation}
          currentConversationId={currentConversationId}
          onSendMessage={onSendMessage}
          isLoading={isLoading}
          onStopCouncil={onStopCouncil}
          onConversationUpdate={onConversationUpdate}
          councilProgress={councilProgress}
          currentProjectId={project.id}
        />
      </div>

      {/* Right Side - Memory, Instructions, Files */}
      <div className="project-view-sidebar">
        {/* Memory Section */}
        <div className="project-section">
          <button className="project-section-header" onClick={() => toggleSection('memory')}>
            <span className="section-title">Memory</span>
            <div className="section-header-right">
              <span className="section-visibility">Only you</span>
              <svg
                className={`section-chevron ${expandedSections.memory ? 'expanded' : ''}`}
                width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
              >
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </div>
          </button>
          {expandedSections.memory && (
            <div className="project-section-content">
              {memory?.context ? (
                <div className="memory-content">
                  <p>{memory.context}</p>
                  <span className="memory-updated">
                    Last updated {memoryStats?.last_updated ? formatTimeAgo(memoryStats.last_updated) : 'recently'}
                  </span>
                </div>
              ) : (
                <p className="memory-empty">No memory stored yet</p>
              )}
              <div className="memory-add-row">
                <input
                  type="text"
                  value={newFact}
                  onChange={(e) => setNewFact(e.target.value)}
                  placeholder="Add a fact to remember..."
                  onKeyDown={(e) => e.key === 'Enter' && handleAddFact()}
                />
                <button onClick={handleAddFact} disabled={addingFact || !newFact.trim()}>
                  Add
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Instructions Section */}
        <div className="project-section">
          <button className="project-section-header" onClick={() => toggleSection('instructions')}>
            <span className="section-title">Instructions</span>
            <div className="section-header-right">
              <button
                className="section-add-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsEditingInstructions(true);
                  setExpandedSections((prev) => ({ ...prev, instructions: true }));
                }}
                title="Edit instructions"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
              </button>
            </div>
          </button>
          {expandedSections.instructions && (
            <div className="project-section-content">
              {isEditingInstructions ? (
                <div className="instructions-edit">
                  <textarea
                    value={editedInstructions}
                    onChange={(e) => setEditedInstructions(e.target.value)}
                    placeholder="Add instructions to tailor Claude's responses"
                    rows={4}
                    autoFocus
                  />
                  <div className="instructions-edit-actions">
                    <button className="btn-cancel" onClick={() => {
                      setIsEditingInstructions(false);
                      setEditedInstructions(project.system_prompt || '');
                    }}>
                      Cancel
                    </button>
                    <button className="btn-save" onClick={handleSaveInstructions}>
                      Save
                    </button>
                  </div>
                </div>
              ) : project.system_prompt ? (
                <div className="instructions-content" onClick={() => setIsEditingInstructions(true)}>
                  <p>{project.system_prompt}</p>
                </div>
              ) : (
                <p className="instructions-empty" onClick={() => setIsEditingInstructions(true)}>
                  Add instructions to tailor Claude's responses
                </p>
              )}
            </div>
          )}
        </div>

        {/* Knowledge Layers Section */}
        <div className="project-section">
          <button className="project-section-header" onClick={() => toggleSection('layers')}>
            <span className="section-title">Knowledge Layers</span>
            <div className="section-header-right">
              <button
                className="section-add-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  setNewLayerForm(true);
                  setExpandedSections((prev) => ({ ...prev, layers: true }));
                }}
                title="Add layer"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
              </button>
              <svg
                className={`section-chevron ${expandedSections.layers ? 'expanded' : ''}`}
                width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
              >
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </div>
          </button>
          {expandedSections.layers && (
            <div className="project-section-content">
              {/* Add Layer Form */}
              {newLayerForm && (
                <div className="layer-form">
                  <input
                    type="text"
                    className="layer-form-input"
                    value={newLayerData.name}
                    onChange={(e) => setNewLayerData((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder="Layer name..."
                    autoFocus
                  />
                  <textarea
                    className="layer-form-textarea"
                    value={newLayerData.description}
                    onChange={(e) => setNewLayerData((prev) => ({ ...prev, description: e.target.value }))}
                    placeholder="Description (optional) - What is this layer about?"
                    rows={2}
                  />
                  <div className="layer-form-row">
                    <input
                      type="text"
                      className="layer-form-input layer-form-icon-input"
                      value={newLayerData.icon}
                      onChange={(e) => setNewLayerData((prev) => ({ ...prev, icon: e.target.value }))}
                      placeholder="Icon (e.g. book, legal, code)"
                    />
                  </div>
                  <div className="layer-color-picker">
                    {LAYER_COLORS.map((color) => (
                      <button
                        key={color}
                        className={`layer-color-option ${newLayerData.color === color ? 'selected' : ''}`}
                        style={{ backgroundColor: LAYER_COLOR_MAP[color] }}
                        onClick={() => setNewLayerData((prev) => ({ ...prev, color }))}
                        title={color}
                        type="button"
                      />
                    ))}
                  </div>
                  <textarea
                    className="layer-form-textarea"
                    value={newLayerData.persona_prompt}
                    onChange={(e) => setNewLayerData((prev) => ({ ...prev, persona_prompt: e.target.value }))}
                    placeholder="Persona prompt (optional) - How should the AI behave with this layer?"
                    rows={2}
                  />
                  <textarea
                    className="layer-form-textarea"
                    value={newLayerData.methodology_prompt}
                    onChange={(e) => setNewLayerData((prev) => ({ ...prev, methodology_prompt: e.target.value }))}
                    placeholder="Methodology prompt (optional) - What approach should be used?"
                    rows={2}
                  />
                  <div className="layer-form-actions">
                    <button
                      className="btn-cancel"
                      onClick={() => {
                        setNewLayerForm(false);
                        setNewLayerData({ name: '', description: '', color: 'blue', icon: 'book', persona_prompt: '', methodology_prompt: '' });
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      className="btn-save"
                      onClick={handleCreateLayer}
                      disabled={!newLayerData.name.trim() || createLayerMutation.isPending}
                    >
                      {createLayerMutation.isPending ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </div>
              )}

              {/* Layer List */}
              {layers?.length > 0 ? (
                <div className="layer-list">
                  {layers.map((layer) => (
                    <div key={layer.id} className="layer-item">
                      <div
                        className="layer-item-header"
                        onClick={() => setEditingLayerId(editingLayerId === layer.id ? null : layer.id)}
                      >
                        <span
                          className="layer-color-dot"
                          style={{ backgroundColor: LAYER_COLOR_MAP[layer.color] || layer.color }}
                        />
                        <span className="layer-item-name">{layer.name}</span>
                        <span className="layer-doc-count">{getLayerDocumentCount(layer.id)}</span>
                        <button
                          className="layer-toggle-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleUpdateLayer(layer.id, { is_active: !layer.is_active });
                          }}
                          title={layer.is_active ? 'Deactivate layer' : 'Activate layer'}
                        >
                          {layer.is_active !== false ? (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                              <circle cx="12" cy="12" r="3"/>
                            </svg>
                          ) : (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth="2">
                              <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                              <line x1="1" y1="1" x2="23" y2="23"/>
                            </svg>
                          )}
                        </button>
                        <button
                          className="layer-delete-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteLayer(layer.id);
                          }}
                          title="Delete layer"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 6L6 18M6 6l12 12"/>
                          </svg>
                        </button>
                      </div>
                      {editingLayerId === layer.id && (
                        <div className="layer-item-details">
                          <input
                            type="text"
                            className="layer-form-input"
                            defaultValue={layer.name}
                            onBlur={(e) => {
                              if (e.target.value.trim() && e.target.value !== layer.name) {
                                handleUpdateLayer(layer.id, { name: e.target.value.trim() });
                              }
                            }}
                            placeholder="Layer name"
                          />
                          <textarea
                            className="layer-form-textarea"
                            defaultValue={layer.description || ''}
                            onBlur={(e) => {
                              if (e.target.value !== (layer.description || '')) {
                                handleUpdateLayer(layer.id, { description: e.target.value.trim() || null });
                              }
                            }}
                            placeholder="Description..."
                            rows={2}
                          />
                          <div className="layer-form-row">
                            <input
                              type="text"
                              className="layer-form-input layer-form-icon-input"
                              defaultValue={layer.icon || 'book'}
                              onBlur={(e) => {
                                if (e.target.value.trim() !== (layer.icon || 'book')) {
                                  handleUpdateLayer(layer.id, { icon: e.target.value.trim() || 'book' });
                                }
                              }}
                              placeholder="Icon (e.g. book, legal, code)"
                            />
                          </div>
                          <div className="layer-color-picker">
                            {LAYER_COLORS.map((color) => (
                              <button
                                key={color}
                                className={`layer-color-option ${layer.color === color ? 'selected' : ''}`}
                                style={{ backgroundColor: LAYER_COLOR_MAP[color] }}
                                onClick={() => handleUpdateLayer(layer.id, { color })}
                                title={color}
                                type="button"
                              />
                            ))}
                          </div>
                          <textarea
                            className="layer-form-textarea"
                            defaultValue={layer.persona_prompt || ''}
                            onBlur={(e) => {
                              if (e.target.value !== (layer.persona_prompt || '')) {
                                handleUpdateLayer(layer.id, { persona_prompt: e.target.value.trim() || null });
                              }
                            }}
                            placeholder="Persona prompt..."
                            rows={2}
                          />
                          <textarea
                            className="layer-form-textarea"
                            defaultValue={layer.methodology_prompt || ''}
                            onBlur={(e) => {
                              if (e.target.value !== (layer.methodology_prompt || '')) {
                                handleUpdateLayer(layer.id, { methodology_prompt: e.target.value.trim() || null });
                              }
                            }}
                            placeholder="Methodology prompt..."
                            rows={2}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : !newLayerForm ? (
                <p className="layers-empty">No knowledge layers yet</p>
              ) : null}
            </div>
          )}
        </div>

        {/* Files Section */}
        <div className="project-section">
          <button className="project-section-header" onClick={() => toggleSection('files')}>
            <span className="section-title">Files</span>
            <div className="section-header-right">
              <button
                className="section-add-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  handleEmbedAll();
                }}
                title="Embed all files for RAG"
                disabled={embedAllMutation.isPending || !project.knowledge_base?.length}
              >
                {embedAllMutation.isPending ? (
                  <span className="embed-spinner">...</span>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="M21 21l-4.35-4.35"/>
                  </svg>
                )}
              </button>
              <button
                className="section-add-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  // TODO: Open file upload dialog
                }}
                title="Add files"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
              </button>
            </div>
          </button>
          {expandedSections.files && (
            <div className="project-section-content">
              {/* Capacity indicator */}
              <div className="files-capacity">
                <div className="capacity-bar">
                  <div className="capacity-fill" style={{ width: `${calculateCapacity()}%` }} />
                </div>
                <span className="capacity-text">{calculateCapacity()}% of project capacity used</span>
              </div>

              {/* Files grid */}
              {project.knowledge_base?.length > 0 ? (
                <div className="files-grid">
                  {project.knowledge_base.map((file) => (
                    <div key={file.id} className="file-card">
                      <button
                        className="file-card-remove"
                        onClick={() => handleRemoveKnowledge(file.id)}
                        title="Remove file"
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M18 6L6 18M6 6l12 12"/>
                        </svg>
                      </button>
                      <div className="file-card-name">{file.filename}</div>
                      <div className="file-card-meta">{file.lines || Math.ceil((file.size || 0) / 50)} lines</div>
                      <div className="file-card-type">{getFileExtension(file.filename)}</div>
                      {ragStatus?.documents?.[file.id] ? (
                        <div className="file-card-embedded" title="Embedded for RAG">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#22c55e" strokeWidth="2">
                            <path d="M20 6L9 17l-5-5"/>
                          </svg>
                        </div>
                      ) : (
                        <div className="file-card-not-embedded" title="Not embedded" style={{opacity: 0.3}}>
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="11" cy="11" r="8"/>
                            <path d="M21 21l-4.35-4.35"/>
                          </svg>
                        </div>
                      )}
                      {layers?.length > 0 && (
                        <select
                          className="file-card-layer-select"
                          value={ragStatus?.documents?.[file.id]?.layer_id || ''}
                          onChange={(e) => {
                            const layerId = e.target.value;
                            if (layerId) handleAssignFileToLayer(file.id, layerId);
                          }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <option value="">No layer</option>
                          {layers.map((layer) => (
                            <option key={layer.id} value={layer.id}>
                              {layer.name}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="files-empty">No files added yet</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
