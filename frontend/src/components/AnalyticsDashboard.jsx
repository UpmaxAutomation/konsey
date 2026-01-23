import { useState, useEffect } from 'react';
import { api } from '../api';
import './AnalyticsDashboard.css';

export default function AnalyticsDashboard({ onClose }) {
  const [overview, setOverview] = useState(null);
  const [modelStats, setModelStats] = useState([]);
  const [conversationStats, setConversationStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      const [overviewData, modelsData, convData] = await Promise.all([
        api.getAnalyticsOverview(),
        api.getModelAnalytics(),
        api.getConversationAnalytics(),
      ]);
      setOverview(overviewData);
      setModelStats(modelsData.models || []);
      setConversationStats(convData);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const data = await api.exportAnalytics();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `llm-council-analytics-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export analytics:', error);
    }
  };

  const formatCost = (cost) => {
    return `$${cost.toFixed(4)}`;
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  };

  if (loading) {
    return (
      <div className="analytics-dashboard">
        <div className="analytics-header">
          <h2>Analytics Dashboard</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="loading">Loading analytics...</div>
      </div>
    );
  }

  return (
    <div className="analytics-dashboard">
      <div className="analytics-header">
        <h2>Analytics Dashboard</h2>
        <div className="header-actions">
          <button className="export-btn" onClick={handleExport}>
            Export Data
          </button>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
      </div>

      <div className="analytics-tabs">
        <button
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`tab ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => setActiveTab('models')}
        >
          Models
        </button>
        <button
          className={`tab ${activeTab === 'trends' ? 'active' : ''}`}
          onClick={() => setActiveTab('trends')}
        >
          Trends
        </button>
      </div>

      <div className="analytics-content">
        {activeTab === 'overview' && overview && (
          <div className="overview-tab">
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon">💬</div>
                <div className="stat-value">
                  {overview.overview.total_conversations}
                </div>
                <div className="stat-label">Total Conversations</div>
              </div>

              <div className="stat-card">
                <div className="stat-icon">📝</div>
                <div className="stat-value">
                  {overview.overview.total_messages}
                </div>
                <div className="stat-label">Total Messages</div>
              </div>

              <div className="stat-card">
                <div className="stat-icon">🔤</div>
                <div className="stat-value">
                  {formatNumber(overview.overview.total_tokens)}
                </div>
                <div className="stat-label">Tokens Used</div>
              </div>

              <div className="stat-card">
                <div className="stat-icon">💰</div>
                <div className="stat-value">
                  {formatCost(overview.overview.total_cost)}
                </div>
                <div className="stat-label">Total Cost</div>
              </div>
            </div>

            <div className="today-stats">
              <h3>Today's Activity</h3>
              <div className="today-grid">
                <div className="today-item">
                  <span className="today-value">
                    {overview.trends.conversations_today}
                  </span>
                  <span className="today-label">New Conversations</span>
                </div>
                <div className="today-item">
                  <span className="today-value">
                    {overview.trends.active_models}
                  </span>
                  <span className="today-label">Active Models</span>
                </div>
              </div>
            </div>

            <div className="cost-breakdown">
              <h3>Cost by Model</h3>
              <div className="cost-list">
                {Object.entries(overview.by_model || {}).map(([model, data]) => (
                  <div key={model} className="cost-item">
                    <span className="model-name">
                      {model.split('/').pop()}
                    </span>
                    <div className="cost-bar-container">
                      <div
                        className="cost-bar"
                        style={{
                          width: `${Math.min((data.cost / overview.overview.total_cost) * 100, 100)}%`
                        }}
                      />
                    </div>
                    <span className="cost-value">{formatCost(data.cost)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'models' && (
          <div className="models-tab">
            <div className="models-table">
              <div className="table-header">
                <span>Model</span>
                <span>Requests</span>
                <span>Input Tokens</span>
                <span>Output Tokens</span>
                <span>Cost</span>
              </div>
              {modelStats.length === 0 ? (
                <div className="no-data">No model usage data yet</div>
              ) : (
                modelStats.map((model) => (
                  <div key={model.model} className="table-row">
                    <span className="model-cell">
                      {model.model.split('/').pop()}
                    </span>
                    <span>{model.requests}</span>
                    <span>{formatNumber(model.input_tokens)}</span>
                    <span>{formatNumber(model.output_tokens)}</span>
                    <span>{formatCost(model.cost)}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {activeTab === 'trends' && conversationStats && (
          <div className="trends-tab">
            <div className="trend-summary">
              <div className="trend-stat">
                <span className="trend-value">
                  {conversationStats.avg_messages_per_conversation.toFixed(1)}
                </span>
                <span className="trend-label">Avg Messages/Conversation</span>
              </div>
            </div>

            <h3>Daily Activity (Last 30 Days)</h3>
            <div className="daily-chart">
              {conversationStats.daily.length === 0 ? (
                <div className="no-data">No conversation data yet</div>
              ) : (
                conversationStats.daily.slice(0, 14).map((day) => (
                  <div key={day.date} className="day-bar">
                    <div
                      className="bar"
                      style={{
                        height: `${Math.max((day.count / Math.max(...conversationStats.daily.map(d => d.count))) * 100, 5)}%`
                      }}
                      title={`${day.date}: ${day.count} conversations, ${day.messages} messages`}
                    />
                    <span className="day-label">
                      {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}
                    </span>
                  </div>
                ))
              )}
            </div>

            <div className="daily-list">
              {conversationStats.daily.slice(0, 7).map((day) => (
                <div key={day.date} className="daily-item">
                  <span className="daily-date">
                    {new Date(day.date).toLocaleDateString()}
                  </span>
                  <span className="daily-stats">
                    {day.count} conversations, {day.messages} messages
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
