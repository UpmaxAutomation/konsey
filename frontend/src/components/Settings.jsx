// TEST COMMENT - If you see this in Antigravity, reload worked! Delete this line.
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
  const [isRefreshingModels, setIsRefreshingModels] = useState(false);

  // Features state (moved from ChatInterface)
  const [features, setFeatures] = useState({
    memory: true,
    web_search: true,
    deep_search: false,
    code_execution: true
  });

  // Memory state
  const [memoryContext, setMemoryContext] = useState('');
  const [memoryStats, setMemoryStats] = useState(null);

  // System instructions state
  const [systemInstructions, setSystemInstructions] = useState('');

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || activeTab !== 'models') return;
    const interval = setInterval(() => {
      loadData();
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [isOpen, activeTab]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [configData, keysData, presetsData, featuresData] = await Promise.all([
        api.getConfig(),
        api.getApiKeys(),
        api.getPresets(),
        api.getFeatures().catch(() => null),
      ]);
      setConfig(configData);
      setSelectedCouncil(configData.council_models);
      setSelectedChairman(configData.chairman_model);
      setApiKeys(keysData.api_keys || {});
      // Check if OpenRouter key is configured (non-empty masked key)
      setHasOpenRouterKey(!!(keysData.api_keys?.openrouter));
      setBuiltInPresets(presetsData.presets || []);
      setCustomPresets(loadCustomPresets());
      if (featuresData) setFeatures(featuresData);

      // Load memory data
      try {
        const [memContext, memStats] = await Promise.all([
          api.getMemoryContext(),
          api.getMemoryStats()
        ]);
        setMemoryContext(memContext.context || 'No memories stored yet.');
        setMemoryStats(memStats);
      } catch (e) {
        console.error('Failed to load memory:', e);
      }

      // Load system instructions
      try {
        const prefs = await api.getPreferences?.() || {};
        setSystemInstructions(prefs.system_instructions || '');
      } catch (e) {
        console.error('Failed to load preferences:', e);
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
    setLoading(false);
  };

  const refreshModelsAndPresets = async () => {
    setIsRefreshingModels(true);
    try {
      await api.refreshModels();
      await loadData();
      showMessage('success', 'Models and presets refreshed');
    } catch (e) {
      showMessage('error', `Failed to refresh models: ${e.message || 'Unknown error'}`);
    } finally {
      setIsRefreshingModels(false);
    }
  };

  // Provider definitions with status
  const providers = [
    { id: 'openrouter', name: 'OpenRouter', models: 'All models via OpenRouter', hint: 'sk-or-v1-...', priority: true },
    { id: 'perplexity', name: 'Perplexity', models: 'Sonar Pro, Deep Research', hint: 'pplx-...', priority: true, description: 'Web search & research' },
    { id: 'openai', name: 'OpenAI', models: 'GPT-4o, GPT-5, o1, o3', hint: 'sk-...' },
    { id: 'anthropic', name: 'Anthropic', models: 'Claude 4, Sonnet, Opus', hint: 'sk-ant-...' },
    { id: 'google', name: 'Google', models: 'Gemini 2.5, 3.0 Flash', hint: 'AIza...' },
    { id: 'x-ai', name: 'xAI', models: 'Grok 3, Grok 4', hint: 'xai-...' },
    { id: 'deepseek', name: 'DeepSeek', models: 'DeepSeek V3, R1', hint: 'sk-...' },
    { id: 'mistralai', name: 'Mistral', models: 'Large, Codestral', hint: '' },
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
      const result = await api.setApiKey(provider, key);
      const keysData = await api.getApiKeys();
      setApiKeys(keysData.api_keys || {});
      window.dispatchEvent(new CustomEvent('api-keys-updated', { detail: keysData.api_keys || {} }));
      setApiKeyInputs({ ...apiKeyInputs, [provider]: '' });
      showMessage('success', `${provider} API key saved successfully`);
    } catch (err) {
      showMessage('error', `Failed to save ${provider} API key: ${err.message || 'Unknown error'}`);
    } finally {
      setSavingKey(null);
    }
  };

  const handleDeleteApiKey = async (provider) => {
    console.log(`[Settings] Deleting API key for provider: ${provider}`);
    setSavingKey(provider);
    setError(null);
    try {
      const deleteResult = await api.deleteApiKey(provider);
      console.log(`[Settings] Delete result:`, deleteResult);

      // Refetch keys to update UI
      const keysData = await api.getApiKeys();
      console.log(`[Settings] Refreshed API keys:`, keysData);
      setApiKeys(keysData.api_keys || {});
      window.dispatchEvent(new CustomEvent('api-keys-updated', { detail: keysData.api_keys || {} }));
      showMessage('success', `${provider} API key removed`);
    } catch (err) {
      console.error(`[Settings] Failed to delete API key:`, err);
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
      const updated = await api.updateConfig({
        council_models: selectedCouncil,
        chairman_model: selectedChairman,
      });
      setConfig((prev) => ({
        ...prev,
        council_models: updated.council_models,
        chairman_model: updated.chairman_model,
      }));
      setSelectedCouncil(updated.council_models || []);
      setSelectedChairman(updated.chairman_model || '');
      window.dispatchEvent(new CustomEvent('council-config-updated', { detail: updated }));
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
        setConfig((prev) => ({
          ...prev,
          council_models: result.council_models,
          chairman_model: result.chairman_model,
        }));
        window.dispatchEvent(new CustomEvent('council-config-updated', { detail: result }));
        showMessage('success', `Applied preset: ${result.preset_name}`);
      } catch (err) {
        showMessage('error', `Failed to apply preset: ${err.message || 'Unknown error'}`);
      }
    }
  };

  const availableModelIds = useMemo(() => {
    return new Set(Object.keys(config?.available_models || {}));
  }, [config]);

  const presetValidity = useMemo(() => {
    const validity = {};
    builtInPresets.forEach((preset) => {
      const invalidModels = (preset.models || []).filter((model) => !availableModelIds.has(model));
      const chairmanInvalid = preset.chairman && !availableModelIds.has(preset.chairman);
      validity[preset.id] = {
        invalidModels,
        chairmanInvalid,
      };
    });
    return validity;
  }, [builtInPresets, availableModelIds]);

  const selectedPresetValidity = useMemo(() => {
    if (!selectedPreset || selectedPreset.startsWith('custom:')) return null;
    return presetValidity[selectedPreset] || null;
  }, [selectedPreset, presetValidity]);

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

  // Feature toggle handler
  const toggleFeature = async (feature) => {
    const newValue = !features[feature];
    try {
      const updated = await api.setFeatures({ [feature]: newValue });
      setFeatures(updated);
      showMessage('success', `${feature.replace('_', ' ')} ${newValue ? 'enabled' : 'disabled'}`);
    } catch (e) {
      showMessage('error', `Failed to toggle ${feature}`);
    }
  };

  // Memory handlers
  const loadMemory = async () => {
    try {
      const [memContext, memStats] = await Promise.all([
        api.getMemoryContext(),
        api.getMemoryStats()
      ]);
      setMemoryContext(memContext.context || 'No memories stored yet.');
      setMemoryStats(memStats);
    } catch (e) {
      showMessage('error', 'Failed to load memory');
    }
  };

  const handleClearMemory = async () => {
    if (!confirm('Clear all stored memories? This cannot be undone.')) return;
    try {
      await api.clearMemory();
      await loadMemory();
      showMessage('success', 'Memory cleared');
    } catch (e) {
      showMessage('error', 'Failed to clear memory');
    }
  };

  // System instructions handler
  const saveInstructions = async () => {
    try {
      await api.setPreference('system_instructions', systemInstructions);
      showMessage('success', 'System instructions saved');
    } catch (e) {
      showMessage('error', 'Failed to save instructions');
    }
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
              <span className="tab-icon">🔑</span>
              API Keys
              {directApiCount > 0 && (
                <span className="tab-badge">{directApiCount}</span>
              )}
            </button>
            <button
              className={`settings-tab ${activeTab === 'models' ? 'active' : ''}`}
              onClick={() => setActiveTab('models')}
            >
              <span className="tab-icon">🤖</span>
              Models
              <span className="tab-badge">{selectedCouncil.length}</span>
            </button>
            <button
              className={`settings-tab ${activeTab === 'appearance' ? 'active' : ''}`}
              onClick={() => setActiveTab('appearance')}
            >
              <span className="tab-icon">{theme === 'dark' ? '🌙' : '☀️'}</span>
              Theme
            </button>
            <button
              className={`settings-tab ${activeTab === 'features' ? 'active' : ''}`}
              onClick={() => setActiveTab('features')}
            >
              <span className="tab-icon">⚡</span>
              Features
            </button>
            <button
              className={`settings-tab ${activeTab === 'memory' ? 'active' : ''}`}
              onClick={() => { setActiveTab('memory'); loadMemory(); }}
            >
              <span className="tab-icon">🧠</span>
              Memory
            </button>
            <button
              className={`settings-tab ${activeTab === 'system' ? 'active' : ''}`}
              onClick={() => setActiveTab('system')}
            >
              <span className="tab-icon">📝</span>
              System
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

                {/* Presets Section */}
                <div className="presets-section">
                  <div className="presets-header">
                    <label className="presets-label">Council Presets</label>
                    <div className="preset-actions">
                      <button
                        className="save-preset-btn"
                        onClick={handleSaveAsPreset}
                        title="Save current configuration as a custom preset"
                      >
                        + Save as Preset
                      </button>
                      <button
                        className="refresh-models-btn"
                        onClick={refreshModelsAndPresets}
                        disabled={isRefreshingModels}
                        title="Refresh models and presets"
                      >
                        {isRefreshingModels ? 'Refreshing...' : 'Refresh'}
                      </button>
                    </div>
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
                          {builtInPresets.map(preset => {
                            const validity = presetValidity[preset.id];
                            const hasInvalid = validity && (validity.invalidModels.length > 0 || validity.chairmanInvalid);
                            return (
                              <option key={preset.id} value={preset.id} disabled={hasInvalid}>
                                {preset.name}{hasInvalid ? ' (Unavailable models)' : ''}
                              </option>
                            );
                          })}
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
                  {selectedPresetValidity && (selectedPresetValidity.invalidModels.length > 0 || selectedPresetValidity.chairmanInvalid) && (
                    <p className="preset-warning">
                      Some models in this preset are unavailable. Please refresh or choose a different preset.
                    </p>
                  )}
                </div>

                {/* OpenRouter Best Practices */}
                <div className="openrouter-info">
                  <div className="info-icon">ℹ️</div>
                  <div className="info-content">
                    <strong>Get the most out of OpenRouter</strong>
                    <p>
                      Free models can be rate-limited. For reliability, use stable paid models
                      and add your own provider keys (BYOK). Refresh models regularly to avoid
                      stale or unavailable IDs.
                    </p>
                  </div>
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

            {/* Features Tab */}
            {activeTab === 'features' && (
              <div className="tab-content features-tab">
                <div className="section-intro">
                  <h3>Features</h3>
                  <p>Enable or disable AI capabilities for your conversations.</p>
                </div>

                <div className="feature-toggles-grid">
                  <div className="feature-card" onClick={() => toggleFeature('memory')}>
                    <div className="feature-icon">🧠</div>
                    <div className="feature-info">
                      <h4>Memory</h4>
                      <p>Remember facts & decisions across sessions</p>
                    </div>
                    <div className={`feature-toggle ${features.memory ? 'active' : ''}`}>
                      <div className="toggle-track">
                        <div className="toggle-thumb"></div>
                      </div>
                    </div>
                  </div>

                  <div className="feature-card" onClick={() => toggleFeature('web_search')}>
                    <div className="feature-icon">🔍</div>
                    <div className="feature-info">
                      <h4>Web Search</h4>
                      <p>Search the web for current information</p>
                    </div>
                    <div className={`feature-toggle ${features.web_search ? 'active' : ''}`}>
                      <div className="toggle-track">
                        <div className="toggle-thumb"></div>
                      </div>
                    </div>
                  </div>

                  <div className="feature-card" onClick={() => toggleFeature('deep_search')}>
                    <div className="feature-icon">🧭</div>
                    <div className="feature-info">
                      <h4>Deep Search</h4>
                      <p>Long-form research with citations (Perplexity)</p>
                    </div>
                    <div className={`feature-toggle ${features.deep_search ? 'active' : ''}`}>
                      <div className="toggle-track">
                        <div className="toggle-thumb"></div>
                      </div>
                    </div>
                  </div>

                  <div className="feature-card" onClick={() => toggleFeature('code_execution')}>
                    <div className="feature-icon">💻</div>
                    <div className="feature-info">
                      <h4>Code Execution</h4>
                      <p>Run Python/JavaScript code</p>
                    </div>
                    <div className={`feature-toggle ${features.code_execution ? 'active' : ''}`}>
                      <div className="toggle-track">
                        <div className="toggle-thumb"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Memory Tab */}
            {activeTab === 'memory' && (
              <div className="tab-content memory-tab">
                <div className="section-intro">
                  <h3>Memory</h3>
                  <p>View and manage what the AI remembers about you.</p>
                </div>

                {memoryStats && (
                  <div className="memory-stats-grid">
                    <div className="memory-stat">
                      <span className="stat-icon">📝</span>
                      <span className="stat-value">{memoryStats.facts_count}</span>
                      <span className="stat-label">Facts</span>
                    </div>
                    <div className="memory-stat">
                      <span className="stat-icon">📋</span>
                      <span className="stat-value">{memoryStats.decisions_count}</span>
                      <span className="stat-label">Decisions</span>
                    </div>
                    <div className="memory-stat">
                      <span className="stat-icon">⚙️</span>
                      <span className="stat-value">{memoryStats.preferences_count}</span>
                      <span className="stat-label">Preferences</span>
                    </div>
                  </div>
                )}

                <div className="memory-content-box">
                  <pre>{memoryContext}</pre>
                </div>

                <div className="memory-actions">
                  <button className="action-btn secondary" onClick={loadMemory}>
                    🔄 Refresh
                  </button>
                  <button className="action-btn danger" onClick={handleClearMemory}>
                    🗑️ Clear All Memory
                  </button>
                </div>
              </div>
            )}

            {/* System Tab */}
            {activeTab === 'system' && (
              <div className="tab-content system-tab">
                <div className="section-intro">
                  <h3>System Instructions</h3>
                  <p>Custom instructions that apply to all your conversations.</p>
                </div>

                <div className="instructions-section">
                  <textarea
                    className="instructions-textarea"
                    value={systemInstructions}
                    onChange={(e) => setSystemInstructions(e.target.value)}
                    placeholder="e.g., Always respond in a formal tone. Focus on technical accuracy. Prefer concise answers..."
                    rows={8}
                  />
                  <div className="instructions-footer">
                    <span className="char-count">{systemInstructions.length} characters</span>
                    <button className="action-btn primary" onClick={saveInstructions}>
                      Save Instructions
                    </button>
                  </div>
                </div>

                <div className="instructions-tips">
                  <h4>Tips for effective instructions:</h4>
                  <ul>
                    <li>Be specific about your preferred response format</li>
                    <li>Mention your expertise level for calibrated explanations</li>
                    <li>Include any domain-specific terminology preferences</li>
                    <li>Specify languages or coding conventions if relevant</li>
                  </ul>
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
