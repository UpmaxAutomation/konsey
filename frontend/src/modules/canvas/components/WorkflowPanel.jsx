import { useState, useCallback } from 'react';
import WorkflowTemplateGallery from './WorkflowTemplateGallery.jsx';
import WorkflowBuilder from './WorkflowBuilder.jsx';
import '../styles/WorkflowPanel.css';

const STATUS_CONFIG = {
  draft:     { label: 'Draft',     className: 'workflow-panel__badge--draft' },
  running:   { label: 'Running',   className: 'workflow-panel__badge--running' },
  completed: { label: 'Completed', className: 'workflow-panel__badge--completed' },
  failed:    { label: 'Failed',    className: 'workflow-panel__badge--failed' },
  paused:    { label: 'Paused',    className: 'workflow-panel__badge--paused' },
  cancelled: { label: 'Cancelled', className: 'workflow-panel__badge--cancelled' },
};

function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  return (
    <span className={`workflow-panel__badge ${config.className}`}>
      {config.label}
    </span>
  );
}

function StepIcon({ status }) {
  if (status === 'completed') {
    return (
      <svg className="workflow-panel__step-icon workflow-panel__step-icon--completed" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <path d="M20 6L9 17l-5-5" />
      </svg>
    );
  }
  if (status === 'running') {
    return (
      <svg className="workflow-panel__step-icon workflow-panel__step-icon--running" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
      </svg>
    );
  }
  if (status === 'waiting') {
    return (
      <svg className="workflow-panel__step-icon workflow-panel__step-icon--waiting" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 6v6l4 2" />
      </svg>
    );
  }
  // pending (default)
  return (
    <svg className="workflow-panel__step-icon workflow-panel__step-icon--pending" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
    </svg>
  );
}

