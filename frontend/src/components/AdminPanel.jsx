import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { API_BASE } from '../api/client';
import './AdminPanel.css';

export default function AdminPanel({ isOpen, onClose }) {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('users'); // 'users' or 'api-keys'
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const limit = 20;
  
  // API Keys state
  const [systemApiKeys, setSystemApiKeys] = useState({});
  const [apiKeysLoading, setApiKeysLoading] = useState(false);
  const [editingProvider, setEditingProvider] = useState(null);
  const [newApiKey, setNewApiKey] = useState('');

  useEffect(() => {
    if (isOpen && user?.is_admin) {
      if (activeTab === 'users') {
        loadUsers();
        loadUserCount();
      } else if (activeTab === 'api-keys') {
        loadSystemApiKeys();
      }
    }
  }, [isOpen, page, user, activeTab]);

  const loadUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_BASE}/auth/admin/users?page=${page}&limit=${limit}&active_only=true`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        if (response.status === 403) {
          setError('Admin privileges required');
          return;
        }
        throw new Error(`Failed to load users: ${response.statusText}`);
      }

      const data = await response.json();
      setUsers(data);
    } catch (err) {
      setError(err.message || 'Failed to load users');
      console.error('Error loading users:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadUserCount = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_BASE}/auth/admin/users/count?active_only=true`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setTotalUsers(data.total_users || 0);
      }
    } catch (err) {
      console.error('Error loading user count:', err);
    }
  };

  const loadSystemApiKeys = async () => {
    setApiKeysLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_BASE}/auth/admin/api-keys`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        if (response.status === 403) {
          setError('Admin privileges required');
          return;
        }
        throw new Error(`Failed to load API keys: ${response.statusText}`);
      }

      const data = await response.json();
      setSystemApiKeys(data.api_keys || {});
    } catch (err) {
      setError(err.message || 'Failed to load API keys');
      console.error('Error loading API keys:', err);
    } finally {
      setApiKeysLoading(false);
    }
  };

  const handleSetApiKey = async (provider) => {
    if (!newApiKey.trim()) {
      alert('Please enter an API key');
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_BASE}/auth/admin/api-keys`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            provider: provider,
            api_key: newApiKey.trim(),
          }),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to set API key');
      }

      // Reload API keys
      await loadSystemApiKeys();
      setEditingProvider(null);
      setNewApiKey('');
      alert('API key set successfully!');
    } catch (err) {
      alert(`Failed to set API key: ${err.message}`);
      console.error('Error setting API key:', err);
    }
  };

  const handleDeleteApiKey = async (provider) => {
    if (!confirm(`Are you sure you want to delete the system API key for ${provider}?`)) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `${API_BASE}/auth/admin/api-keys/${provider}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete API key');
      }

      // Reload API keys
      await loadSystemApiKeys();
      alert('API key deleted successfully!');
    } catch (err) {
      alert(`Failed to delete API key: ${err.message}`);
      console.error('Error deleting API key:', err);
    }
  };

  if (!isOpen) return null;

  if (!user?.is_admin) {
    return (
      <div className="admin-panel-overlay" onClick={onClose}>
        <div className="admin-panel" onClick={(e) => e.stopPropagation()}>
          <div className="admin-panel-header">
            <h2>Admin Panel</h2>
            <button className="close-button" onClick={onClose}>×</button>
          </div>
          <div className="admin-panel-content">
            <p className="admin-error">You do not have admin privileges.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-panel-overlay" onClick={onClose}>
      <div className="admin-panel" onClick={(e) => e.stopPropagation()}>
        <div className="admin-panel-header">
          <h2>Admin Panel</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        {/* Tabs */}
        <div className="admin-tabs">
          <button
            className={`admin-tab ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            Users
          </button>
          <button
            className={`admin-tab ${activeTab === 'api-keys' ? 'active' : ''}`}
            onClick={() => setActiveTab('api-keys')}
          >
            System API Keys
          </button>
        </div>

        <div className="admin-panel-content">
          {error && (
            <div className="admin-error-message">
              {error}
            </div>
          )}

          <div className="admin-stats">
            <div className="stat-card">
              <div className="stat-value">{totalUsers}</div>
              <div className="stat-label">Total Users</div>
            </div>
          </div>

          {activeTab === 'users' ? (
            <>
              {loading ? (
                <div className="admin-loading">Loading users...</div>
              ) : (
                <>
                  <div className="users-table-container">
                    <table className="users-table">
                      <thead>
                        <tr>
                          <th>Email</th>
                          <th>Name</th>
                          <th>Status</th>
                          <th>Admin</th>
                          <th>Verified</th>
                          <th>Joined</th>
                        </tr>
                      </thead>
                      <tbody>
                        {users.length === 0 ? (
                          <tr>
                            <td colSpan="6" className="no-users">
                              No users found
                            </td>
                          </tr>
                        ) : (
                          users.map((u) => (
                            <tr key={u.id}>
                              <td>{u.email}</td>
                              <td>{u.name || '-'}</td>
                              <td>
                                <span className={`status-badge ${u.is_active ? 'active' : 'inactive'}`}>
                                  {u.is_active ? 'Active' : 'Inactive'}
                                </span>
                              </td>
                              <td>
                                {u.is_admin && (
                                  <span className="admin-badge">Admin</span>
                                )}
                              </td>
                              <td>
                                {u.is_verified && (
                                  <span className="verified-badge">✓</span>
                                )}
                              </td>
                              <td>{new Date(u.created_at).toLocaleDateString()}</td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>

                  <div className="admin-pagination">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1 || loading}
                    >
                      Previous
                    </button>
                    <span>Page {page}</span>
                    <button
                      onClick={() => setPage(p => p + 1)}
                      disabled={users.length < limit || loading}
                    >
                      Next
                    </button>
                  </div>
                </>
              )}
            </>
          ) : (
            <>
              <div className="admin-section-header">
                <h3>System API Keys</h3>
                <p className="admin-hint">
                  Set system-wide API keys that will be used as fallback when users don't have their own keys.
                  Users with their own keys will always use their keys first.
                </p>
              </div>

              {apiKeysLoading ? (
                <div className="admin-loading">Loading API keys...</div>
              ) : (
                <div className="api-keys-list">
                  {['openrouter', 'openai', 'anthropic', 'google', 'x-ai', 'deepseek', 'mistralai', 'cohere', 'qwen'].map((provider) => (
                    <div key={provider} className="api-key-item">
                      <div className="api-key-header">
                        <span className="api-key-provider">{provider.toUpperCase()}</span>
                        {systemApiKeys[provider] && systemApiKeys[provider] !== '' ? (
                          <span className="api-key-status has-key">Key Set</span>
                        ) : (
                          <span className="api-key-status no-key">No Key</span>
                        )}
                      </div>
                      
                      {editingProvider === provider ? (
                        <div className="api-key-edit">
                          <input
                            type="password"
                            value={newApiKey}
                            onChange={(e) => setNewApiKey(e.target.value)}
                            placeholder={`Enter ${provider} API key`}
                            className="api-key-input"
                          />
                          <div className="api-key-actions">
                            <button
                              onClick={() => handleSetApiKey(provider)}
                              className="api-key-save"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => {
                                setEditingProvider(null);
                                setNewApiKey('');
                              }}
                              className="api-key-cancel"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="api-key-display">
                          <span className="api-key-value">
                            {systemApiKeys[provider] && systemApiKeys[provider] !== '' 
                              ? systemApiKeys[provider] 
                              : 'Not set'}
                          </span>
                          <div className="api-key-actions">
                            <button
                              onClick={() => {
                                setEditingProvider(provider);
                                setNewApiKey('');
                              }}
                              className="api-key-edit-btn"
                            >
                              {systemApiKeys[provider] && systemApiKeys[provider] !== '' ? 'Edit' : 'Set Key'}
                            </button>
                            {systemApiKeys[provider] && systemApiKeys[provider] !== '' && (
                              <button
                                onClick={() => handleDeleteApiKey(provider)}
                                className="api-key-delete"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
