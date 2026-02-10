import { useState } from 'react';
import '../styles/IntegrationPanel.css';

const INTEGRATIONS = [
  {
    id: 'github',
    name: 'GitHub',
    icon: '\uD83D\uDC19',
    description: 'Create cards from GitHub issues, PRs, and pushes',
    webhookPath: '/api/webhooks/github',
  },
  {
    id: 'slack',
    name: 'Slack',
    icon: '\uD83D\uDCAC',
    description: 'Create cards from Slack messages',
    webhookPath: '/api/webhooks/slack',
  },
  {
    id: 'gdrive',
    name: 'Google Drive',
    icon: '\uD83D\uDCC1',
    description: 'Export boards and assets to Google Drive',
    webhookPath: null,
  },
];

export default function IntegrationPanel({ boardId, onClose }) {
  const [copiedId, setCopiedId] = useState(null);

  const getWebhookUrl = (integration) => {
    if (!integration.webhookPath) return null;
    const base = window.location.origin;
    return `${base}${integration.webhookPath}?board_id=${boardId}`;
  };

  const copyUrl = (id, url) => {
    navigator.clipboard.writeText(url);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="integration-overlay" onClick={onClose}>
      <div className="integration-panel" onClick={e => e.stopPropagation()}>
        <div className="integration-header">
          <h2>Integrations</h2>
          <button className="integration-close" onClick={onClose}>×</button>
        </div>

        <div className="integration-list">
          {INTEGRATIONS.map(integration => {
            const webhookUrl = getWebhookUrl(integration);
            return (
              <div key={integration.id} className="integration-item">
                <div className="integration-icon">{integration.icon}</div>
                <div className="integration-info">
                  <h3>{integration.name}</h3>
                  <p>{integration.description}</p>
                  {webhookUrl && (
                    <div className="integration-webhook">
                      <span className="integration-webhook-label">Webhook URL:</span>
                      <div className="integration-webhook-url">
                        <code>{webhookUrl}</code>
                        <button
                          className="integration-copy-btn"
                          onClick={() => copyUrl(integration.id, webhookUrl)}
                        >
                          {copiedId === integration.id ? 'Copied!' : 'Copy'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="integration-note">
          <p>Configure webhooks in your external services to point to the URLs above.
          Include the <code>board_id</code> query parameter to target a specific board.</p>
        </div>
      </div>
    </div>
  );
}
