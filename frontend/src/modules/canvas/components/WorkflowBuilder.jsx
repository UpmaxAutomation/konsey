import { useState, useCallback } from 'react';
import '../styles/WorkflowBuilder.css';

const STEP_TYPES = [
  { value: 'council_query', label: 'Council Query' },
  { value: 'ai_transform', label: 'AI Transform' },
  { value: 'combine', label: 'Combine' },
  { value: 'human_review', label: 'Human Review' },
];

const DEFAULT_STEP = { step_type: 'ai_transform', name: '', prompt_template: '' };

export default function WorkflowBuilder({ initialSteps = [], onSave, onCancel, workflowName = '', saving = false }) {
  const [name, setName] = useState(workflowName);
  const [steps, setSteps] = useState(
    initialSteps.length > 0 ? initialSteps : [{ ...DEFAULT_STEP }]
  );
  const [expandedStep, setExpandedStep] = useState(0);

  const addStep = useCallback(() => {
    setSteps((prev) => [...prev, { ...DEFAULT_STEP }]);
    setExpandedStep(steps.length);
  }, [steps.length]);

  const removeStep = useCallback((index) => {
    setSteps((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateStep = useCallback((index, field, value) => {
    setSteps((prev) => prev.map((s, i) => i === index ? { ...s, [field]: value } : s));
  }, []);

  const moveStep = useCallback((index, direction) => {
    setSteps((prev) => {
      const newSteps = [...prev];
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= newSteps.length) return prev;
      [newSteps[index], newSteps[targetIndex]] = [newSteps[targetIndex], newSteps[index]];
      return newSteps;
    });
    setExpandedStep((prev) => prev + direction);
  }, []);

  const handleSave = () => {
    if (!name.trim()) return;
    const validSteps = steps.filter((s) => s.name.trim());
    if (validSteps.length === 0) return;
    onSave({
      name: name.trim(),
      steps: validSteps.map((s, i) => ({
        step_index: i,
        step_type: s.step_type,
        name: s.name,
        prompt_template: s.prompt_template,
      })),
    });
  };

  return (
    <div className="wf-builder">
      <div className="wf-builder__name-row">
        <label className="wf-builder__name-label" htmlFor="wf-builder-name">
          Workflow Name
        </label>
        <input
          id="wf-builder-name"
          className="wf-builder__name-input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Workflow name..."
        />
      </div>

      <div className="wf-builder__steps">
        {steps.map((step, index) => (
          <div
            key={index}
            className={`wf-builder__step ${expandedStep === index ? 'wf-builder__step--expanded' : ''}`}
          >
            <div
              className="wf-builder__step-header"
              onClick={() => setExpandedStep(expandedStep === index ? -1 : index)}
              role="button"
              tabIndex={0}
              aria-expanded={expandedStep === index}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setExpandedStep(expandedStep === index ? -1 : index);
                }
              }}
            >
              <span className="wf-builder__step-number">{index + 1}</span>
              <span className="wf-builder__step-name">{step.name || 'Untitled step'}</span>
              <span className="wf-builder__step-type-badge">{step.step_type}</span>
              <div className="wf-builder__step-actions">
                <button
                  onClick={(e) => { e.stopPropagation(); moveStep(index, -1); }}
                  disabled={index === 0}
                  title="Move up"
                  aria-label={`Move step ${index + 1} up`}
                >
                  &uarr;
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); moveStep(index, 1); }}
                  disabled={index === steps.length - 1}
                  title="Move down"
                  aria-label={`Move step ${index + 1} down`}
                >
                  &darr;
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); removeStep(index); }}
                  disabled={steps.length <= 1}
                  title="Remove"
                  aria-label={`Remove step ${index + 1}`}
                >
                  &times;
                </button>
              </div>
            </div>
            {expandedStep === index && (
              <div className="wf-builder__step-body">
                <label className="wf-builder__field">
                  <span className="wf-builder__field-label">Type</span>
                  <select
                    value={step.step_type}
                    onChange={(e) => updateStep(index, 'step_type', e.target.value)}
                  >
                    {STEP_TYPES.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </label>
                <label className="wf-builder__field">
                  <span className="wf-builder__field-label">Name</span>
                  <input
                    value={step.name}
                    onChange={(e) => updateStep(index, 'name', e.target.value)}
                    placeholder="Step name..."
                  />
                </label>
                {step.step_type !== 'human_review' && (
                  <label className="wf-builder__field">
                    <span className="wf-builder__field-label">Prompt template</span>
                    <textarea
                      value={step.prompt_template}
                      onChange={(e) => updateStep(index, 'prompt_template', e.target.value)}
                      placeholder="Use {{input}} for previous step output..."
                      rows={4}
                    />
                    <span className="wf-builder__hint">
                      Use {"{{input}}"} to reference output from the previous step
                    </span>
                  </label>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <button className="wf-builder__add-step" onClick={addStep}>+ Add Step</button>

      <div className="wf-builder__footer">
        <button className="wf-builder__btn wf-builder__btn--cancel" onClick={onCancel}>
          Cancel
        </button>
        <button
          className="wf-builder__btn wf-builder__btn--save"
          onClick={handleSave}
          disabled={saving || !name.trim() || steps.every((s) => !s.name.trim())}
        >
          {saving ? 'Saving...' : 'Save Workflow'}
        </button>
      </div>
    </div>
  );
}
