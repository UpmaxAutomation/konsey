import { useState, useCallback, memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import '../styles/PipelineNode.css';

const TYPE_CONFIG = {
  pl_input:       { label: 'Input',       color: '#10b981', icon: '\u25B6' },
  pl_llm:         { label: 'LLM',         color: '#3b82f6', icon: '\u2731' },
  pl_council:     { label: 'Council',      color: '#8b5cf6', icon: '\u25C8' },
  pl_transform:   { label: 'Transform',    color: '#f59e0b', icon: '\u21C4' },
  pl_output:      { label: 'Output',       color: '#64748b', icon: '\u25A0' },
  pl_conditional: { label: 'Conditional',  color: '#eab308', icon: '\u2662' },
};

const MODELS = [
  'openai/gpt-4o',
  'openai/gpt-4o-mini',
  'anthropic/claude-sonnet-4-20250514',
  'google/gemini-2.0-flash-001',
];

const STATUS_ICONS = {
  idle:    null,
  running: '\u23F3',
  done:    '\u2713',
  error:   '\u2717',
};

function PipelineNode({ data }) {
  const [expanded, setExpanded] = useState(false);

  const config = TYPE_CONFIG[data.card_type] || TYPE_CONFIG.pl_llm;
  const status = data.pipelineStatus || 'idle';
  const hasModelSelector = data.card_type === 'pl_llm' || data.card_type === 'pl_council';
  const hasPromptTemplate = data.card_type === 'pl_llm' || data.card_type === 'pl_transform';
  const isConditional = data.card_type === 'pl_conditional';
  const isInput = data.card_type === 'pl_input';
  const isOutput = data.card_type === 'pl_output';
  const output = data.pipelineOutput || data.extra?.last_output || '';

  const handleFieldChange = useCallback((field, value) => {
    const extra = { ...(data.extra || {}), [field]: value };
    data.onUpdateCard?.(data.cardId, { extra });
  }, [data.onUpdateCard, data.cardId, data.extra]);

  const handleContentChange = useCallback((value) => {
    data.onUpdateCard?.(data.cardId, { content: value });
  }, [data.onUpdateCard, data.cardId]);

  return (
    <div
      className={`pipeline-node pipeline-node--${status}`}
      style={{ '--pn-color': config.color }}
    >
      {/* Input handle (left) -- not for pl_input */}
      {!isInput && (
        <Handle
          type="target"
          position={Position.Left}
          id="input"
          className="pipeline-node__handle pipeline-node__handle--input"
        />
      )}

      {/* Output handle (right) -- not for pl_output */}
      {!isOutput && !isConditional && (
        <Handle
          type="source"
          position={Position.Right}
          id="output"
          className="pipeline-node__handle pipeline-node__handle--output"
        />
      )}

      {/* Conditional: two output handles */}
      {isConditional && (
        <>
          <Handle
            type="source"
            position={Position.Right}
            id="true"
            className="pipeline-node__handle pipeline-node__handle--true"
            style={{ top: '35%' }}
          />
          <Handle
            type="source"
            position={Position.Right}
            id="false"
            className="pipeline-node__handle pipeline-node__handle--false"
            style={{ top: '65%' }}
          />
        </>
      )}

      {/* Header */}
      <div className="pipeline-node__header">
        <span className="pipeline-node__icon">{config.icon}</span>
        <span className="pipeline-node__label">{data.title || config.label}</span>
        {status !== 'idle' && (
          <span className={`pipeline-node__status pipeline-node__status--${status}`}>
            {STATUS_ICONS[status]}
          </span>
        )}
      </div>

      {/* Config area */}
      <div className="pipeline-node__config">
        {hasModelSelector && (
          <select
            className="pipeline-node__select nodrag"
            value={data.extra?.model || MODELS[0]}
            onChange={(e) => handleFieldChange('model', e.target.value)}
            aria-label="Select model"
          >
            {MODELS.map((m) => (
              <option key={m} value={m}>{m.split('/').pop()}</option>
            ))}
          </select>
        )}

        {hasPromptTemplate && (
          <textarea
            className="pipeline-node__textarea nodrag nowheel"
            placeholder="Prompt template... use {{input}} for piped data"
            value={data.extra?.prompt_template || ''}
            onChange={(e) => handleFieldChange('prompt_template', e.target.value)}
            rows={3}
            aria-label="Prompt template"
          />
        )}

        {isConditional && (
          <textarea
            className="pipeline-node__textarea nodrag nowheel"
            placeholder="Condition (e.g. contains 'error')"
            value={data.extra?.condition || ''}
            onChange={(e) => handleFieldChange('condition', e.target.value)}
            rows={2}
            aria-label="Condition"
          />
        )}

        {isInput && (
          <textarea
            className="pipeline-node__textarea nodrag nowheel"
            placeholder="Enter input text..."
            value={data.content || ''}
            onChange={(e) => handleContentChange(e.target.value)}
            rows={3}
            aria-label="Input text"
          />
        )}
      </div>

      {/* Result preview */}
      {output && (
        <div className="pipeline-node__result">
          <button
            className="pipeline-node__result-toggle nodrag"
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            aria-label={expanded ? 'Collapse output' : 'Expand output'}
          >
            <span className="pipeline-node__result-label">Output</span>
            <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d={expanded ? 'M18 15l-6-6-6 6' : 'M6 9l6 6 6-6'} />
            </svg>
          </button>
          <div className={`pipeline-node__result-text${expanded ? ' pipeline-node__result-text--expanded' : ''}`}>
            {expanded ? output : output.slice(0, 200) + (output.length > 200 ? '...' : '')}
          </div>
        </div>
      )}

      {/* Conditional handle labels */}
      {isConditional && (
        <>
          <span className="pipeline-node__handle-label pipeline-node__handle-label--true">T</span>
          <span className="pipeline-node__handle-label pipeline-node__handle-label--false">F</span>
        </>
      )}
    </div>
  );
}

export default memo(PipelineNode, (prev, next) =>
  prev.data === next.data
);
