import { useState, useEffect } from 'react';
import { api } from '../api';
import './APIKeysManager.css';

export default function APIKeysManager({ onClose }) {
  const [keys, setKeys] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyScopes, setNewKeyScopes] = useState(['chat', 'read']);
  const [newKeyRateLimit, setNewKeyRateLimit] = useState(100);
  const [createdKey, setCreatedKey] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copiedKeyId, setCopiedKeyId] = useState(null);

  const availableScopes = [
    { id: 'chat', label: 'Chat', description: 'Send messages and run council' },
    { id: 'read', label: 'Read', description: 'Read conversations and history' },
    { id: 'export', label: 'Export', description: 'Export conversations' },
    { id: 'admin', label: 'Admin', description: 'Manage settings and config' },
  ];

  useEffect(() => {
    loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      const response = await api.listAPIKeys();
      setKeys(response.keys || []);
    } catch (error) {
      console.error('Failed to load API keys:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async (e) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    try {
      const result = await api.createAPIKey({
        name: newKeyName.trim(),
        scopes: newKeyScopes,
        rate_limit: newKeyRateLimit,
      });
      setCreatedKey(result);
      setKeys([...keys, {
        id: result.id,
        name: result.name,
        prefix: result.key.substring(0, 12),
        scopes: result.scopes,
        rate_limit: newKeyRateLimit,
        created_at: result.created_at,
      }]);
      setNewKeyName('');
      setNewKeyScopes(['chat', 'read']);
      setNewKeyRateLimit(100);
      setShowCreateForm(false);
    } catch (error) {
      console.error('Failed to create API key:', error);
    }
  };

  const handleRevokeKey = async (keyId) => {
    if (!confirm('Are you sure you want to revoke this API key? This action cannot be undone.')) {
      return;
    }

    try {
      await api.revokeAPIKey(keyId);
      setKeys(keys.filter(k => k.id !== keyId));
    } catch (error) {
      console.error('Failed to revoke API key:', error);
    }
  };

  const copyToClipboard = async (text, keyId) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKeyId(keyId);
      setTimeout(() => setCopiedKeyId(null), 2000);
    } catch (error) {
      console.error('Failed to copy:', error);
    }
  };

  const toggleScope = (scope) => {
    if (newKeyScopes.includes(scope)) {
      setNewKeyScopes(newKeyScopes.filter(s => s !== scope));
    } else {
      setNewKeyScopes([...newKeyScopes, scope]);
    }
  };

  if (loading) {
    return (
      <div className="api-keys-manager">
        <div className="api-keys-header">
          <h2>API Keys</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="loading">Loading API keys...</div>
      </div>
    );
  }

  return (
    <div className="api-keys-manager">
      <div className="api-keys-header">
        <h2>API Keys</h2>
        <button className="close-btn" onClick={onClose}>×</button>
      </div>

      <div className="api-keys-content">
        <div className="api-info">
          <p>
            API keys allow you to access AI Konsey programmatically.
            Keep your keys secure and never share them publicly.
          </p>
          <div className="api-endpoint">
            <span className="endpoint-label">API Endpoint:</span>
            <code>{window.location.origin}/api</code>
          </div>
        </div>

        {createdKey && (
          <div className="created-key-banner">
            <div className="banner-header">
              <span className="banner-icon">🔑</span>
              <span>New API Key Created</span>
            </div>
            <p className="banner-warning">
              Make sure to copy your API key now. You won't be able to see it again!
            </p>
            <div className="key-display">
              <code>{createdKey.key}</code>
              <button
                className="copy-btn"
                onClick={() => copyToClipboard(createdKey.key, 'new')}
              >
                {copiedKeyId === 'new' ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <button
              className="dismiss-btn"
              onClick={() => setCreatedKey(null)}
            >
              I've saved my key
            </button>
          </div>
        )}

        <div className="keys-section">
          <div className="section-header">
            <h3>Your API Keys</h3>
            <button
              className="create-key-btn"
              onClick={() => setShowCreateForm(true)}
            >
              + Create New Key
            </button>
          </div>

          {showCreateForm && (
            <form className="create-key-form" onSubmit={handleCreateKey}>
              <div className="form-group">
                <label>Key Name</label>
                <input
                  type="text"
                  placeholder="e.g., Production API Key"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  autoFocus
                />
              </div>

              <div className="form-group">
                <label>Permissions</label>
                <div className="scopes-grid">
                  {availableScopes.map((scope) => (
                    <label key={scope.id} className="scope-checkbox">
                      <input
                        type="checkbox"
                        checked={newKeyScopes.includes(scope.id)}
                        onChange={() => toggleScope(scope.id)}
                      />
                      <div className="scope-info">
                        <span className="scope-name">{scope.label}</span>
                        <span className="scope-desc">{scope.description}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>Rate Limit (requests/minute)</label>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={newKeyRateLimit}
                  onChange={(e) => setNewKeyRateLimit(parseInt(e.target.value) || 100)}
                />
              </div>

              <div className="form-actions">
                <button type="submit">Create Key</button>
                <button type="button" onClick={() => setShowCreateForm(false)}>
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="keys-list">
            {keys.length === 0 ? (
              <div className="no-keys">
                No API keys yet. Create one to get started!
              </div>
            ) : (
              keys.map((key) => (
                <div key={key.id} className="key-item">
                  <div className="key-info">
                    <div className="key-name">{key.name}</div>
                    <div className="key-meta">
                      <code className="key-prefix">{key.prefix}...</code>
                      <span className="key-scopes">
                        {key.scopes?.join(', ')}
                      </span>
                      <span className="key-rate">
                        {key.rate_limit} req/min
                      </span>
                    </div>
                    <div className="key-dates">
                      Created: {new Date(key.created_at).toLocaleDateString()}
                      {key.last_used && (
                        <span> | Last used: {new Date(key.last_used).toLocaleDateString()}</span>
                      )}
                    </div>
                  </div>
                  <button
                    className="revoke-btn"
                    onClick={() => handleRevokeKey(key.id)}
                  >
                    Revoke
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="usage-example">
          <h3>Usage Example</h3>
          <pre><code>{`curl -X POST ${window.location.origin}/api/v1/chat \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Hello, Council!"}'`}</code></pre>
        </div>
      </div>
    </div>
  );
}