export default function WorkflowPanel({
  boardId,
  workflows = [],
  activeWorkflow,
  onSelect,
  onCreate,
  onDelete,
  onRun,
  onCancel,
  running,
  currentStep,
  waitingReview,
  onApprove,
  onClose,
  onShowTemplates,
  onShowBuilder,
}) {
  const [initialInput, setInitialInput] = useState('');
  const [showGallery, setShowGallery] = useState(false);
  const [showBuilder, setShowBuilder] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [savingBuilder, setSavingBuilder] = useState(false);

  const handleRun = useCallback(() => {
    if (!activeWorkflow || running) return;
    onRun?.(activeWorkflow.id, initialInput.trim());
  }, [activeWorkflow, running, onRun, initialInput]);

  const handleInputKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleRun();
    }
  }, [handleRun]);

  const handleDelete = useCallback((e, workflowId) => {
    e.stopPropagation();
    onDelete?.(workflowId);
  }, [onDelete]);

  const handleTemplateSelect = useCallback((template) => {
    setSelectedTemplate(template);
    setShowGallery(false);
    setShowBuilder(true);
  }, []);

  const handleBuilderSave = useCallback(async (data) => {
    setSavingBuilder(true);
    try {
      await onCreate?.(data);
      setShowBuilder(false);
      setSelectedTemplate(null);
    } catch (err) {
      console.error('Failed to save workflow:', err);
    } finally {
      setSavingBuilder(false);
    }
  }, [onCreate]);

  const handleBuilderCancel = useCallback(() => {
    setShowBuilder(false);
    setSelectedTemplate(null);
  }, []);

  const handleShowTemplates = useCallback(() => {
    setShowGallery(true);
  }, []);

  const handleShowBuilder = useCallback(() => {
    setSelectedTemplate(null);
    setShowBuilder(true);
  }, []);

  const stepCount = (wf) => {
    const count = wf.steps?.length || 0;
    return `${count} step${count !== 1 ? 's' : ''}`;
  };

  return (
    <div className="workflow-panel" role="complementary" aria-label="Workflow management panel">
      {/* Header */}
      <div className="workflow-panel__header">
        <h3 className="workflow-panel__title">Workflows</h3>
        <button
          className="workflow-panel__close"
          onClick={onClose}
          aria-label="Close workflows panel"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Action buttons */}
      <div className="workflow-panel__actions">
        <button
          className="workflow-panel__action-btn workflow-panel__action-btn--new"
          onClick={onCreate}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12h14" />
          </svg>
          New Workflow
        </button>
        <button
          className="workflow-panel__action-btn workflow-panel__action-btn--template"
          onClick={handleShowTemplates}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
          From Template
        </button>
      </div>

      {/* Builder inline view */}
      {showBuilder && (
        <div className="workflow-panel__builder-section">
          <WorkflowBuilder
            workflowName={selectedTemplate?.name || ''}
            initialSteps={
              selectedTemplate?.steps?.map((s) => ({
                step_type: s.step_type || 'ai_transform',
                name: s.name || '',
                prompt_template: s.prompt_template || '',
              })) || []
            }
            onSave={handleBuilderSave}
            onCancel={handleBuilderCancel}
            saving={savingBuilder}
          />
        </div>
      )}

      {/* Gallery modal */}
      {showGallery && (
        <WorkflowTemplateGallery
          onSelect={handleTemplateSelect}
          onClose={() => setShowGallery(false)}
        />
      )}

      {/* Workflow list / detail split */}
      {!showBuilder && activeWorkflow ? (
        <div className="workflow-panel__detail">
          {/* Back button */}
          <button
            className="workflow-panel__back"
            onClick={() => onSelect?.(null)}
            aria-label="Back to workflow list"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 18l-6-6 6-6" />
            </svg>
            All Workflows
          </button>

          {/* Active workflow header */}
          <div className="workflow-panel__detail-header">
            <span className="workflow-panel__detail-name">{activeWorkflow.name || 'Untitled'}</span>
            <StatusBadge status={activeWorkflow.status || 'draft'} />
          </div>

          {/* Step list */}
          <div className="workflow-panel__steps">
            <div className="workflow-panel__steps-label">Steps</div>
            {activeWorkflow.steps?.length > 0 ? (
              <ol className="workflow-panel__step-list">
                {activeWorkflow.steps.map((step, idx) => {
                  const isCurrentStep = running && currentStep === idx;
                  return (
                    <li
                      key={step.id || idx}
                      className={`workflow-panel__step${isCurrentStep ? ' workflow-panel__step--current' : ''}`}
                    >
                      <StepIcon status={step.status || 'pending'} />
                      <span className="workflow-panel__step-name">{step.name || `Step ${idx + 1}`}</span>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <div className="workflow-panel__empty">
                No steps defined.{' '}
                <button className="workflow-panel__link-btn" onClick={handleShowBuilder}>
                  Open builder
                </button>
              </div>
            )}
          </div>

          {/* Initial input */}
          {!running && activeWorkflow.status !== 'completed' && (
            <div className="workflow-panel__input-section">
              <label className="workflow-panel__input-label" htmlFor="workflow-initial-input">
                Initial Input
              </label>
              <textarea
                id="workflow-initial-input"
                className="workflow-panel__input"
                placeholder="Provide input for the first step..."
                value={initialInput}
                onChange={(e) => setInitialInput(e.target.value)}
                onKeyDown={handleInputKeyDown}
                rows={3}
              />
            </div>
          )}

          {/* Running progress */}
          {running && currentStep != null && activeWorkflow.steps?.length > 0 && (
            <div className="workflow-panel__progress">
              <div className="workflow-panel__progress-bar">
                <div
                  className="workflow-panel__progress-fill"
                  style={{ width: `${((currentStep + 1) / activeWorkflow.steps.length) * 100}%` }}
                />
              </div>
              <span className="workflow-panel__progress-text">
                Step {currentStep + 1} of {activeWorkflow.steps.length}
              </span>
            </div>
          )}

          {/* Action buttons */}
          <div className="workflow-panel__detail-actions">
            {!running && activeWorkflow.status !== 'completed' && (
              <button
                className="workflow-panel__run-btn"
                onClick={handleRun}
                disabled={running || !activeWorkflow.steps?.length}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="5,3 19,12 5,21" />
                </svg>
                Run
              </button>
            )}
            {running && (
              <button
                className="workflow-panel__cancel-btn"
                onClick={() => onCancel?.(activeWorkflow.id)}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="6" y="6" width="12" height="12" rx="1" />
                </svg>
                Cancel
              </button>
            )}
            {waitingReview && (
              <button
                className="workflow-panel__approve-btn"
                onClick={() => onApprove?.(activeWorkflow.id)}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
                Approve
              </button>
            )}
          </div>
        </div>
      ) : !showBuilder ? (
        <div className="workflow-panel__list">
          {workflows.length === 0 ? (
            <div className="workflow-panel__empty">
              No workflows yet. Create one or start from a template.
            </div>
          ) : (
            workflows.map((wf) => (
              <button
                key={wf.id}
                className="workflow-panel__item"
                onClick={() => onSelect?.(wf)}
              >
                <div className="workflow-panel__item-top">
                  <span className="workflow-panel__item-name">{wf.name || 'Untitled'}</span>
                  <StatusBadge status={wf.status || 'draft'} />
                </div>
                <div className="workflow-panel__item-bottom">
                  <span className="workflow-panel__item-steps">{stepCount(wf)}</span>
                  <button
                    className="workflow-panel__item-delete"
                    onClick={(e) => handleDelete(e, wf.id)}
                    aria-label={`Delete workflow ${wf.name || 'Untitled'}`}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
                    </svg>
                  </button>
                </div>
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
