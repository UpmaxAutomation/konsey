import { useState, useEffect } from 'react';
import { api } from '../../../api';
import '../styles/CostEstimate.css';

/**
 * CostEstimate component - Shows estimated cost before sending a query.
 * Displays min/max cost range with breakdown by stage.
 *
 * @param {Object} props
 * @param {number} props.messageLength - Character length of the message to estimate
 * @param {function} props.onConfirm - Called when user confirms to proceed
 * @param {function} props.onCancel - Called when user cancels
 * @param {boolean} props.isVisible - Whether the component is visible
 */
export default function CostEstimate({ messageLength, onConfirm, onCancel, isVisible }) {
  const [estimate, setEstimate] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showBreakdown, setShowBreakdown] = useState(false);

  useEffect(() => {
    if (isVisible && messageLength > 0) {
      fetchEstimate();
    }
  }, [isVisible, messageLength]);

  const fetchEstimate = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.estimateCost({ message_length: messageLength });
      setEstimate(result);
    } catch (err) {
      setError('Failed to estimate cost. Please try again.');
      console.error('Cost estimation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatCost = (cost) => {
    if (cost < 0.01) {
      return `$${cost.toFixed(4)}`;
    } else if (cost < 1) {
      return `$${cost.toFixed(3)}`;
    }
    return `$${cost.toFixed(2)}`;
  };

  const formatTokens = (tokens) => {
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}k`;
    }
    return tokens.toString();
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="cost-estimate-overlay">
      <div className="cost-estimate-modal">
        <div className="cost-estimate-header">
          <h3>Estimated Query Cost</h3>
          <button className="cost-estimate-close" onClick={onCancel} aria-label="Close">
            &times;
          </button>
        </div>

        <div className="cost-estimate-content">
          {loading && (
            <div className="cost-estimate-loading">
              <div className="cost-estimate-spinner"></div>
              <span>Calculating estimate...</span>
            </div>
          )}

          {error && (
            <div className="cost-estimate-error">
              <span>{error}</span>
              <button onClick={fetchEstimate} className="cost-estimate-retry">
                Retry
              </button>
            </div>
          )}

          {estimate && !loading && (
            <>
              <div className="cost-estimate-main">
                <div className="cost-estimate-range">
                  <span className="cost-estimate-label">Estimated Cost:</span>
                  <span className="cost-estimate-value">
                    {formatCost(estimate.min_cost)} - {formatCost(estimate.max_cost)}
                  </span>
                </div>

                <div className="cost-estimate-models">
                  <span className="cost-estimate-label">Council:</span>
                  <span className="cost-estimate-model-count">
                    {estimate.models_used.council.length} models
                  </span>
                </div>
              </div>

              <button
                className="cost-estimate-breakdown-toggle"
                onClick={() => setShowBreakdown(!showBreakdown)}
              >
                {showBreakdown ? 'Hide Details' : 'Show Details'}
              </button>

              {showBreakdown && (
                <div className="cost-estimate-breakdown">
                  <div className="cost-estimate-stage">
                    <div className="cost-estimate-stage-header">
                      <span className="stage-name">Stage 1: Collection</span>
                      <span className="stage-cost">
                        {formatCost(estimate.breakdown.stage1.min)} - {formatCost(estimate.breakdown.stage1.max)}
                      </span>
                    </div>
                    <div className="cost-estimate-stage-details">
                      <span>Input: {formatTokens(estimate.token_estimates.stage1.input)} tokens</span>
                      <span>Output: {formatTokens(estimate.token_estimates.stage1.output_range[0])} - {formatTokens(estimate.token_estimates.stage1.output_range[1])} tokens</span>
                    </div>
                  </div>

                  <div className="cost-estimate-stage">
                    <div className="cost-estimate-stage-header">
                      <span className="stage-name">Stage 2: Peer Review</span>
                      <span className="stage-cost">
                        {formatCost(estimate.breakdown.stage2.min)} - {formatCost(estimate.breakdown.stage2.max)}
                      </span>
                    </div>
                    <div className="cost-estimate-stage-details">
                      <span>Input: {formatTokens(estimate.token_estimates.stage2.input)} tokens</span>
                      <span>Output: {formatTokens(estimate.token_estimates.stage2.output_range[0])} - {formatTokens(estimate.token_estimates.stage2.output_range[1])} tokens</span>
                    </div>
                  </div>

                  <div className="cost-estimate-stage">
                    <div className="cost-estimate-stage-header">
                      <span className="stage-name">Stage 3: Synthesis</span>
                      <span className="stage-cost">
                        {formatCost(estimate.breakdown.stage3.min)} - {formatCost(estimate.breakdown.stage3.max)}
                      </span>
                    </div>
                    <div className="cost-estimate-stage-details">
                      <span>Input: {formatTokens(estimate.token_estimates.stage3.input)} tokens</span>
                      <span>Output: {formatTokens(estimate.token_estimates.stage3.output_range[0])} - {formatTokens(estimate.token_estimates.stage3.output_range[1])} tokens</span>
                    </div>
                  </div>

                  <div className="cost-estimate-models-list">
                    <div className="models-section">
                      <span className="models-label">Council Models:</span>
                      <ul className="models-list">
                        {estimate.models_used.council.map((model, idx) => (
                          <li key={idx}>{model.split('/').pop()}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="models-section">
                      <span className="models-label">Chairman:</span>
                      <span className="models-value">{estimate.models_used.chairman.split('/').pop()}</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="cost-estimate-actions">
          <button className="cost-estimate-cancel" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="cost-estimate-confirm"
            onClick={onConfirm}
            disabled={loading || error}
          >
            Proceed
          </button>
        </div>
      </div>
    </div>
  );
}
