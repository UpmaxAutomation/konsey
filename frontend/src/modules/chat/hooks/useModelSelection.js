import { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../../api';
import { useDebounce } from '../../../hooks/useDebounce';

// localStorage keys for favorites and recent models
const FAVORITES_STORAGE_KEY = 'llm-council-favorites';
const RECENT_STORAGE_KEY = 'llm-council-recent';
const MAX_RECENT_MODELS = 3;

// Popular models to show at top
const POPULAR_MODELS = [
  'anthropic/claude-sonnet-4',
  'anthropic/claude-opus-4',
  'openai/gpt-4o',
  'openai/gpt-4.1',
  'google/gemini-2.5-pro',
  'google/gemini-2.5-flash',
  'deepseek/deepseek-chat-v3',
  'openai/o3',
];

// Estimate tokens for cost calculation
const ESTIMATED_INPUT_TOKENS = 500;
const ESTIMATED_OUTPUT_TOKENS = 1000;

/**
 * Hook for model selection, favorites, recents, grouping, filtering, and cost estimation.
 *
 * @param {Object} params
 * @param {Object} params.toast - Toast notification instance
 * @returns {Object} Model selection state and handlers
 */
export function useModelSelection({ toast }) {
  const [selectedModel, setSelectedModel] = useState('');
  const [models, setModels] = useState({});
  const [councilModels, setCouncilModels] = useState([]);
  const [autoMode, setAutoMode] = useState(false);
  const [hasPerplexityKey, setHasPerplexityKey] = useState(false);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [modelSearch, setModelSearch] = useState('');
  const debouncedModelSearch = useDebounce(modelSearch, 200);

  const [favoriteModels, setFavoriteModels] = useState(() => {
    try {
      const stored = localStorage.getItem(FAVORITES_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [recentModels, setRecentModels] = useState(() => {
    try {
      const stored = localStorage.getItem(RECENT_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [collapsedGroups, setCollapsedGroups] = useState({});

  const loadConfig = async () => {
    try {
      const config = await api.getConfig();
      setModels(config.available_models || {});
      setCouncilModels(config.council_models || []);
      const maskedKeys = config.api_keys || {};
      setHasPerplexityKey(!!maskedKeys.perplexity);
      const modelList = Object.keys(config.available_models || {});
      const defaultModel = modelList.find(m => m.includes('claude-sonnet-4')) || modelList[0];
      setSelectedModel(defaultModel || 'anthropic/claude-sonnet-4');
    } catch (error) {
      console.error('Failed to load config:', error);
      toast.error('Failed to load model configuration.');
      setSelectedModel('anthropic/claude-sonnet-4');
    }
  };

  // Load models once
  useEffect(() => {
    loadConfig();
  }, []);

  const refreshApiKeys = useCallback(async () => {
    try {
      const keysData = await api.getApiKeys();
      const masked = keysData.api_keys || {};
      setHasPerplexityKey(!!masked.perplexity);
    } catch (error) {
      console.error('Failed to refresh API keys:', error);
    }
  }, []);

  useEffect(() => {
    refreshApiKeys();
    const handleKeysUpdated = () => refreshApiKeys();
    window.addEventListener('api-keys-updated', handleKeysUpdated);
    return () => window.removeEventListener('api-keys-updated', handleKeysUpdated);
  }, [refreshApiKeys]);

  // Refresh council models after settings update
  useEffect(() => {
    const handleConfigUpdated = (event) => {
      const updated = event?.detail;
      if (updated?.council_models) {
        setCouncilModels(updated.council_models);
      } else {
        loadConfig();
      }
    };
    window.addEventListener('council-config-updated', handleConfigUpdated);
    return () => window.removeEventListener('council-config-updated', handleConfigUpdated);
  }, []);

  // Group models by provider
  const groupedModels = useMemo(() => {
    const groups = {};
    const popular = [];

    Object.entries(models).forEach(([id, info]) => {
      const provider = id.split('/')[0] || 'other';
      if (!groups[provider]) groups[provider] = [];
      groups[provider].push({ id, ...info });

      if (POPULAR_MODELS.includes(id)) {
        popular.push({ id, ...info });
      }
    });

    return { groups, popular };
  }, [models]);

  // Filter models by search (using debounced value)
  const filteredModels = useMemo(() => {
    if (!debouncedModelSearch) return groupedModels;

    const query = debouncedModelSearch.toLowerCase();
    const filtered = {};

    Object.entries(groupedModels.groups).forEach(([provider, modelList]) => {
      const matches = modelList.filter(m =>
        m.id.toLowerCase().includes(query) ||
        m.name.toLowerCase().includes(query)
      );
      if (matches.length) filtered[provider] = matches;
    });

    return {
      groups: filtered,
      popular: groupedModels.popular.filter(m =>
        m.id.toLowerCase().includes(query) ||
        m.name.toLowerCase().includes(query)
      )
    };
  }, [groupedModels, debouncedModelSearch]);

  // Calculate estimated cost for council mode
  const councilCostEstimate = useMemo(() => {
    if (councilModels.length === 0 || Object.keys(models).length === 0) {
      return null;
    }

    let totalCost = 0;
    let modelCount = 0;

    councilModels.forEach(modelId => {
      const modelInfo = models[modelId];
      if (modelInfo && modelInfo.input_cost !== undefined && modelInfo.output_cost !== undefined) {
        const inputCost = (modelInfo.input_cost * ESTIMATED_INPUT_TOKENS) / 1_000_000;
        const outputCost = (modelInfo.output_cost * ESTIMATED_OUTPUT_TOKENS) / 1_000_000;
        totalCost += inputCost + outputCost;
        modelCount++;
      }
    });

    if (modelCount === 0) return null;

    const formattedCost = totalCost < 0.01
      ? `~$${totalCost.toFixed(4)}`
      : totalCost < 0.1
        ? `~$${totalCost.toFixed(3)}`
        : `~$${totalCost.toFixed(2)}`;

    return {
      cost: formattedCost,
      modelCount
    };
  }, [councilModels, models]);

  // Toggle favorite status of a model
  const toggleFavorite = (modelId, e) => {
    e.stopPropagation();
    setFavoriteModels(prev => {
      const newFavorites = prev.includes(modelId)
        ? prev.filter(id => id !== modelId)
        : [...prev, modelId];
      localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(newFavorites));
      return newFavorites;
    });
  };

  // Add model to recent list
  const addToRecent = (modelId) => {
    setRecentModels(prev => {
      const filtered = prev.filter(id => id !== modelId);
      const newRecent = [modelId, ...filtered].slice(0, MAX_RECENT_MODELS);
      localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(newRecent));
      return newRecent;
    });
  };

  const selectModel = (modelId) => {
    setSelectedModel(modelId);
    addToRecent(modelId);
    setShowModelPicker(false);
    setModelSearch('');
  };

  // Toggle collapsed state of provider groups
  const toggleProviderGroup = (provider) => {
    setCollapsedGroups(prev => ({
      ...prev,
      [provider]: !prev[provider]
    }));
  };

  // Simple model name display
  const getModelName = (id) => {
    if (!id) return '';
    const name = id.split('/')[1] || id;
    return name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  return {
    selectedModel,
    setSelectedModel,
    models,
    councilModels,
    autoMode,
    setAutoMode,
    hasPerplexityKey,
    showModelPicker,
    setShowModelPicker,
    modelSearch,
    setModelSearch,
    filteredModels,
    groupedModels,
    councilCostEstimate,
    favoriteModels,
    recentModels,
    collapsedGroups,
    toggleFavorite,
    selectModel,
    toggleProviderGroup,
    getModelName,
  };
}

export default useModelSelection;
