/**
 * IntegrationsPanel - External Integrations Dashboard.
 *
 * Features:
 * - Google Drive file browser
 * - Slack channel messaging
 * - GitHub repository browser
 */

import React, { useState, useEffect } from 'react';
import { api } from '../api';
import './IntegrationsPanel.css';

const INTEGRATION_ICONS = {
  google_drive: '📁',
  slack: '💬',
  github: '🐙',
};

export default function IntegrationsPanel({ onClose }) {
  const [activeIntegration, setActiveIntegration] = useState('github');
  const [integrationStatus, setIntegrationStatus] = useState({});
  const [error, setError] = useState(null);

  // GitHub state
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [repoFiles, setRepoFiles] = useState([]);
  const [issues, setIssues] = useState([]);
  const [prs, setPrs] = useState([]);
  const [isLoadingRepos, setIsLoadingRepos] = useState(false);

  // Slack state
  const [slackChannels, setSlackChannels] = useState([]);
  const [selectedChannel, setSelectedChannel] = useState('');
  const [slackMessage, setSlackMessage] = useState('');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [messageSent, setMessageSent] = useState(false);

  // Load integration status
  useEffect(() => {
    const loadStatus = async () => {
      try {
        const status = await api.getIntegrationStatus();
        setIntegrationStatus(status);
      } catch (err) {
        console.error('Failed to load integration status:', err);
      }
    };
    loadStatus();
  }, []);

  // Load GitHub repos
  useEffect(() => {
    if (activeIntegration === 'github' && integrationStatus.github?.available) {
      loadRepos();
    }
  }, [activeIntegration, integrationStatus]);

  // Load Slack channels
  useEffect(() => {
    if (activeIntegration === 'slack' && integrationStatus.slack?.available) {
      loadSlackChannels();
    }
  }, [activeIntegration, integrationStatus]);

  const loadRepos = async () => {
    setIsLoadingRepos(true);
    try {
      const result = await api.githubListRepos();
      setRepos(result.repos || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingRepos(false);
    }
  };

  const loadRepoDetails = async (repo) => {
    setSelectedRepo(repo);
    try {
      const [issuesResult, prsResult] = await Promise.all([
        api.githubListIssues(repo.full_name.split('/')[0], repo.name),
        api.githubListPRs(repo.full_name.split('/')[0], repo.name),
      ]);
      setIssues(issuesResult.issues || []);
      setPrs(prsResult.pull_requests || []);
    } catch (err) {
      setError(err.message);
    }
  };

  const loadSlackChannels = async () => {
    try {
      const result = await api.slackListChannels();
      setSlackChannels(result.channels || []);
    } catch (err) {
      setError(err.message);
    }
  };

  const sendSlackMessage = async () => {
    if (!selectedChannel || !slackMessage.trim() || isSendingMessage) return;

    setIsSendingMessage(true);
    setError(null);

    try {
      await api.slackSendMessage(selectedChannel, slackMessage.trim());
      setMessageSent(true);
      setSlackMessage('');
      setTimeout(() => setMessageSent(false), 3000);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSendingMessage(false);
    }
  };

  const renderGitHubPanel = () => {
    const status = integrationStatus.github;

    if (!status?.available) {
      return (
        <div className="ip-not-configured">
          <span className="ip-icon">🔐</span>
          <h3>GitHub Not Configured</h3>
          <p>Set GITHUB_TOKEN environment variable to enable GitHub integration.</p>
        </div>
      );
    }

    return (
      <div className="ip-github">
        <div className="ip-sidebar">
          <h3>Repositories</h3>
          {isLoadingRepos ? (
            <div className="ip-loading">Loading...</div>
          ) : (
            <div className="ip-repo-list">
              {repos.map(repo => (
                <div
                  key={repo.id}
                  className={`ip-repo-item ${selectedRepo?.id === repo.id ? 'active' : ''}`}
                  onClick={() => loadRepoDetails(repo)}
                >
                  <span className="ip-repo-icon">{repo.private ? '🔒' : '📂'}</span>
                  <div className="ip-repo-info">
                    <span className="ip-repo-name">{repo.name}</span>
                    <span className="ip-repo-meta">
                      {repo.language && <span className="ip-lang">{repo.language}</span>}
                      ⭐ {repo.stars}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="ip-main">
          {selectedRepo ? (
            <>
              <div className="ip-repo-header">
                <h3>{selectedRepo.full_name}</h3>
                <p>{selectedRepo.description}</p>
                <a href={selectedRepo.html_url} target="_blank" rel="noopener noreferrer">
                  View on GitHub →
                </a>
              </div>

              <div className="ip-repo-sections">
                <div className="ip-section">
                  <h4>Open Issues ({issues.length})</h4>
                  <div className="ip-issue-list">
                    {issues.slice(0, 5).map(issue => (
                      <a
                        key={issue.number}
                        href={issue.html_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ip-issue-item"
                      >
                        <span className="ip-issue-number">#{issue.number}</span>
                        <span className="ip-issue-title">{issue.title}</span>
                        <div className="ip-issue-labels">
                          {issue.labels.slice(0, 3).map(label => (
                            <span key={label} className="ip-label">{label}</span>
                          ))}
                        </div>
                      </a>
                    ))}
                    {issues.length === 0 && <p className="ip-empty">No open issues</p>}
                  </div>
                </div>

                <div className="ip-section">
                  <h4>Pull Requests ({prs.length})</h4>
                  <div className="ip-pr-list">
                    {prs.slice(0, 5).map(pr => (
                      <a
                        key={pr.number}
                        href={pr.html_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ip-pr-item"
                      >
                        <span className="ip-pr-number">#{pr.number}</span>
                        <span className="ip-pr-title">{pr.title}</span>
                        <span className="ip-pr-branch">{pr.head} → {pr.base}</span>
                      </a>
                    ))}
                    {prs.length === 0 && <p className="ip-empty">No open pull requests</p>}
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="ip-placeholder">
              <span>👈</span>
              <p>Select a repository to view details</p>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderSlackPanel = () => {
    const status = integrationStatus.slack;

    if (!status?.available) {
      return (
        <div className="ip-not-configured">
          <span className="ip-icon">🔐</span>
          <h3>Slack Not Configured</h3>
          <p>Set SLACK_BOT_TOKEN or SLACK_WEBHOOK_URL environment variable.</p>
        </div>
      );
    }

    return (
      <div className="ip-slack">
        <div className="ip-slack-form">
          <div className="ip-form-group">
            <label>Channel</label>
            <select
              value={selectedChannel}
              onChange={(e) => setSelectedChannel(e.target.value)}
            >
              <option value="">Select a channel...</option>
              {slackChannels.map(ch => (
                <option key={ch.id} value={ch.id}>
                  #{ch.name} ({ch.num_members} members)
                </option>
              ))}
            </select>
          </div>

          <div className="ip-form-group">
            <label>Message</label>
            <textarea
              value={slackMessage}
              onChange={(e) => setSlackMessage(e.target.value)}
              placeholder="Type your message..."
              rows={4}
            />
          </div>

          <button
            className="ip-send-btn"
            onClick={sendSlackMessage}
            disabled={!selectedChannel || !slackMessage.trim() || isSendingMessage}
          >
            {isSendingMessage ? 'Sending...' : '📤 Send Message'}
          </button>

          {messageSent && (
            <div className="ip-success">✅ Message sent successfully!</div>
          )}
        </div>
      </div>
    );
  };

  const renderGDrivePanel = () => {
    const status = integrationStatus.google_drive;

    return (
      <div className="ip-not-configured">
        <span className="ip-icon">📁</span>
        <h3>Google Drive</h3>
        <p>
          {status?.available
            ? 'Connect your Google account to access Drive files.'
            : 'Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable.'}
        </p>
        <button className="ip-connect-btn" disabled>
          🔗 Connect Google Drive
        </button>
      </div>
    );
  };

  return (
    <div className="integrations-panel">
      <div className="ip-header">
        <h2>
          <span className="ip-icon">🔌</span>
          Integrations
        </h2>
        <p className="ip-description">
          Connect with Google Drive, Slack, and GitHub.
        </p>
        {onClose && (
          <button className="close-btn" onClick={onClose}>×</button>
        )}
      </div>

      <div className="ip-tabs">
        {Object.entries(integrationStatus).map(([key, value]) => (
          <button
            key={key}
            className={`ip-tab ${activeIntegration === key ? 'active' : ''} ${value?.available ? '' : 'disabled'}`}
            onClick={() => setActiveIntegration(key)}
          >
            <span>{INTEGRATION_ICONS[key]}</span>
            <span>{key.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
            {value?.available && <span className="ip-status-dot active"></span>}
          </button>
        ))}
      </div>

      <div className="ip-content">
        {error && (
          <div className="ip-error">
            <strong>Error:</strong> {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        {activeIntegration === 'github' && renderGitHubPanel()}
        {activeIntegration === 'slack' && renderSlackPanel()}
        {activeIntegration === 'google_drive' && renderGDrivePanel()}
      </div>
    </div>
  );
}
