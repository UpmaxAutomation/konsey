import { useState, useCallback } from 'react';
import '../styles/WorkflowBuilder.css';

const STEP_TYPES = [
  { value: 'council_query', label: 'Council Query' },
  { value: 'ai_transform', label: 'AI Transform' },
  { value: 'combine', label: 'Combine' },
  { value: 'human_review', label: 'Human Review' },
  { value: 'conditional', label: 'Conditional' },
];

const MODEL_OPTIONS = [
  { value: '', label: 'Default model' },
  { value: 'openai/gpt-4o', label: 'GPT-4o' },
  { value: 'openai/gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'anthropic/claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5' },
  { value: 'anthropic/claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
  { value: 'google/gemini-2.0-flash-001', label: 'Gemini 2.0 Flash' },
];

const DEFAULT_STEP = { step_type: 'ai_transform', name: '', prompt_template: '' };

export default function WorkflowBuilder({ initialSteps = [], onSave, onCancel, onSaveAsTemplate, workflowName = '', saving = false }) {
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
        model: s.model || undefined,
        config: s.config || undefined,
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
                    <span className="wf-builder__field-label">Model</span>
                    <select
                      value={step.model || ''}
                      onChange={(e) => updateStep(index, 'model', e.target.value)}
                      className="workflow-builder__model-select"
                    >
                      {MODEL_OPTIONS.map((m) => (
                        <option key={m.value} value={m.value}>{m.label}</option>
                      ))}
                    </select>
                  </label>
                )}
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
                {step.step_type === 'conditional' && (
                  <div className="wf-builder__conditional-config">
                    <span className="wf-builder__field-label">Branch targets</span>
                    <div className="wf-builder__conditional-row">
                      <label className="wf-builder__conditional-field">
                        <span>If TRUE, go to step #</span>
                        <input
                          type="number"
                          min={1}
                          max={steps.length}
                          value={step.config?.true_step_index != null ? step.config.true_step_index + 1 : ''}
                          onChange={(e) => {
                            const val = e.target.value ? parseInt(e.target.value, 10) - 1 : undefined;
                            updateStep(index, 'config', { ...(step.config || {}), true_step_index: val });
                          }}
                          placeholder="-"
                        />
                      </label>
                      <label className="wf-builder__conditional-field">
                        <span>If FALSE, go to step #</span>
                        <input
                          type="number"
                          min={1}
                          max={steps.length}
                          value={step.config?.false_step_index != null ? step.config.false_step_index + 1 : ''}
                          onChange={(e) => {
                            const val = e.target.value ? parseInt(e.target.value, 10) - 1 : undefined;
                            updateStep(index, 'config', { ...(step.config || {}), false_step_index: val });
                          }}
                          placeholder="-"
                        />
                      </label>
                    </div>
                    <span className="wf-builder__hint">
                      Leave empty to continue to the next step sequentially
                    </span>
                  </div>
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
      {onSaveAsTemplate && (
        <button
          type="button"
          className="wf-builder__btn wf-builder__template-btn"
          onClick={() => onSaveAsTemplate({
            name: name.trim(),
            steps: steps.filter((s) => s.name.trim()).map((s, i) => ({
              step_index: i,
              step_type: s.step_type,
              name: s.name,
              prompt_template: s.prompt_template,
              model: s.model || undefined,
              config: s.config || undefined,
            })),
          })}
          disabled={!name.trim() || steps.every((s) => !s.name.trim())}
        >
          Save as Template
        </button>
      )}
    </div>
  );
}
