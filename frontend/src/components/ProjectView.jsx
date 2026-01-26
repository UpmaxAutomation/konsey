/**
 * ProjectView - Dedicated project page like Claude AI
 * Shows project conversations on left, Memory/Instructions/Files on right
 */

import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import { useToast } from './Toast';
import ChatInterface from './ChatInterface';
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
    files: true,
  });
  const toast = useToast();
  const inputRef = useRef(null);

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
                <button
                  type="button"
                  className="project-conv-delete"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (window.confirm('Delete this conversation?')) {
                      onDeleteConversation(conv.id);
                    }
                  }}
                  title="Delete conversation"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
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

        {/* Files Section */}
        <div className="project-section">
          <button className="project-section-header" onClick={() => toggleSection('files')}>
            <span className="section-title">Files</span>
            <div className="section-header-right">
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
