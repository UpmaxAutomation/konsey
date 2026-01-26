import { useState, useEffect, memo, useMemo } from 'react';
import SafeMarkdown from './SafeMarkdown';
import CompareView from './CompareView';
import CopyButton from './CopyButton';
import './Stage1.css';

import { API_BASE } from '../api/client';

const Stage1 = memo(function Stage1({ responses, conversationId, messageIndex }) {
  const [activeTab, setActiveTab] = useState(0);
  const [showThinking, setShowThinking] = useState({});
  const [showCompare, setShowCompare] = useState(false);
  const [ratings, setRatings] = useState({});
  const [showFeedback, setShowFeedback] = useState({});
  const [feedbackText, setFeedbackText] = useState({});
  const [submittingRating, setSubmittingRating] = useState({});

  if (!responses || responses.length === 0) {
    return null;
  }

  const currentResponse = responses[activeTab];
  const hasThinking = currentResponse.thinking && currentResponse.thinking.trim().length > 0;

  // Memoize response count to avoid reloading ratings when response content changes
  const responseCount = responses?.length || 0;

  // Load existing ratings when component mounts or conversation changes
  useEffect(() => {
    if (conversationId && messageIndex !== undefined && responseCount > 0) {
      loadExistingRatings();
    }
  }, [conversationId, messageIndex, responseCount]);

  const loadExistingRatings = async () => {
    if (!responses || responses.length === 0) return;

    const loadedRatings = {};
    for (const response of responses) {
      if (!response?.model) continue;

      try {
        const res = await fetch(
          `${API_BASE}/ratings/${conversationId}/${messageIndex}/${encodeURIComponent(response.model)}`
        );
        if (!res.ok) continue;

        const data = await res.json();
        if (data?.has_rating && data?.rating?.rating) {
          loadedRatings[response.model] = data.rating.rating;
          if (data.rating.feedback_text) {
            setFeedbackText(prev => ({
              ...prev,
              [response.model]: data.rating.feedback_text
            }));
          }
        }
      } catch (error) {
        console.error('Failed to load rating for', response.model, ':', error);
      }
    }
    setRatings(loadedRatings);
  };

  const submitRating = async (modelId, rating) => {
    if (!conversationId || messageIndex === undefined) {
      console.error('Cannot submit rating: missing conversation context');
      return;
    }

    setSubmittingRating(prev => ({ ...prev, [modelId]: true }));

    try {
      const response = await fetch(`${API_BASE}/ratings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          message_index: messageIndex,
          model_id: modelId,
          rating: rating,
          feedback_text: feedbackText[modelId] || null,
          query_category: 'general'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to submit rating');
      }

      setRatings(prev => ({ ...prev, [modelId]: rating }));
      setShowFeedback(prev => ({ ...prev, [modelId]: false }));
    } catch (error) {
      console.error('Failed to submit rating:', error);
      alert('Failed to submit rating. Please try again.');
    } finally {
      setSubmittingRating(prev => ({ ...prev, [modelId]: false }));
    }
  };

  const toggleThinking = (index) => {
    setShowThinking(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const toggleFeedback = (modelId) => {
    setShowFeedback(prev => ({
      ...prev,
      [modelId]: !prev[modelId]
    }));
  };

  return (
    <div className="stage stage1">
      <div className="stage-header-with-controls">
        <h3 className="stage-title">Stage 1: Individual Responses</h3>
        {responses.length > 1 && (
          <button
            className="compare-btn"
            onClick={() => setShowCompare(true)}
            title="Compare responses side-by-side"
          >
            ⚖️ Compare
          </button>
        )}
      </div>

      <div className="tabs">
        {responses.map((resp, index) => (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {resp.model.split('/')[1] || resp.model}
            {resp.thinking && <span className="thinking-indicator" title="Has reasoning tokens">🧠</span>}
          </button>
        ))}
      </div>

      <div className="tab-content">
        <div className="tab-content-header">
          <div className="model-name">{currentResponse.model}</div>
          <CopyButton text={currentResponse.response} className="compact" />
        </div>

        {hasThinking && (
          <div className="thinking-controls">
            <button
              className="toggle-thinking-btn"
              onClick={() => toggleThinking(activeTab)}
            >
              {showThinking[activeTab] ? '▼ Hide Reasoning' : '▶ Show Reasoning'}
            </button>
          </div>
        )}

        {hasThinking && showThinking[activeTab] && (
          <div className="thinking-block">
            <div className="thinking-header">Reasoning Process:</div>
            <div className="thinking-content">
              <SafeMarkdown>{currentResponse.thinking}</SafeMarkdown>
            </div>
          </div>
        )}

        <div className="response-text markdown-content">
          <SafeMarkdown>{currentResponse.response}</SafeMarkdown>
        </div>

        {conversationId && messageIndex !== undefined && (
          <div className="rating-section">
            <div className="rating-header">Rate this response:</div>
            <div className="star-rating">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  className={`star-btn ${ratings[currentResponse.model] >= star ? 'filled' : ''} ${submittingRating[currentResponse.model] ? 'disabled' : ''}`}
                  onClick={() => submitRating(currentResponse.model, star)}
                  disabled={submittingRating[currentResponse.model]}
                  title={`${star} star${star > 1 ? 's' : ''}`}
                >
                  ★
                </button>
              ))}
              {ratings[currentResponse.model] && (
                <span className="rating-value">
                  {ratings[currentResponse.model]}/5
                </span>
              )}
            </div>

            <button
              className="feedback-toggle-btn"
              onClick={() => toggleFeedback(currentResponse.model)}
            >
              {showFeedback[currentResponse.model] ? '▼ Hide Feedback' : '▶ Add Feedback'}
            </button>

            {showFeedback[currentResponse.model] && (
              <div className="feedback-input-section">
                <textarea
                  className="feedback-textarea"
                  placeholder="Optional: Share your thoughts on this response..."
                  value={feedbackText[currentResponse.model] || ''}
                  onChange={(e) => setFeedbackText(prev => ({
                    ...prev,
                    [currentResponse.model]: e.target.value
                  }))}
                  rows={3}
                />
                <button
                  className="submit-feedback-btn"
                  onClick={() => {
                    if (ratings[currentResponse.model]) {
                      submitRating(currentResponse.model, ratings[currentResponse.model]);
                    } else {
                      alert('Please select a star rating first');
                    }
                  }}
                  disabled={submittingRating[currentResponse.model]}
                >
                  {submittingRating[currentResponse.model] ? 'Saving...' : 'Save Feedback'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <CompareView
        responses={responses}
        isOpen={showCompare}
        onClose={() => setShowCompare(false)}
      />
    </div>
  );
});

export default Stage1;
