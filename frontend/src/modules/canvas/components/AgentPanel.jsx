import { useState, useRef, useEffect } from 'react';
import '../styles/AgentPanel.css';

const MODEL_OPTIONS = [
  { value: 'openai/gpt-4o', label: 'GPT-4o' },
  { value: 'anthropic/claude-sonnet-4', label: 'Claude Sonnet 4' },
  { value: 'google/gemini-2.0-flash-001', label: 'Gemini 2.0 Flash' },
];

const TOOL_COLORS = {
  create_card: '#6366f1',
  update_card: '#8b5cf6',
  delete_card: '#ef4444',
  move_card: '#f59e0b',
  create_edge: '#3b82f6',
  run_council: '#10b981',
  search_cards: '#06b6d4',
  create_section: '#ec4899',
};

function getToolColor(toolName) {
  if (!toolName) return '#6366f1';
  const key = Object.keys(TOOL_COLORS).find((k) => toolName.includes(k));
  return key ? TOOL_COLORS[key] : '#6366f1';
}

function ThoughtEntry({ entry }) {
  return (
    <div className="agent-panel__thought" role="listitem">
      <div className="agent-panel__thought-header">
        <span className="agent-panel__thought-iter">#{entry.iteration}</span>
        {entry.tool && (
          <span
            className="agent-panel__tool-badge"
            style={{ background: getToolColor(entry.tool) }}
          >
            {entry.tool}
          </span>
        )}
      </div>
      {entry.thought && (
        <p className="agent-panel__thought-text">{entry.thought}</p>
      )}
      {entry.result && (
        <pre className="agent-panel__thought-result">{entry.result}</pre>
      )}
    </div>
  );
}

export default function AgentPanel({
  boardId,
  running,
  paused,
  thoughts,
  iteration,
  error,
  onStart,
  onPause,
  onResume,
  onCancel,
  onClose,
}) {
  const [goal, setGoal] = useState('');
  const [model, setModel] = useState(MODEL_OPTIONS[0].value);
  const thoughtsEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Focus the goal textarea on mount
  useEffect(() => {
    if (textareaRef.current && !running) {
      textareaRef.current.focus();
    }
  }, []);

  // Auto-scroll to the bottom of the thought log when new entries arrive
  useEffect(() => {
    if (thoughtsEndRef.current) {
      thoughtsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thoughts]);

  const handleStart = () => {
    if (!goal.trim() || running) return;
    onStart?.({ goal: goal.trim(), model, boardId });
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleStart();
    }
    if (e.key === 'Escape') {
      onClose?.();
    }
  };

  const maxIterations = 20;
  const thoughtEntries = thoughts || [];
  const canStart = goal.trim().length > 0 && !running;

  return (
    <div className="agent-panel" role="complementary" aria-label="Canvas Agent">
      {/* Header */}
      <div className="agent-panel__header">
        <div className="agent-panel__header-left">
          <svg
            className="agent-panel__header-icon"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2z" />
            <path d="M12 6v6l4 2" />
          </svg>
          <h3 className="agent-panel__title">Canvas Agent</h3>
          {running && (
            <span className="agent-panel__status-dot" aria-label={paused ? 'Paused' : 'Running'} />
          )}
        </div>
        <button
          className="agent-panel__close"
          onClick={onClose}
          title="Close agent panel"
          aria-label="Close agent panel"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Goal Input */}
      <div className="agent-panel__config">
        <label className="agent-panel__label" htmlFor="agent-goal">
          Goal
        </label>
        <textarea
          ref={textareaRef}
          id="agent-goal"
          className="agent-panel__textarea"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe what you want the agent to build on this board..."
          rows={3}
          disabled={running}
        />

        <label className="agent-panel__label" htmlFor="agent-model">
          Model
        </label>
        <select
          id="agent-model"
          className="agent-panel__select"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          disabled={running}
        >
          {MODEL_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Start / Controls */}
        <div className="agent-panel__actions">
          {!running ? (
            <button
              className="agent-panel__start-btn"
              onClick={handleStart}
              disabled={!canStart}
              aria-label="Run agent"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              Run Agent
            </button>
          ) : (
            <div className="agent-panel__running-controls">
              {paused ? (
                <button
                  className="agent-panel__control-btn agent-panel__control-btn--resume"
                  onClick={onResume}
                  aria-label="Resume agent"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  Resume
                </button>
              ) : (
                <button
                  className="agent-panel__control-btn agent-panel__control-btn--pause"
                  onClick={onPause}
                  aria-label="Pause agent"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="6" y="4" width="4" height="16" />
                    <rect x="14" y="4" width="4" height="16" />
                  </svg>
                  Pause
                </button>
              )}
              <button
                className="agent-panel__control-btn agent-panel__control-btn--stop"
                onClick={onCancel}
                aria-label="Stop agent"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                </svg>
                Stop
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Iteration Counter */}
      {running && (
        <div className="agent-panel__iteration" role="status" aria-live="polite">
          <div className="agent-panel__iteration-bar">
            <div
              className="agent-panel__iteration-fill"
              style={{ width: `${Math.min(((iteration || 0) / maxIterations) * 100, 100)}%` }}
            />
          </div>
          <span className="agent-panel__iteration-label">
            Iteration {iteration || 0}/{maxIterations}
          </span>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="agent-panel__error" role="alert">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
          <span className="agent-panel__error-text">{error}</span>
        </div>
      )}

      {/* Thought Log */}
      <div className="agent-panel__log" role="list" aria-label="Agent thought log">
        {thoughtEntries.length === 0 && !running && (
          <div className="agent-panel__empty">
            Configure a goal and run the agent to see its thought process here.
          </div>
        )}
        {thoughtEntries.length === 0 && running && (
          <div className="agent-panel__empty">
            Agent is thinking...
          </div>
        )}
        {thoughtEntries.map((entry, idx) => (
          <ThoughtEntry key={idx} entry={entry} />
        ))}
        <div ref={thoughtsEndRef} />
      </div>
    </div>
  );
}
