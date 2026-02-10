import { useState, useEffect } from 'react';
import './Analytics.css';

import { API_BASE } from '../api/client';

export default function Analytics({ isOpen, onClose }) {
  const [analytics, setAnalytics] = useState(null);
  const [ratings, setRatings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (isOpen) {
      fetchAnalytics();
      fetchRatings();
    }
  }, [isOpen]);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/analytics`);
      if (!response.ok) throw new Error('Failed to fetch analytics');
      const data = await response.json();
      setAnalytics(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchRatings = async () => {
    try {
      const response = await fetch(`${API_BASE}/ratings/models`);
      if (!response.ok) throw new Error('Failed to fetch ratings');
      const data = await response.json();
      setRatings(data);
    } catch (err) {
      console.error('Failed to fetch ratings:', err);
    }
  };

  const clearAnalytics = async () => {
    if (!confirm('Are you sure you want to clear all analytics data?')) return;

    try {
      const response = await fetch(`${API_BASE}/analytics/clear`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to clear analytics');
      fetchAnalytics();
    } catch (err) {
      setError(err.message);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content analytics-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Model Analytics Dashboard</h2>
          <button className="close-button" onClick={onClose}>x</button>
        </div>

        <div className="analytics-tabs">
          <button
            className={activeTab === 'overview' ? 'active' : ''}
            onClick={() => setActiveTab('overview')}
          >
            Overview
          </button>
          <button
            className={activeTab === 'performance' ? 'active' : ''}
            onClick={() => setActiveTab('performance')}
          >
            Win Rates
          </button>
          <button
            className={activeTab === 'response-times' ? 'active' : ''}
            onClick={() => setActiveTab('response-times')}
          >
            Response Times
          </button>
          <button
            className={activeTab === 'ratings' ? 'active' : ''}
            onClick={() => setActiveTab('ratings')}
          >
            User Ratings
          </button>
          <button
            className={activeTab === 'costs' ? 'active' : ''}
            onClick={() => setActiveTab('costs')}
          >
            Costs
          </button>
        </div>

        <div className="analytics-body">
          {loading && <div className="loading-state">Loading analytics...</div>}
          {error && <div className="error-state">Error: {error}</div>}

          {analytics && !loading && (
            <>
              {activeTab === 'overview' && <OverviewTab data={analytics} ratings={ratings} />}
              {activeTab === 'performance' && <WinRatesTab data={analytics.model_stats} />}
              {activeTab === 'response-times' && <ResponseTimesTab data={analytics.model_stats} responseTimes={analytics.response_times} />}
              {activeTab === 'ratings' && <RatingsTab data={ratings} />}
              {activeTab === 'costs' && <CostsTab data={analytics.cost_breakdown} />}
            </>
          )}
        </div>

        <div className="analytics-footer">
          <button onClick={clearAnalytics} className="danger-button">
            Clear Analytics Data
          </button>
          <button onClick={fetchAnalytics} className="refresh-button">
            Refresh
          </button>
        </div>
      </div>
    </div>
  );
}

function OverviewTab({ data, ratings }) {
  const { usage_trends, cost_breakdown, model_stats } = data;
  const modelCount = Object.keys(model_stats || {}).length;
  const avgTokensPerQuery = usage_trends.total_queries > 0
    ? Object.values(model_stats).reduce((sum, m) => sum + m.total_tokens, 0) / usage_trends.total_queries
    : 0;

  // Calculate top performer
  const sortedByWins = Object.entries(model_stats || {}).sort(([, a], [, b]) => b.wins - a.wins);
  const topPerformer = sortedByWins.length > 0 ? sortedByWins[0] : null;

  // Calculate average rating across all models
  const avgRating = ratings && Object.keys(ratings).length > 0
    ? Object.values(ratings).reduce((sum, m) => sum + m.average_rating, 0) / Object.keys(ratings).length
    : 0;

  // Calculate total ratings count
  const totalRatingsCount = ratings
    ? Object.values(ratings).reduce((sum, m) => sum + m.total_ratings, 0)
    : 0;

  return (
    <div className="overview-tab">
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Queries</h3>
          <div className="stat-value">{usage_trends.total_queries || 0}</div>
        </div>
        <div className="stat-card">
          <h3>Total Cost</h3>
          <div className="stat-value">${cost_breakdown.total_cost.toFixed(4)}</div>
        </div>
        <div className="stat-card">
          <h3>Models Used</h3>
          <div className="stat-value">{modelCount}</div>
        </div>
        <div className="stat-card">
          <h3>Avg Tokens/Query</h3>
          <div className="stat-value">{Math.round(avgTokensPerQuery)}</div>
        </div>
      </div>

      {/* Quick Performance Summary */}
      <div className="overview-section">
        <h3>Performance Summary</h3>
        <div className="performance-summary-grid">
          <div className="summary-card highlight-card">
            <div className="summary-icon">🏆</div>
            <div className="summary-content">
              <span className="summary-label">Top Performer</span>
              <span className="summary-value">
                {topPerformer ? formatModelName(topPerformer[0]) : 'N/A'}
              </span>
              {topPerformer && (
                <span className="summary-detail">{topPerformer[1].wins} wins</span>
              )}
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-icon">⭐</div>
            <div className="summary-content">
              <span className="summary-label">Avg User Rating</span>
              <span className="summary-value">{avgRating.toFixed(2)} / 5.0</span>
              <span className="summary-detail">{totalRatingsCount} total ratings</span>
            </div>
          </div>
          <div className="summary-card">
            <div className="summary-icon">📊</div>
            <div className="summary-content">
              <span className="summary-label">Models in Council</span>
              <span className="summary-value">{modelCount}</span>
              <span className="summary-detail">Active models</span>
            </div>
          </div>
        </div>
      </div>

      {/* Mini Win Rate Chart */}
      {sortedByWins.length > 0 && (
        <div className="overview-section">
          <h3>Top Performers (by Wins)</h3>
          <div className="mini-chart">
            {sortedByWins.slice(0, 5).map(([model, stats]) => {
              const maxWins = sortedByWins[0][1].wins || 1;
              const percentage = (stats.wins / maxWins) * 100;
              return (
                <div key={model} className="mini-chart-row">
                  <div className="mini-chart-label">{formatModelName(model)}</div>
                  <div className="mini-chart-bar-container">
                    <div className="mini-chart-bar" style={{ width: `${percentage}%` }} />
                    <span className="mini-chart-value">{stats.wins}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function WinRatesTab({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return <div className="empty-state">No model performance data yet. Run some council queries to see win rates.</div>;
  }

  // Sort by wins (primary) then avg_rank (secondary)
  const sortedModels = Object.entries(data).sort(([, a], [, b]) => {
    if (b.wins !== a.wins) return b.wins - a.wins;
    if (a.avg_rank !== null && b.avg_rank !== null) {
      return a.avg_rank - b.avg_rank;
    }
    return 0;
  });

  const maxWins = Math.max(...sortedModels.map(([, s]) => s.wins)) || 1;
  const maxAppearances = Math.max(...sortedModels.map(([, s]) => s.appearances)) || 1;

  return (
    <div className="win-rates-tab">
      <h3>Model Win Rate Leaderboard</h3>
      <p className="subtitle">Based on Stage 2 peer rankings. A "win" is when a model ranks #1 (avg rank ≤ 1.5)</p>

      {/* Win Rate Bar Chart */}
      <div className="chart-section">
        <h4>Wins by Model</h4>
        <div className="horizontal-bar-chart">
          {sortedModels.map(([model, stats], index) => {
            const winPercentage = (stats.wins / maxWins) * 100;
            const winRate = stats.appearances > 0 ? ((stats.wins / stats.appearances) * 100).toFixed(1) : 0;
            return (
              <div key={model} className="bar-chart-row">
                <div className="bar-chart-rank">
                  {index === 0 && <span className="medal gold">1st</span>}
                  {index === 1 && <span className="medal silver">2nd</span>}
                  {index === 2 && <span className="medal bronze">3rd</span>}
                  {index > 2 && <span className="rank-num">#{index + 1}</span>}
                </div>
                <div className="bar-chart-label">{formatModelName(model)}</div>
                <div className="bar-chart-bar-wrapper">
                  <div className="bar-chart-bar-bg">
                    <div
                      className="bar-chart-bar-fill wins-bar"
                      style={{ width: `${winPercentage}%` }}
                    />
                  </div>
                </div>
                <div className="bar-chart-stats">
                  <span className="wins-count">{stats.wins} wins</span>
                  <span className="win-rate">({winRate}%)</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Average Rank Chart */}
      <div className="chart-section">
        <h4>Average Rank Position</h4>
        <p className="chart-subtitle">Lower is better (1.0 = always ranked first)</p>
        <div className="rank-chart">
          {sortedModels
            .filter(([, s]) => s.avg_rank !== null)
            .sort(([, a], [, b]) => a.avg_rank - b.avg_rank)
            .map(([model, stats]) => {
              // Invert: lower rank = better = longer bar
              const maxRank = 5;
              const barWidth = ((maxRank - stats.avg_rank + 1) / maxRank) * 100;
              return (
                <div key={model} className="rank-chart-row">
                  <div className="rank-chart-label">{formatModelName(model)}</div>
                  <div className="rank-chart-bar-wrapper">
                    <div className="rank-chart-bar-bg">
                      <div
                        className="rank-chart-bar-fill"
                        style={{ width: `${barWidth}%` }}
                      />
                    </div>
                  </div>
                  <div className="rank-chart-value">{stats.avg_rank.toFixed(2)}</div>
                </div>
              );
            })}
        </div>
      </div>

      {/* Detailed Table */}
      <div className="chart-section">
        <h4>Detailed Statistics</h4>
        <table className="models-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Model</th>
              <th>Wins</th>
              <th>Win Rate</th>
              <th>Avg Rank</th>
              <th>Appearances</th>
            </tr>
          </thead>
          <tbody>
            {sortedModels.map(([model, stats], index) => {
              const winRate = stats.appearances > 0 ? ((stats.wins / stats.appearances) * 100).toFixed(1) : 0;
              return (
                <tr key={model}>
                  <td className="rank-cell">
                    {index === 0 && '🥇'}
                    {index === 1 && '🥈'}
                    {index === 2 && '🥉'}
                    {index > 2 && `#${index + 1}`}
                  </td>
                  <td className="model-cell">{formatModelName(model)}</td>
                  <td>{stats.wins}</td>
                  <td>{winRate}%</td>
                  <td>{stats.avg_rank ? stats.avg_rank.toFixed(2) : 'N/A'}</td>
                  <td>{stats.appearances}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ResponseTimesTab({ data, responseTimes }) {
  const times = responseTimes || {};
  const hasData = Object.keys(times).length > 0;

  if (!hasData && (!data || Object.keys(data).length === 0)) {
    return <div className="empty-state">No response time data yet. Run some council queries to see timing comparisons.</div>;
  }

  // Use responseTimes if available, otherwise extract from model_stats
  let timeData = {};
  if (hasData) {
    timeData = times;
  } else if (data) {
    Object.entries(data).forEach(([model, stats]) => {
      if (stats.avg_response_time > 0) {
        timeData[model] = stats.avg_response_time;
      }
    });
  }

  const sortedByTime = Object.entries(timeData).sort(([, a], [, b]) => a - b);
  const maxTime = Math.max(...Object.values(timeData)) || 1;
  const avgTime = Object.values(timeData).length > 0
    ? Object.values(timeData).reduce((a, b) => a + b, 0) / Object.values(timeData).length
    : 0;

  return (
    <div className="response-times-tab">
      <h3>Response Time Comparison</h3>
      <p className="subtitle">Average response time per model (lower is faster)</p>

      {/* Summary Stats */}
      <div className="time-stats-grid">
        <div className="time-stat-card fastest">
          <div className="time-stat-icon">⚡</div>
          <div className="time-stat-content">
            <span className="time-stat-label">Fastest Model</span>
            <span className="time-stat-value">
              {sortedByTime.length > 0 ? formatModelName(sortedByTime[0][0]) : 'N/A'}
            </span>
            <span className="time-stat-detail">
              {sortedByTime.length > 0 ? `${sortedByTime[0][1].toFixed(2)}s` : ''}
            </span>
          </div>
        </div>
        <div className="time-stat-card">
          <div className="time-stat-icon">📊</div>
          <div className="time-stat-content">
            <span className="time-stat-label">Average Time</span>
            <span className="time-stat-value">{avgTime.toFixed(2)}s</span>
            <span className="time-stat-detail">across all models</span>
          </div>
        </div>
        <div className="time-stat-card slowest">
          <div className="time-stat-icon">🐢</div>
          <div className="time-stat-content">
            <span className="time-stat-label">Slowest Model</span>
            <span className="time-stat-value">
              {sortedByTime.length > 0 ? formatModelName(sortedByTime[sortedByTime.length - 1][0]) : 'N/A'}
            </span>
            <span className="time-stat-detail">
              {sortedByTime.length > 0 ? `${sortedByTime[sortedByTime.length - 1][1].toFixed(2)}s` : ''}
            </span>
          </div>
        </div>
      </div>

      {/* Response Time Bar Chart */}
      <div className="chart-section">
        <h4>Response Times (sorted by speed)</h4>
        <div className="time-bar-chart">
          {sortedByTime.map(([model, time], index) => {
            const percentage = (time / maxTime) * 100;
            const isAvg = Math.abs(time - avgTime) < avgTime * 0.1;
            const isFast = time < avgTime * 0.7;
            const isSlow = time > avgTime * 1.3;

            let barClass = 'time-bar-fill';
            if (isFast) barClass += ' fast';
            else if (isSlow) barClass += ' slow';

            return (
              <div key={model} className="time-bar-row">
                <div className="time-bar-rank">
                  {index === 0 && <span className="speed-indicator fast">Fastest</span>}
                  {index === sortedByTime.length - 1 && sortedByTime.length > 1 && (
                    <span className="speed-indicator slow">Slowest</span>
                  )}
                </div>
                <div className="time-bar-label">{formatModelName(model)}</div>
                <div className="time-bar-wrapper">
                  <div className="time-bar-bg">
                    <div
                      className={barClass}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
                <div className="time-bar-value">{time.toFixed(2)}s</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Time Distribution Visualization */}
      <div className="chart-section">
        <h4>Time Distribution</h4>
        <div className="time-distribution">
          <div className="time-legend">
            <span className="legend-item"><span className="dot fast"></span> Fast (&lt;70% avg)</span>
            <span className="legend-item"><span className="dot normal"></span> Normal</span>
            <span className="legend-item"><span className="dot slow"></span> Slow (&gt;130% avg)</span>
          </div>
          <div className="time-scale">
            <span className="scale-label">0s</span>
            <div className="scale-bar">
              {sortedByTime.map(([model, time]) => {
                const position = (time / maxTime) * 100;
                const isFast = time < avgTime * 0.7;
                const isSlow = time > avgTime * 1.3;
                let dotClass = 'time-dot';
                if (isFast) dotClass += ' fast';
                else if (isSlow) dotClass += ' slow';

                return (
                  <div
                    key={model}
                    className={dotClass}
                    style={{ left: `${position}%` }}
                    title={`${formatModelName(model)}: ${time.toFixed(2)}s`}
                  />
                );
              })}
              <div
                className="avg-line"
                style={{ left: `${(avgTime / maxTime) * 100}%` }}
                title={`Average: ${avgTime.toFixed(2)}s`}
              />
            </div>
            <span className="scale-label">{maxTime.toFixed(1)}s</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function CostsTab({ data }) {
  if (!data || !data.by_model || Object.keys(data.by_model).length === 0) {
    return <div className="empty-state">No cost data yet</div>;
  }

  const sortedCosts = Object.entries(data.by_model).sort(([, a], [, b]) => b - a);

  return (
    <div className="costs-tab">
      <div className="total-cost-card">
        <h3>Total Cost</h3>
        <div className="big-value">${data.total_cost.toFixed(4)}</div>
      </div>

      <h3>Cost by Model</h3>
      <div className="cost-bars">
        {sortedCosts.map(([model, cost]) => {
          const percentage = (cost / data.total_cost) * 100;
          return (
            <div key={model} className="cost-bar-item">
              <div className="cost-bar-label">
                <span className="model-name">{formatModelName(model)}</span>
                <span className="cost-value">${cost.toFixed(4)}</span>
              </div>
              <div className="cost-bar-bg">
                <div
                  className="cost-bar-fill"
                  style={{ width: `${percentage}%` }}
                />
              </div>
              <div className="cost-percentage">{percentage.toFixed(1)}%</div>
            </div>
          );
        })}
      </div>

      {data.by_day && Object.keys(data.by_day).length > 0 && (
        <>
          <h3>Cost by Day</h3>
          <table className="cost-by-day-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.by_day)
                .sort(([a], [b]) => b.localeCompare(a))
                .map(([date, cost]) => (
                  <tr key={date}>
                    <td>{date}</td>
                    <td>${cost.toFixed(4)}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

function RatingsTab({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return <div className="empty-state">No ratings yet. Start rating model responses to see statistics!</div>;
  }

  // Sort by average rating (primary) then total ratings (secondary)
  const sortedModels = Object.entries(data).sort(([, a], [, b]) => {
    if (b.average_rating !== a.average_rating) {
      return b.average_rating - a.average_rating;
    }
    return b.total_ratings - a.total_ratings;
  });

  const maxRatings = Math.max(...sortedModels.map(([, s]) => s.total_ratings)) || 1;

  return (
    <div className="ratings-tab">
      <h3>User Ratings by Model</h3>
      <p className="subtitle">Based on user feedback (1-5 stars)</p>

      {/* Rating Overview Chart */}
      <div className="chart-section">
        <h4>Average Ratings</h4>
        <div className="rating-bar-chart">
          {sortedModels.map(([model, stats], index) => {
            const ratingWidth = (stats.average_rating / 5) * 100;
            return (
              <div key={model} className="rating-bar-row">
                <div className="rating-bar-rank">
                  {index === 0 && '🥇'}
                  {index === 1 && '🥈'}
                  {index === 2 && '🥉'}
                  {index > 2 && `#${index + 1}`}
                </div>
                <div className="rating-bar-label">{formatModelName(model)}</div>
                <div className="rating-bar-wrapper">
                  <div className="rating-bar-bg">
                    <div
                      className="rating-bar-fill"
                      style={{ width: `${ratingWidth}%` }}
                    />
                  </div>
                </div>
                <div className="rating-bar-value">
                  <span className="star-display">{'★'.repeat(Math.round(stats.average_rating))}</span>
                  <span className="rating-numeric">{stats.average_rating.toFixed(2)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Rating Distribution Section */}
      <div className="chart-section">
        <h4>Rating Distribution by Model</h4>
        <div className="rating-distributions">
          {sortedModels.slice(0, 6).map(([model, stats]) => (
            <div key={model} className="distribution-card">
              <div className="distribution-header">
                <strong>{formatModelName(model)}</strong>
                <span className="avg-rating">{stats.average_rating.toFixed(2)} / 5.0</span>
              </div>
              <div className="distribution-bars">
                {[5, 4, 3, 2, 1].map(star => {
                  const count = stats.rating_distribution ? stats.rating_distribution[star] || 0 : 0;
                  const percentage = stats.total_ratings > 0 ? (count / stats.total_ratings) * 100 : 0;
                  return (
                    <div key={star} className="distribution-bar-row">
                      <span className="star-label">{star}★</span>
                      <div className="distribution-bar-bg">
                        <div
                          className="distribution-bar-fill"
                          style={{
                            width: `${percentage}%`,
                            background: star >= 4 ? '#28a745' : star >= 3 ? '#ffc107' : '#dc3545'
                          }}
                        />
                      </div>
                      <span className="count-label">{count}</span>
                    </div>
                  );
                })}
              </div>
              <div className="distribution-footer">
                <span>{stats.total_ratings} total ratings</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed Table */}
      <div className="chart-section">
        <h4>All Model Ratings</h4>
        <table className="ratings-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Model</th>
              <th>Avg Rating</th>
              <th>Total Ratings</th>
              <th>Win Rate</th>
            </tr>
          </thead>
          <tbody>
            {sortedModels.map(([model, stats], index) => (
              <tr key={model}>
                <td className="rank-cell">
                  {index === 0 && '🥇'}
                  {index === 1 && '🥈'}
                  {index === 2 && '🥉'}
                  {index > 2 && `#${index + 1}`}
                </td>
                <td className="model-cell">{formatModelName(model)}</td>
                <td className="rating-cell">
                  <div className="star-display">
                    {'★'.repeat(Math.round(stats.average_rating))}
                    {'☆'.repeat(5 - Math.round(stats.average_rating))}
                  </div>
                  <span className="rating-numeric">{stats.average_rating.toFixed(2)}</span>
                </td>
                <td>{stats.total_ratings}</td>
                <td>{stats.win_rate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Helper function to format model names
function formatModelName(fullName) {
  // Extract just the model name without provider prefix
  const parts = fullName.split('/');
  return parts[parts.length - 1];
}
