import { useState, useCallback } from 'react';
import '../styles/WorkflowRunner.css';

/**
 * Compact floating overlay that displays real-time workflow execution progress.
 * Sits at the bottom-center of the canvas and can collapse to a pill.
 *
 * @param {object}   props
 * @param {object}   props.workflow       - Workflow definition with `name` and `steps` array.
 * @param {number}   props.currentStep    - Zero-based index of the currently executing step.
 * @param {boolean}  props.running        - Whether the workflow is actively running.
 * @param {boolean}  props.waitingReview  - Whether the workflow is paused awaiting review.
 * @param {function} props.onApprove      - Called when the user approves the waiting step.
 * @param {function} props.onCancel       - Called when the user cancels the workflow.
 */
export default function WorkflowRunner({
  workflow,
  currentStep,
  running,
  waitingReview,
  onApprove,
  onCancel,
}) {
  const [minimized, setMinimized] = useState(false);

  const totalSteps = workflow?.steps?.length ?? 0;
  const stepLabel = totalSteps > 0 && currentStep >= 0 && currentStep < totalSteps
    ? workflow.steps[currentStep]?.name || `Step ${currentStep + 1}`
    : null;
  const displayStep = currentStep + 1;
  const progressPct = totalSteps > 0 ? (displayStep / totalSteps) * 100 : 0;

  const handleToggleMinimize = useCallback(() => {
    setMinimized((prev) => !prev);
  }, []);

  if (!workflow) return null;

  /* ---- Minimized pill ---- */
  if (minimized) {
    return (
      <button
        className="workflow-runner workflow-runner--pill"
        onClick={handleToggleMinimize}
        aria-label={`Expand workflow runner: ${workflow.name}`}
        type="button"
      >
        <span className={`workflow-runner__dot ${running ? 'workflow-runner__dot--running' : ''} ${waitingReview ? 'workflow-runner__dot--waiting' : ''}`} />
        <span className="workflow-runner__pill-label">
          {workflow.name} {displayStep}/{totalSteps}
        </span>
      </button>
    );
  }

  /* ---- Expanded bar ---- */
  return (
    <div
      className="workflow-runner"
      role="status"
      aria-live="polite"
      aria-label={`Workflow: ${workflow.name}, step ${displayStep} of ${totalSteps}`}
    >
      {/* Status dot */}
      <span
        className={`workflow-runner__dot ${running ? 'workflow-runner__dot--running' : ''} ${waitingReview ? 'workflow-runner__dot--waiting' : ''}`}
        aria-hidden="true"
      />

      {/* Workflow name */}
      <span className="workflow-runner__name">{workflow.name}</span>

      {/* Step progress */}
      <div className="workflow-runner__progress">
        <span className="workflow-runner__step-label">
          Step {displayStep}/{totalSteps}{stepLabel ? `: ${stepLabel}` : ''}
        </span>
        <div
          className="workflow-runner__bar"
          role="progressbar"
          aria-valuenow={displayStep}
          aria-valuemin={1}
          aria-valuemax={totalSteps}
        >
          <div
            className="workflow-runner__bar-fill"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Approve button -- visible only when waiting for review */}
      {waitingReview && (
        <button
          className="workflow-runner__btn workflow-runner__btn--approve"
          onClick={onApprove}
          type="button"
          aria-label="Approve step"
        >
          Approve
        </button>
      )}

      {/* Cancel button */}
      <button
        className="workflow-runner__btn workflow-runner__btn--cancel"
        onClick={onCancel}
        type="button"
        aria-label="Cancel workflow"
      >
        Cancel
      </button>

      {/* Minimize toggle */}
      <button
        className="workflow-runner__minimize"
        onClick={handleToggleMinimize}
        type="button"
        title="Minimize"
        aria-label="Minimize workflow runner"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
    </div>
  );
}
