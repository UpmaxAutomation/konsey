import { useState, useEffect, useCallback } from 'react';
import { api } from '../../../api';

/**
 * Hook for managing feature toggles (memory, web search, deep search, code execution, fast mode).
 *
 * @param {Object} params
 * @param {boolean} params.hasPerplexityKey - Whether a Perplexity API key is configured
 * @returns {Object} Features state and toggle functions
 */
export function useFeatures({ hasPerplexityKey }) {
  const [features, setFeatures] = useState({
    memory: true,
    web_search: true,
    deep_search: false,
    code_execution: true,
    fast_mode: false,
    auto_preference: 'quality',
  });

  // Load features on mount
  useEffect(() => {
    api.getFeatures().then(setFeatures).catch(console.error);
  }, []);

  // Toggle or set feature
  const toggleFeature = async (feature, value = null) => {
    const newValue = value !== null ? value : !features[feature];
    if (features[feature] === newValue) return;
    try {
      const updated = await api.setFeatures({ [feature]: newValue });
      setFeatures(updated);
    } catch (e) {
      console.error('Failed to toggle feature:', e);
    }
  };

  const setAutoPreference = async (preference) => {
    if (features.auto_preference === preference) return;
    try {
      const updated = await api.setFeatures({ auto_preference: preference });
      setFeatures(updated);
    } catch (e) {
      console.error('Failed to set auto preference:', e);
    }
  };

  // Set search mode (Off / Online / Deep)
  const setSearchMode = async (mode) => {
    try {
      let updates = {};
      if (mode === 'off') {
        updates = { web_search: false, deep_search: false };
      } else if (mode === 'online') {
        updates = { web_search: true, deep_search: false };
      } else if (mode === 'deep') {
        updates = hasPerplexityKey
          ? { web_search: false, deep_search: true }
          : { web_search: true, deep_search: false };
      }
      const updated = await api.setFeatures(updates);
      setFeatures(updated);
    } catch (e) {
      console.error('Failed to set search mode:', e);
    }
  };

  // Cycle search mode: Off -> Online -> Deep -> Off
  const cycleSearchMode = useCallback(() => {
    if (!features.web_search && !features.deep_search) {
      setSearchMode('online');
    } else if (features.web_search && !features.deep_search) {
      if (!hasPerplexityKey) {
        setSearchMode('off');
        return;
      }
      setSearchMode('deep');
    } else {
      setSearchMode('off');
    }
  }, [features.web_search, features.deep_search, hasPerplexityKey]);

  // Fallback if Perplexity key removed while deep search is active
  useEffect(() => {
    if (!hasPerplexityKey && features.deep_search) {
      setSearchMode('online');
    }
  }, [hasPerplexityKey, features.deep_search]);

  // Keyboard shortcut: Ctrl+Shift+S to toggle search
  useEffect(() => {
    const handleKeyboard = (e) => {
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        cycleSearchMode();
      }
    };
    window.addEventListener('keydown', handleKeyboard);
    return () => window.removeEventListener('keydown', handleKeyboard);
  }, [cycleSearchMode]);

  return {
    features,
    setFeatures,
    toggleFeature,
    setAutoPreference,
    setSearchMode,
    cycleSearchMode,
  };
}

export default useFeatures;
