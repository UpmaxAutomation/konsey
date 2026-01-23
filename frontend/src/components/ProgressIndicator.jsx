import React from 'react';
import './ProgressIndicator.css';

/**
 * ProgressIndicator - Shows real-time progress during council query
 *
 * Props:
 * - stage: Current stage (1, 2, or 3)
 * - models: Array of model names in the council
 * - modelProgress: Map of model -> status ('pending' | 'loading' | 'completed' | 'error')
 * - chairmanModel: The chairman model name (for stage 3)
 * - chairmanStatus: Chairman status ('pending' | 'loading' | 'completed')
 */
function ProgressIndicator({
  stage = 0,
  models = [],
  modelProgress = {},
  chairmanModel = '',
  chairmanStatus = 'pending'
}) {
  const stages = [
    { num: 1, label: 'Gathering responses', description: 'Council members are responding...' },
    { num: 2, label: 'Peer review', description: 'Models are evaluating each other...' },
    { num: 3, label: 'Chairman synthesis', description: 'Chairman is synthesizing the final answer...' }
  ];

  const getCompletedCount = () => {
    return Object.values(modelProgress).filter(status => status === 'completed').length;
  };

  const getModelStatus = (model) => {
    return modelProgress[model] || 'pending';
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <span className="status-icon completed">✓</span>;
      case 'loading':
        return <span className="status-icon loading"><span className="spinner"></span></span>;
      case 'error':
        return <span className="status-icon error">✗</span>;
      default:
        return <span className="status-icon pending">○</span>;
    }
  };

  const getModelDisplayName = (model) => {
    // Extract just the model name from the full path (e.g., "openai/gpt-4" -> "GPT-4")
    const parts = model.split('/');
    const name = parts[parts.length - 1];
    // Capitalize and format nicely
    return name
      .replace(/-/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase())
      .replace(/Gpt/g, 'GPT')
      .replace(/Llama/g, 'Llama')
      .replace(/Claude/g, 'Claude');
  };

  const completedCount = getCompletedCount();
  const totalModels = models.length;
  const progressPercent = totalModels > 0 ? (completedCount / totalModels) * 100 : 0;

  return (
    <div className="progress-indicator">
      {/* Stage tabs */}
      <div className="progress-stages">
        {stages.map((s) => (
          <div
            key={s.num}
            className={`progress-stage ${stage === s.num ? 'active' : ''} ${stage > s.num ? 'completed' : ''}`}
          >
            <div className="stage-number">
              {stage > s.num ? (
                <span className="stage-check">✓</span>
              ) : stage === s.num ? (
                <span className="stage-spinner"><span className="spinner"></span></span>
              ) : (
                s.num
              )}
            </div>
            <div className="stage-info">
              <span className="stage-label">{s.label}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Current stage details */}
      {stage > 0 && stage <= 3 && (
        <div className="progress-details">
          <div className="progress-description">
            {stages[stage - 1].description}
          </div>

          {/* For stages 1 and 2, show model list */}
          {(stage === 1 || stage === 2) && models.length > 0 && (
            <>
              <div className="progress-bar-container">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="progress-count">
                {completedCount} of {totalModels} models {stage === 1 ? 'responded' : 'reviewed'}
              </div>
              <div className="model-list">
                {models.map((model) => (
                  <div
                    key={model}
                    className={`model-item ${getModelStatus(model)}`}
                  >
                    {getStatusIcon(getModelStatus(model))}
                    <span className="model-name">{getModelDisplayName(model)}</span>
                  </div>
                ))}
              </div>
            </>
          )}

          {/* For stage 3, show chairman */}
          {stage === 3 && chairmanModel && (
            <div className="chairman-status">
              <div className={`model-item ${chairmanStatus}`}>
                {getStatusIcon(chairmanStatus)}
                <span className="model-name">
                  {getModelDisplayName(chairmanModel)}
                  <span className="chairman-badge">Chairman</span>
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ProgressIndicator;
