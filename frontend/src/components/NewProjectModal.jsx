/**
 * NewProjectModal - Claude-style modal for creating new projects
 * Features: name input, description, icon picker, custom instructions
 */

import { useState, useEffect, useRef } from 'react';
import './NewProjectModal.css';

// Available icons for projects
const PROJECT_ICONS = [
  '📁', '💼', '🔬', '💻', '📚', '🎯', '🚀', '🔧', '📊', '🎨',
  '📝', '🧪', '🎮', '🌐', '🔐', '📈', '🎵', '📸', '🏠', '💡',
  '🤖', '⚡', '🔥', '💎', '🌟', '🎪', '🧠', '📱', '🛠️', '🎁',
];

// Preset project templates
const PROJECT_TEMPLATES = [
  { name: 'Blank Project', icon: '📁', description: '', instructions: '' },
  { name: 'Code Review', icon: '💻', description: 'Code review and development', instructions: 'You are an expert code reviewer. Focus on code quality, best practices, security vulnerabilities, and performance optimizations. Provide actionable suggestions.' },
  { name: 'Research', icon: '🔬', description: 'Research and analysis', instructions: 'You are a research assistant. Provide thorough, well-cited analysis. Consider multiple perspectives and clearly distinguish facts from opinions.' },
  { name: 'Writing', icon: '📝', description: 'Writing and content creation', instructions: 'You are a skilled writer. Focus on clarity, engagement, and proper structure. Match the requested tone and style.' },
  { name: 'Data Analysis', icon: '📊', description: 'Data analysis and visualization', instructions: 'You are a data analyst. Focus on extracting insights, identifying patterns, and presenting findings clearly. Suggest appropriate visualizations.' },
];

export default function NewProjectModal({ isOpen, onClose, onCreateProject }) {
  const [step, setStep] = useState(1); // 1: template, 2: details
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedIcon, setSelectedIcon] = useState('📁');
  const [instructions, setInstructions] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState(null);
  const nameInputRef = useRef(null);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setName('');
      setDescription('');
      setSelectedIcon('📁');
      setInstructions('');
      setError(null);
    }
  }, [isOpen]);

  // Focus name input when entering step 2
  useEffect(() => {
    if (step === 2 && nameInputRef.current) {
      setTimeout(() => nameInputRef.current?.focus(), 100);
    }
  }, [step]);

  // Handle template selection
  const handleTemplateSelect = (template) => {
    setName(template.name === 'Blank Project' ? '' : template.name);
    setDescription(template.description);
    setSelectedIcon(template.icon);
    setInstructions(template.instructions);
    setStep(2);
  };

  // Handle project creation
  const handleCreate = async () => {
    if (!name.trim()) {
      setError('Project name is required');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      await onCreateProject({
        name: name.trim(),
        description: description.trim(),
        icon: selectedIcon,
        system_prompt: instructions.trim(),
      });
      onClose();
    } catch (err) {
      console.error('Failed to create project:', err);
      setError('Failed to create project. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      if (step === 2) {
        setStep(1);
      } else {
        onClose();
      }
    }
    if (e.key === 'Enter' && e.metaKey && step === 2) {
      handleCreate();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="new-project-overlay" onClick={onClose} onKeyDown={handleKeyDown}>
      <div className="new-project-modal" role="dialog" aria-modal="true" aria-label="Create a project" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="new-project-header">
          <div className="new-project-header-content">
            {step === 2 && (
              <button className="new-project-back" onClick={() => setStep(1)}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M19 12H5M12 19l-7-7 7-7"/>
                </svg>
              </button>
            )}
            <h2>{step === 1 ? 'Create a Project' : 'Project Details'}</h2>
          </div>
          <button className="new-project-close" onClick={onClose}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Step 1: Template Selection */}
        {step === 1 && (
          <div className="new-project-templates">
            <p className="new-project-subtitle">Start with a template or create a blank project</p>
            <div className="template-grid">
              {PROJECT_TEMPLATES.map((template, index) => (
                <button
                  key={index}
                  className="template-card"
                  onClick={() => handleTemplateSelect(template)}
                >
                  <span className="template-icon">{template.icon}</span>
                  <span className="template-name">{template.name}</span>
                  {template.description && (
                    <span className="template-desc">{template.description}</span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Project Details */}
        {step === 2 && (
          <div className="new-project-details">
            {error && (
              <div className="new-project-error">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 8v4M12 16h.01"/>
                </svg>
                {error}
              </div>
            )}

            {/* Icon and Name */}
            <div className="new-project-name-row">
              <div className="icon-picker-trigger">
                <button className="selected-icon-btn" title="Choose icon">
                  {selectedIcon}
                </button>
                <div className="icon-picker-dropdown">
                  <div className="icon-grid">
                    {PROJECT_ICONS.map((icon, index) => (
                      <button
                        key={index}
                        className={`icon-option ${icon === selectedIcon ? 'selected' : ''}`}
                        onClick={() => setSelectedIcon(icon)}
                      >
                        {icon}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <input
                ref={nameInputRef}
                type="text"
                className="new-project-name-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Project name"
                maxLength={50}
              />
            </div>

            {/* Description */}
            <div className="form-group">
              <label>Description <span className="optional">(optional)</span></label>
              <input
                type="text"
                className="new-project-input"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of this project"
                maxLength={200}
              />
            </div>

            {/* Custom Instructions */}
            <div className="form-group">
              <label>
                Custom Instructions
                <span className="optional">(optional)</span>
              </label>
              <textarea
                className="new-project-textarea"
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Enter instructions that will be applied to all conversations in this project. For example:&#10;&#10;• You are an expert in...&#10;• Always respond in a formal tone&#10;• Focus on Python and TypeScript"
                rows={6}
              />
              <div className="textarea-hint">
                These instructions will be included in every conversation within this project.
              </div>
            </div>

            {/* Footer */}
            <div className="new-project-footer">
              <div className="footer-hint">
                <kbd>⌘</kbd> + <kbd>Enter</kbd> to create
              </div>
              <div className="footer-actions">
                <button className="btn-cancel" onClick={() => setStep(1)}>
                  Back
                </button>
                <button
                  className="btn-create"
                  onClick={handleCreate}
                  disabled={isCreating || !name.trim()}
                >
                  {isCreating ? (
                    <>
                      <span className="spinner"></span>
                      Creating...
                    </>
                  ) : (
                    'Create Project'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
