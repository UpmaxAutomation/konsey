import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './CompareView.css';

export default function CompareView({ responses, isOpen, onClose }) {
  const [mergedSelections, setMergedSelections] = useState([]);
  const scrollRefs = useRef([]);

  // Auto-select ALL models when modal opens - no manual selection needed
  const selectedModels = responses.map(r => r.model);

  // Determine layout based on number of responses
  const layoutMode = responses.length <= 2 ? '2-column' : responses.length === 3 ? '3-column' : 'auto';

  // Sync scroll across columns
  const handleScroll = (index) => {
    const currentScroll = scrollRefs.current[index];
    if (!currentScroll) return;

    const scrollTop = currentScroll.scrollTop;
    scrollRefs.current.forEach((ref, i) => {
      if (ref && i !== index) {
        ref.scrollTop = scrollTop;
      }
    });
  };

  // Handle text selection for merging
  const handleTextSelect = (modelName, text) => {
    const selection = window.getSelection().toString().trim();
    if (selection.length > 0) {
      setMergedSelections([...mergedSelections, {
        model: modelName,
        text: selection,
        timestamp: Date.now()
      }]);
    }
  };

  // Copy merged text to clipboard
  const copyMergedText = () => {
    const merged = mergedSelections.map((sel, idx) =>
      `[From ${sel.model.split('/')[1] || sel.model}]\n${sel.text}`
    ).join('\n\n---\n\n');

    navigator.clipboard.writeText(merged);
    alert('Merged text copied to clipboard!');
  };

  // Clear merged selections
  const clearMergedSelections = () => {
    setMergedSelections([]);
  };

  // Copy individual response
  const copyResponse = (response) => {
    navigator.clipboard.writeText(response.response);
    alert('Response copied to clipboard!');
  };

  if (!isOpen) return null;

  const selectedResponses = responses;

  // Color palette for model headers
  const colors = [
    '#4a90e2', // blue
    '#2d8a2d', // green
    '#e24a4a', // red
    '#e2a54a', // orange
    '#a54ae2', // purple
    '#4ae2e2'  // cyan
  ];

  return (
    <div className="compare-modal-overlay" onClick={onClose}>
      <div className="compare-modal" onClick={(e) => e.stopPropagation()}>
        <div className="compare-header">
          <h3>Compare Model Responses</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="compare-controls">
          <div className="compare-info">
            <span className="model-count">{responses.length} models compared</span>
            <span className="hint">Select text from any column to merge responses</span>
          </div>

          {mergedSelections.length > 0 && (
            <div className="merge-controls">
              <span>{mergedSelections.length} selection(s) merged</span>
              <button className="copy-merged-btn" onClick={copyMergedText}>
                📋 Copy Merged Text
              </button>
              <button className="clear-merged-btn" onClick={clearMergedSelections}>
                🗑️ Clear
              </button>
            </div>
          )}
        </div>

        <div className="compare-grid" style={{ gridTemplateColumns: `repeat(${responses.length}, 1fr)` }}>
          {selectedResponses.map((response, idx) => {
            const headerColor = colors[idx % colors.length];

            return (
              <div key={response.model} className="compare-column">
                <div
                  className="compare-column-header"
                  style={{ backgroundColor: headerColor }}
                >
                  <div className="model-name-full">
                    {response.model.split('/')[1] || response.model}
                    {response.thinking && (
                      <span className="thinking-indicator" title="Has reasoning tokens">🧠</span>
                    )}
                  </div>
                  <button
                    className="copy-single-btn"
                    onClick={() => copyResponse(response)}
                    title="Copy this response"
                  >
                    📋
                  </button>
                </div>

                <div
                  className="compare-column-content"
                  ref={(el) => scrollRefs.current[idx] = el}
                  onScroll={() => handleScroll(idx)}
                  onMouseUp={() => handleTextSelect(response.model, response.response)}
                >
                  {response.thinking && (
                    <div className="thinking-preview">
                      <details>
                        <summary>🧠 Reasoning Process</summary>
                        <div className="thinking-content-compare">
                          <ReactMarkdown>{response.thinking}</ReactMarkdown>
                        </div>
                      </details>
                    </div>
                  )}

                  <div className="response-content markdown-content">
                    <ReactMarkdown>{response.response}</ReactMarkdown>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {mergedSelections.length > 0 && (
          <div className="merged-preview">
            <h4>Merged Selections Preview:</h4>
            <div className="merged-content">
              {mergedSelections.map((sel, idx) => (
                <div key={sel.timestamp} className="merged-item">
                  <div className="merged-item-header">
                    From: {sel.model.split('/')[1] || sel.model}
                    <button
                      className="remove-merged-btn"
                      onClick={() => setMergedSelections(mergedSelections.filter((_, i) => i !== idx))}
                    >
                      ✕
                    </button>
                  </div>
                  <div className="merged-item-text">{sel.text}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
