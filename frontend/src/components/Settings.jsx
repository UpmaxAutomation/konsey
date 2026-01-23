import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';
import { useTheme } from '../contexts/ThemeContext';
import ThemeToggle from './ThemeToggle';
import './Settings.css';

const CUSTOM_PRESETS_KEY = 'llm-council-custom-presets';

// Load custom presets from localStorage
const loadCustomPresets = () => {
  try {
    const stored = localStorage.getItem(CUSTOM_PRESETS_KEY);
    return stored ? JSON.parse(stored) : {};
  } catch (e) {
    console.error('Failed to load custom presets:', e);
    return {};
  }
};

// Save custom presets to localStorage
const saveCustomPresets = (presets) => {
  try {
    localStorage.setItem(CUSTOM_PRESETS_KEY, JSON.stringify(presets));
  } catch (e) {
    console.error('Failed to save custom presets:', e);
  }
};

export default function Settings({ isOpen, onClose }) {
  const { theme } = useTheme();
  const [activeTab, setActiveTab] = useState('routing');
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // API Keys state
  const [apiKeys, setApiKeys] = useState({});
  const [apiKeyInputs, setApiKeyInputs] = useState({});
  const [savingKey, setSavingKey] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // OpenRouter key status (for model availability)
  const [hasOpenRouterKey, setHasOpenRouterKey] = useState(false);

  // Model selection state
  const [selectedCouncil, setSelectedCouncil] = useState([]);
  const [selectedChairman, setSelectedChairman] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [providerFilter, setProviderFilter] = useState('all');

  // Presets state
  const [builtInPresets, setBuiltInPresets] = useState([]);
  const [customPresets, setCustomPresets] = useState({});
  const [selectedPreset, setSelectedPreset] = useState('');
  const [showSavePresetModal, setShowSavePresetModal] = useState(false);
  const [newPresetName, setNewPresetName] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [configData, keysData, presetsData] = await Promise.all([
        api.getConfig(),
        api.getApiKeys(),
        api.getPresets(),
      ]);
      setConfig(configData);
      setSelectedCouncil(configData.council_models);
      setSelectedChairman(configData.chairman_model);
      setApiKeys(keysData.api_keys || {});
      // Check if OpenRouter key is configured (non-empty masked key)
      setHasOpenRouterKey(!!(keysData.api_keys?.openrouter));
      setBuiltInPresets(presetsData.presets || []);
      setCustomPresets(loadCustomPresets());
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
    setLoading(false);
  };

  // Provider definitions with status
  const providers = [
    { id: 'openrouter', name: 'OpenRouter', models: 'All models via OpenRouter', hint: 'sk-or-v1-...', priority: true },
    { id: 'openai', name: 'OpenAI', models: 'GPT-4o, GPT-4.1, o1, o3', hint: 'sk-...' },
    { id: 'anthropic', name: 'Anthropic', models: 'Claude 4, Sonnet, Opus', hint: 'sk-ant-...' },
    { id: 'google', name: 'Google', models: 'Gemini 2.5, 2.0 Flash', hint: 'AIza...' },
    { id: 'x-ai', name: 'xAI', models: 'Grok 3, Grok 2', hint: 'xai-...' },
    { id: 'deepseek', name: 'DeepSeek', models: 'DeepSeek V3, R1', hint: 'sk-...' },
    { id: 'mistralai', name: 'Mistral', models: 'Large, Medium, Codestral', hint: '' },
    { id: 'qwen', name: 'Qwen', models: 'Qwen 3, QwQ, Coder', hint: 'sk-...' },
    { id: 'cohere', name: 'Cohere', models: 'Command R+', hint: '' },
  ];

  // Clear messages after 3 seconds
  const showMessage = (type, message) => {
    if (type === 'error') {
      setError(message);
      setSuccess(null);
    } else {
      setSuccess(message);
      setError(null);
    }
    setTimeout(() => {
      setError(null);
      setSuccess(null);
    }, 3000);
  };

  const handleSaveApiKey = async (provider) => {
    const key = apiKeyInputs[provider];
    if (!key) return;

    setSavingKey(provider);
    setError(null);
    try {
      await api.setApiKey(provider, key);
      const keysData = await api.getApiKeys();
      setApiKeys(keysData.api_keys || {});
      setApiKeyInputs({ ...apiKeyInputs, [provider]: '' });
      showMessage('success', `${provider} API key saved successfully`);
    } catch (err) {
      showMessage('error', `Failed to save ${provider} API key: ${err.message || 'Unknown error'}`);
    } finally {
      setSavingKey(null);
    }
  };

  const handleDeleteApiKey = async (provider) => {
    setSavingKey(provider);
    setError(null);
    try {
      await api.deleteApiKey(provider);
      const keysData = await api.getApiKeys();
      setApiKeys(keysData.api_keys || {});
      showMessage('success', `${provider} API key removed`);
    } catch (err) {
      showMessage('error', `Failed to remove ${provider} API key: ${err.message || 'Unknown error'}`);
    } finally {
      setSavingKey(null);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    
    // Validate chairman selection
    if (!selectedChairman) {
      showMessage('error', 'Please select a chairman model');
      setSaving(false);
      return;
    }
    
    // Validate council models
    if (selectedCouncil.length === 0) {
      showMessage('error', 'Please select at least one council model');
      setSaving(false);
      return;
    }
    
    try {
      await api.updateConfig({
        council_models: selectedCouncil,
        chairman_model: selectedChairman,
      });
      showMessage('success', 'Settings saved successfully');
      setTimeout(() => onClose(), 500);
    } catch (err) {
      showMessage('error', `Failed to save settings: ${err.message || 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  // Preset handlers
  const handlePresetChange = async (presetValue) => {
    setSelectedPreset(presetValue);

    if (!presetValue) return;

    // Check if it's a custom preset
    if (presetValue.startsWith('custom:')) {
      const customId = presetValue.replace('custom:', '');
      const preset = customPresets[customId];
      if (preset) {
        setSelectedCouncil(preset.council_models);
        setSelectedChairman(preset.chairman_model);
        showMessage('success', `Loaded preset: ${preset.name}`);
      }
    } else {
      // Built-in preset - apply via API
      try {
        const result = await api.applyPreset(presetValue);
        setSelectedCouncil(result.council_models);
        setSelectedChairman(result.chairman_model);
        showMessage('success', `Applied preset: ${result.preset_name}`);
      } catch (err) {
        showMessage('error', `Failed to apply preset: ${err.message || 'Unknown error'}`);
      }
    }
  };

  const handleSaveAsPreset = () => {
    if (selectedCouncil.length === 0) {
      showMessage('error', 'Please select at least one council model');
      return;
    }
    if (!selectedChairman) {
      showMessage('error', 'Please select a chairman model');
      return;
    }
    setNewPresetName('');
    setShowSavePresetModal(true);
  };

  const handleConfirmSavePreset = () => {
    const name = newPresetName.trim();
    if (!name) {
      showMessage('error', 'Please enter a preset name');
      return;
    }

    // Generate a unique ID from the name
    const id = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

    // Check for duplicate names
    const existingCustom = Object.values(customPresets).find(p => p.name.toLowerCase() === name.toLowerCase());
    if (existingCustom) {
      showMessage('error', 'A preset with this name already exists');
      return;
    }

    const newPreset = {
      name,
      council_models: [...selectedCouncil],
      chairman_model: selectedChairman,
    };

    const updatedPresets = { ...customPresets, [id]: newPreset };
    setCustomPresets(updatedPresets);
    saveCustomPresets(updatedPresets);
    setShowSavePresetModal(false);
    setNewPresetName('');
    showMessage('success', `Preset "${name}" saved successfully`);
  };

  const handleDeleteCustomPreset = (presetId) => {
    const preset = customPresets[presetId];
    if (!preset) return;

    const updatedPresets = { ...customPresets };
    delete updatedPresets[presetId];
    setCustomPresets(updatedPresets);
    saveCustomPresets(updatedPresets);

    if (selectedPreset === `custom:${presetId}`) {
      setSelectedPreset('');
    }

    showMessage('success', `Preset "${preset.name}" deleted`);
  };

  const toggleModel = (modelId) => {
    if (selectedCouncil.includes(modelId)) {
      setSelectedCouncil(selectedCouncil.filter((m) => m !== modelId));
    } else {
      setSelectedCouncil([...selectedCouncil, modelId]);
    }
  };

  // Get provider from model ID
  const getProvider = (modelId) => {
    return modelId.split('/')[0] || 'other';
  };

  // Check if using direct API for a provider
  const isUsingDirectApi = (providerId) => {
    return !!apiKeys[providerId];
  };

  // Check if a model is available (has direct API key OR has OpenRouter fallback)
  const isModelAvailable = (modelId) => {
    const provider = getProvider(modelId);
    // Model is available if it has a direct API key OR OpenRouter is configured
    return !!apiKeys[provider] || hasOpenRouterKey;
  };

  // Count models by provider
  const modelsByProvider = useMemo(() => {
    if (!config) return {};
    const counts = {};
    Object.keys(config.available_models).forEach(id => {
      const provider = getProvider(id);
      counts[provider] = (counts[provider] || 0) + 1;
    });
    return counts;
  }, [config]);

  // Check if model is free
  const isFreeModel = (modelId, info) => {
    return modelId.includes(':free') ||
           info?.input_cost === 0 ||
           (info?.input_cost === 0.0 && info?.output_cost === 0.0);
  };

  // Check if model is "latest" (released in last year, or has latest/new in name)
  const isLatestModel = (modelId, info) => {
    const latestPatterns = /gpt-5|gpt-4\.1|o3|o4|claude-opus-4|claude-sonnet-4|gemini-3|gemini-2\.5|grok-4|llama-4|r1-0528|deepseek-r1/i;
    return latestPatterns.test(modelId) || latestPatterns.test(info?.name || '');
  };

  // Check if model is reasoning model
  const isReasoningModel = (modelId) => {
    return /\b(o1|o3|o4|r1|qwq)\b/i.test(modelId);
  };

  // Check if model is deep search/research model
  const isDeepSearchModel = (modelId, info) => {
    const deepPatterns = /deep-research|deep-search|perplexity|sonar|grounded|search/i;
    return deepPatterns.test(modelId) || deepPatterns.test(info?.name || '');
  };

  // Filter models
  const filteredModels = useMemo(() => {
    if (!config) return [];
    let models = Object.entries(config.available_models);

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      models = models.filter(([id, info]) =>
        id.toLowerCase().includes(q) || info.name.toLowerCase().includes(q)
      );
    }

    if (providerFilter === 'free') {
      models = models.filter(([id, info]) => isFreeModel(id, info));
    } else if (providerFilter === 'latest') {
      models = models.filter(([id, info]) => isLatestModel(id, info));
    } else if (providerFilter === 'selected') {
      models = models.filter(([id]) => selectedCouncil.includes(id));
    } else if (providerFilter === 'reasoning') {
      models = models.filter(([id]) => isReasoningModel(id));
    } else if (providerFilter === 'deepsearch') {
      models = models.filter(([id, info]) => isDeepSearchModel(id, info));
    } else if (providerFilter !== 'all') {
      models = models.filter(([id]) => getProvider(id) === providerFilter);
    }

    // Sort: selected first, then by name
    return models.sort((a, b) => {
      const aSelected = selectedCouncil.includes(a[0]);
      const bSelected = selectedCouncil.includes(b[0]);
      if (aSelected && !bSelected) return -1;
      if (!aSelected && bSelected) return 1;
      return a[1].name.localeCompare(b[1].name);
    });
  }, [config, searchQuery, providerFilter, selectedCouncil]);

  // Get unique providers from models
  const availableProviders = useMemo(() => {
    if (!config) return [];
    const providerSet = new Set(Object.keys(config.available_models).map(getProvider));
    return Array.from(providerSet).sort();
  }, [config]);

  // Count configured direct APIs
  const directApiCount = Object.keys(apiKeys).filter(k => apiKeys[k]).length;

  if (!isOpen) return null;

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
        {/* Toast notifications */}
        {error && (
          <div className="settings-toast error">
            <span className="toast-icon">❌</span>
            {error}
          </div>
        )}
        {success && (
          <div className="settings-toast success">
            <span className="toast-icon">✓</span>
            {success}
          </div>
        )}

        {/* Header with tabs */}
        <div className="settings-header">
          <div className="settings-tabs">
            <button
              className={`settings-tab ${activeTab === 'routing' ? 'active' : ''}`}
              onClick={() => setActiveTab('routing')}
            >
              <span className="tab-icon">🔀</span>
              API Routing
              {directApiCount > 0 && (
                <span className="tab-badge">{directApiCount} direct</span>
              )}
            </button>
            <button
              className={`settings-tab ${activeTab === 'models' ? 'active' : ''}`}
              onClick={() => setActiveTab('models')}
            >
              <span className="tab-icon">🤖</span>
              Council Models
              <span className="tab-badge">{selectedCouncil.length}</span>
            </button>
            <button
              className={`settings-tab ${activeTab === 'teams' ? 'active' : ''}`}
              onClick={() => setActiveTab('teams')}
            >
              <span className="tab-icon">👥</span>
              Teams
            </button>
            <button
              className={`settings-tab ${activeTab === 'apikeys' ? 'active' : ''}`}
              onClick={() => setActiveTab('apikeys')}
            >
              <span className="tab-icon">🔑</span>
              API Keys
            </button>
            <button
              className={`settings-tab ${activeTab === 'analytics' ? 'active' : ''}`}
              onClick={() => setActiveTab('analytics')}
            >
              <span className="tab-icon">📊</span>
              Analytics
            </button>
            <button
              className={`settings-tab ${activeTab === 'appearance' ? 'active' : ''}`}
              onClick={() => setActiveTab('appearance')}
            >
              <span className="tab-icon">{theme === 'dark' ? '🌙' : '☀️'}</span>
              Theme
            </button>
          </div>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {loading ? (
          <div className="settings-loading">Loading...</div>
        ) : (
          <div className="settings-content">
            {/* Tab: API Routing */}
            {activeTab === 'routing' && (
              <div className="tab-content">
                {/* Warning banner if OpenRouter key is missing */}
                {!hasOpenRouterKey && (
                  <div className="api-key-warning">
                    <div className="warning-icon">⚠️</div>
                    <div className="warning-content">
                      <strong>OpenRouter API Key Required</strong>
                      <p>
                        You need to configure an OpenRouter API key to access models. Without it, the council system cannot function.
                        {' '}
                        <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="warning-link">
                          Get your key at openrouter.ai →
                        </a>
                      </p>
                    </div>
                  </div>
                )}
                
                {/* Current Status Banner */}
                <div className="routing-status">
                  <div className="status-header">
                    <h3>Current API Status</h3>
                  </div>
                  <div className="status-summary">
                    <div className="status-item">
                      <span className="status-count">{directApiCount}</span>
                      <span className="status-label">Direct APIs</span>
                    </div>
                    <div className="status-item">
                      <span className="status-count">{providers.length - directApiCount}</span>
                      <span className="status-label">Via OpenRouter</span>
                    </div>
                  </div>
                </div>

                {/* Provider Cards */}
                <div className="provider-grid">
                  {providers
                    .sort((a, b) => {
                      // Sort OpenRouter first if it has priority flag
                      if (a.priority && !b.priority) return -1;
                      if (!a.priority && b.priority) return 1;
                      return 0;
                    })
                    .map(provider => {
                    const isDirect = isUsingDirectApi(provider.id);
                    const modelCount = modelsByProvider[provider.id] || 0;
                    const isOpenRouter = provider.id === 'openrouter';

                    return (
                      <div key={provider.id} className={`provider-card ${isDirect ? 'direct' : 'openrouter'}`}>
                        <div className="provider-header">
                          <div className="provider-info">
                            <h4 className="provider-name">{provider.name}</h4>
                            <p className="provider-models">{provider.models}</p>
                          </div>
                          <div className={`provider-status ${isDirect ? 'direct' : 'openrouter'}`}>
                            {isDirect ? (
                              <>
                                <span className="status-dot"></span>
                                Direct API
                              </>
                            ) : (
                              <>
                                <span className="status-dot"></span>
                                {isOpenRouter ? 'Required' : 'OpenRouter'}
                              </>
                            )}
                          </div>
                        </div>

                        {isDirect ? (
                          <div className="provider-configured">
                            <div className="configured-key">
                              <span className="key-mask">{apiKeys[provider.id]}</span>
                              <button
                                className="remove-key-btn"
                                onClick={() => handleDeleteApiKey(provider.id)}
                                disabled={savingKey === provider.id}
                              >
                                {savingKey === provider.id ? '...' : 'Remove'}
                              </button>
                            </div>
                            <p className="configured-note">
                              {modelCount} models available • Using direct API (faster, often cheaper)
                            </p>
                          </div>
                        ) : (
                          <div className="provider-setup">
                            <div className="setup-input-row">
                              <input
                                type="password"
                                className="api-key-input"
                                placeholder={provider.hint || 'Enter API key...'}
                                value={apiKeyInputs[provider.id] || ''}
                                onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, [provider.id]: e.target.value })}
                                onKeyDown={(e) => e.key === 'Enter' && handleSaveApiKey(provider.id)}
                              />
                              <button
                                className="save-key-btn"
                                onClick={() => handleSaveApiKey(provider.id)}
                                disabled={savingKey === provider.id || !apiKeyInputs[provider.id]}
                              >
                                {savingKey === provider.id ? '...' : 'Add'}
                              </button>
                            </div>
                            <p className="setup-note">
                              {isOpenRouter 
                                ? 'Required for accessing all models. Get your key at openrouter.ai'
                                : `${modelCount} models • Currently routed through OpenRouter`}
                            </p>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* OpenRouter Info */}
                <div className="openrouter-info">
                  <div className="info-icon">ℹ️</div>
                  <div className="info-content">
                    <strong>About OpenRouter</strong>
                    <p>
                      Models without direct API keys are routed through OpenRouter, which provides
                      unified access to 200+ models. Add your own API keys above to use providers
                      directly for potentially lower costs and faster responses.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Tab: Council Models */}
            {activeTab === 'models' && (
              <div className="tab-content">
                {/* Presets Section */}
                <div className="presets-section">
                  <div className="presets-header">
                    <label className="presets-label">Council Presets</label>
                    <button
                      className="save-preset-btn"
                      onClick={handleSaveAsPreset}
                      title="Save current configuration as a custom preset"
                    >
                      + Save as Preset
                    </button>
                  </div>
                  <div className="presets-row">
                    <select
                      className="preset-select"
                      value={selectedPreset}
                      onChange={(e) => handlePresetChange(e.target.value)}
                    >
                      <option value="">-- Select a preset --</option>
                      {builtInPresets.length > 0 && (
                        <optgroup label="Built-in Presets">
                          {builtInPresets.map(preset => (
                            <option key={preset.id} value={preset.id}>
                              {preset.name}
                            </option>
                          ))}
                        </optgroup>
                      )}
                      {Object.keys(customPresets).length > 0 && (
                        <optgroup label="Custom Presets">
                          {Object.entries(customPresets).map(([id, preset]) => (
                            <option key={id} value={`custom:${id}`}>
                              {preset.name}
                            </option>
                          ))}
                        </optgroup>
                      )}
                    </select>
                    {selectedPreset.startsWith('custom:') && (
                      <button
                        className="delete-preset-btn"
                        onClick={() => handleDeleteCustomPreset(selectedPreset.replace('custom:', ''))}
                        title="Delete this custom preset"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                  {selectedPreset && !selectedPreset.startsWith('custom:') && (
                    <p className="preset-description">
                      {builtInPresets.find(p => p.id === selectedPreset)?.description || ''}
                    </p>
                  )}
                </div>

                {/* Selected Models Summary */}
                {selectedCouncil.length > 0 && (
                  <div className="selected-models-summary">
                    <div className="selected-header">
                      <span className="selected-title">
                        <span className="selected-icon">✓</span>
                        {selectedCouncil.length} Model{selectedCouncil.length !== 1 ? 's' : ''} Selected
                      </span>
                      <button
                        className="clear-all-btn"
                        onClick={() => setSelectedCouncil([])}
                      >
                        Clear All
                      </button>
                    </div>
                    <div className="selected-chips">
                      {selectedCouncil.map(modelId => {
                        const info = config.available_models[modelId];
                        return (
                          <div key={modelId} className="selected-chip">
                            <span className="chip-name">{info?.name || modelId.split('/')[1]}</span>
                            <button
                              className="chip-remove"
                              onClick={() => setSelectedCouncil(selectedCouncil.filter(m => m !== modelId))}
                            >
                              ×
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Search */}
                <div className="models-search">
                  <div className="search-box">
                    <span className="search-icon">🔍</span>
                    <input
                      type="text"
                      placeholder="Search by name, provider, or capability..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                    {searchQuery && (
                      <button className="clear-search" onClick={() => setSearchQuery('')}>×</button>
                    )}
                  </div>
                </div>

                {/* Filter Chips */}
                <div className="filter-chips">
                  <button
                    className={`filter-chip ${providerFilter === 'all' ? 'active' : ''}`}
                    onClick={() => setProviderFilter('all')}
                  >
                    All ({config ? Object.keys(config.available_models).length : 0})
                  </button>
                  <button
                    className={`filter-chip ${providerFilter === 'free' ? 'active' : ''}`}
                    onClick={() => setProviderFilter('free')}
                  >
                    💚 Free
                  </button>
                  <button
                    className={`filter-chip ${providerFilter === 'latest' ? 'active' : ''}`}
                    onClick={() => setProviderFilter('latest')}
                  >
                    ✨ Latest
                  </button>
                  <button
                    className={`filter-chip ${providerFilter === 'reasoning' ? 'active' : ''}`}
                    onClick={() => setProviderFilter('reasoning')}
                  >
                    🧠 Reasoning
                  </button>
                  <button
                    className={`filter-chip ${providerFilter === 'deepsearch' ? 'active' : ''}`}
                    onClick={() => setProviderFilter('deepsearch')}
                  >
                    🔬 Deep Search
                  </button>
                  <div className="filter-divider"></div>
                  {availableProviders.slice(0, 6).map(p => (
                    <button
                      key={p}
                      className={`filter-chip provider-chip ${providerFilter === p ? 'active' : ''}`}
                      onClick={() => setProviderFilter(p)}
                    >
                      {p}
                    </button>
                  ))}
                  {availableProviders.length > 6 && (
                    <select
                      className="more-providers"
                      value={availableProviders.slice(6).includes(providerFilter) ? providerFilter : ''}
                      onChange={(e) => e.target.value && setProviderFilter(e.target.value)}
                    >
                      <option value="">More...</option>
                      {availableProviders.slice(6).map(p => (
                        <option key={p} value={p}>{p} ({modelsByProvider[p] || 0})</option>
                      ))}
                    </select>
                  )}
                </div>

                {/* Quick Select Actions */}
                <div className="quick-select-actions">
                  <span className="quick-label">Quick Select:</span>
                  <button onClick={() => {
                    const free = Object.entries(config.available_models)
                      .filter(([id, info]) => isFreeModel(id, info))
                      .map(([id]) => id);
                    setSelectedCouncil(free);
                  }}>
                    Select All Free
                  </button>
                  <button onClick={() => {
                    const latest = Object.entries(config.available_models)
                      .filter(([id, info]) => isLatestModel(id, info))
                      .map(([id]) => id);
                    setSelectedCouncil(latest);
                  }}>
                    Select Latest
                  </button>
                  <button onClick={() => {
                    const reasoning = Object.keys(config.available_models).filter(id =>
                      /\b(o1|o3|o4|r1|qwq)\b/i.test(id)
                    );
                    setSelectedCouncil(reasoning);
                  }}>
                    Select Reasoning
                  </button>
                  <button onClick={() => {
                    const deepSearch = Object.entries(config.available_models)
                      .filter(([id, info]) => isDeepSearchModel(id, info))
                      .map(([id]) => id);
                    setSelectedCouncil(deepSearch);
                  }}>
                    Select Deep Search
                  </button>
                  <button onClick={() => {
                    // Select visible models
                    const visibleIds = filteredModels.map(([id]) => id);
                    const newSelection = [...new Set([...selectedCouncil, ...visibleIds])];
                    setSelectedCouncil(newSelection);
                  }}>
                    Select Visible
                  </button>
                </div>

                {/* Results Count */}
                <div className="results-count">
                  Showing {filteredModels.length} of {config ? Object.keys(config.available_models).length : 0} model{filteredModels.length !== 1 ? 's' : ''}
                  {providerFilter !== 'all' && ` in "${providerFilter}"`}
                  {searchQuery && ` matching "${searchQuery}"`}
                  {selectedCouncil.length > 0 && ` • ${selectedCouncil.length} selected`}
                </div>

                {/* Model List */}
                <div className="models-list">
                  {filteredModels.map(([modelId, info]) => {
                    const isSelected = selectedCouncil.includes(modelId);
                    const provider = getProvider(modelId);
                    const isDirect = isUsingDirectApi(provider);
                    const isFree = isFreeModel(modelId, info);
                    const isLatest = isLatestModel(modelId, info);
                    const isReasoning = /\b(o1|o3|o4|r1|qwq)\b/i.test(modelId);
                    const isDeepSearch = isDeepSearchModel(modelId, info);
                    const isAvailable = isModelAvailable(modelId);

                    return (
                      <div
                        key={modelId}
                        className={`model-card ${isSelected ? 'selected' : ''} ${!isAvailable ? 'unavailable' : ''}`}
                        onClick={() => toggleModel(modelId)}
                      >
                        <div className="model-checkbox">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {}}
                          />
                        </div>
                        <div className="model-info">
                          <div className="model-header">
                            <div className="model-name-wrapper">
                              <span className={`availability-dot ${isAvailable ? 'available' : 'unavailable'}`} title={isAvailable ? 'API available' : 'No API key configured'}></span>
                              <span className="model-name">{info.name}</span>
                            </div>
                            <div className="model-badges">
                              {isFree && <span className="badge free">FREE</span>}
                              {isLatest && <span className="badge latest">NEW</span>}
                              {isReasoning && <span className="badge reasoning">🧠</span>}
                              {isDeepSearch && <span className="badge deepsearch">🔬</span>}
                            </div>
                          </div>
                          <div className="model-footer">
                            <span className="model-provider">{provider}</span>
                            <span className={`model-route ${isDirect ? 'direct' : ''}`}>
                              {isDirect ? '⚡ Direct' : 'OpenRouter'}
                            </span>
                            <span className="model-cost">
                              ${info.input_cost} / ${info.output_cost}
                            </span>
                          </div>
                        </div>
                        {isSelected && (
                          <div className="model-selected-indicator">✓</div>
                        )}
                      </div>
                    );
                  })}
                  {filteredModels.length === 0 && (
                    <div className="no-models">
                      No models found. Try adjusting your search or filters.
                    </div>
                  )}
                </div>

                {/* Chairman Selection */}
                <div className="chairman-section">
                  <label className="chairman-label">Chairman Model (synthesizes final answer)</label>
                  <select
                    className="chairman-select"
                    value={selectedChairman || ''}
                    onChange={(e) => setSelectedChairman(e.target.value)}
                    required
                  >
                    <option value="">-- Select Chairman Model --</option>
                    {config && Object.entries(config.available_models).map(([modelId, info]) => (
                      <option key={modelId} value={modelId}>{info.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {/* Teams Tab */}
            {activeTab === 'teams' && (
              <div className="settings-section teams-section">
                <div className="section-intro">
                  <h3>Team Workspaces</h3>
                  <p>Collaborate with your team by sharing conversations and council configurations.</p>
                </div>
                <div className="team-placeholder">
                  <div className="placeholder-icon">👥</div>
                  <h4>Team Workspaces</h4>
                  <p>Create teams, invite members, and share conversations collaboratively.</p>
                  <button
                    className="open-teams-btn"
                    onClick={() => {
                      onClose();
                      window.dispatchEvent(new CustomEvent('openTeamManager'));
                    }}
                  >
                    Open Team Manager
                  </button>
                </div>
              </div>
            )}

            {/* API Keys Tab */}
            {activeTab === 'apikeys' && (
              <div className="settings-section apikeys-section">
                <div className="section-intro">
                  <h3>Public API Access</h3>
                  <p>Create API keys to access AI Konsey programmatically from your applications.</p>
                </div>
                <div className="apikeys-placeholder">
                  <div className="placeholder-icon">🔑</div>
                  <h4>API Keys</h4>
                  <p>Generate and manage API keys with custom scopes and rate limits.</p>
                  <button
                    className="open-apikeys-btn"
                    onClick={() => {
                      onClose();
                      window.dispatchEvent(new CustomEvent('openAPIKeysManager'));
                    }}
                  >
                    Manage API Keys
                  </button>
                </div>
              </div>
            )}

            {/* Analytics Tab */}
            {activeTab === 'analytics' && (
              <div className="settings-section analytics-section">
                <div className="section-intro">
                  <h3>Usage Analytics</h3>
                  <p>Track your usage, costs, and model performance over time.</p>
                </div>
                <div className="analytics-placeholder">
                  <div className="placeholder-icon">📊</div>
                  <h4>Analytics Dashboard</h4>
                  <p>View detailed usage statistics, cost breakdowns, and trends.</p>
                  <button
                    className="open-analytics-btn"
                    onClick={() => {
                      onClose();
                      window.dispatchEvent(new CustomEvent('openAnalytics'));
                    }}
                  >
                    Open Analytics Dashboard
                  </button>
                </div>
              </div>
            )}

            {/* Appearance Tab */}
            {activeTab === 'appearance' && (
              <div className="settings-section appearance-section">
                <div className="section-intro">
                  <h3>Appearance</h3>
                  <p>Customize how AI Konsey looks and feels.</p>
                </div>

                <div className="appearance-option">
                  <div className="option-info">
                    <h4>Theme</h4>
                    <p>Choose between light and dark mode. The system preference is detected automatically on first visit.</p>
                  </div>
                  <div className="option-control">
                    <ThemeToggle showLabel />
                  </div>
                </div>

                <div className="theme-preview">
                  <div className="preview-cards">
                    <div className={`preview-card ${theme === 'light' ? 'active' : ''}`}>
                      <div className="preview-header light-preview">
                        <span className="preview-icon">☀️</span>
                        <span className="preview-title">Light Mode</span>
                      </div>
                      <div className="preview-body light-preview">
                        <div className="preview-line"></div>
                        <div className="preview-line short"></div>
                      </div>
                    </div>
                    <div className={`preview-card ${theme === 'dark' ? 'active' : ''}`}>
                      <div className="preview-header dark-preview">
                        <span className="preview-icon">🌙</span>
                        <span className="preview-title">Dark Mode</span>
                      </div>
                      <div className="preview-body dark-preview">
                        <div className="preview-line"></div>
                        <div className="preview-line short"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="settings-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button
            className="save-btn"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>

        {/* Save Preset Modal */}
        {showSavePresetModal && (
          <div className="preset-modal-overlay" onClick={() => setShowSavePresetModal(false)}>
            <div className="preset-modal" onClick={(e) => e.stopPropagation()}>
              <h3>Save Custom Preset</h3>
              <p className="preset-modal-info">
                Save your current council configuration ({selectedCouncil.length} models + chairman) as a reusable preset.
              </p>
              <input
                type="text"
                className="preset-name-input"
                placeholder="Enter preset name..."
                value={newPresetName}
                onChange={(e) => setNewPresetName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleConfirmSavePreset()}
                autoFocus
              />
              <div className="preset-modal-actions">
                <button
                  className="cancel-btn"
                  onClick={() => setShowSavePresetModal(false)}
                >
                  Cancel
                </button>
                <button
                  className="save-btn"
                  onClick={handleConfirmSavePreset}
                  disabled={!newPresetName.trim()}
                >
                  Save Preset
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
