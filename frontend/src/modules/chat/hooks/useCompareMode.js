import { useState, useRef } from 'react';
import { api } from '../../../api';

/**
 * Hook for model comparison mode - parallel queries to multiple models with voting.
 *
 * @param {Object} params
 * @param {Object} params.conversation - Current conversation object
 * @param {Array} params.attachedFiles - Currently attached files
 * @param {Object} params.features - Feature toggles
 * @param {Object} params.toast - Toast notification instance
 * @returns {Object} Compare mode state and handlers
 */
export function useCompareMode({ conversation, attachedFiles, features, toast }) {
  const [compareModels, setCompareModels] = useState([]);
  const [compareResponses, setCompareResponses] = useState({});
  const [isComparing, setIsComparing] = useState(false);
  const [compareVote, setCompareVote] = useState(null);
  const [compareQuery, setCompareQuery] = useState('');
  const [showCompareModelPicker, setShowCompareModelPicker] = useState(false);
  const compareAbortControllersRef = useRef({});

  const handleStopCompare = () => {
    Object.values(compareAbortControllersRef.current).forEach(ctrl => ctrl?.abort());
    compareAbortControllersRef.current = {};
    setIsComparing(false);
  };

  const handleCompareSubmit = async (message) => {
    if (compareModels.length < 2) {
      alert('Please select at least 2 models to compare');
      return;
    }

    setCompareQuery(message);
    setCompareVote(null);
    setIsComparing(true);

    // Initialize response state for each model
    const initialResponses = {};
    compareModels.forEach(modelId => {
      initialResponses[modelId] = { text: '', done: false, error: null };
    });
    setCompareResponses(initialResponses);

    // Create abort controllers for each model
    compareModels.forEach(modelId => {
      compareAbortControllersRef.current[modelId] = new AbortController();
    });

    // Send parallel requests to all selected models
    const streamPromises = compareModels.map(async (modelId) => {
      try {
        await api.sendQuickMessageStream(
          conversation.id,
          message,
          modelId,
          (type, event) => {
            if (type === 'chunk') {
              setCompareResponses(prev => ({
                ...prev,
                [modelId]: { ...prev[modelId], text: prev[modelId].text + event.data }
              }));
            } else if (type === 'complete' || type === 'title_complete') {
              setCompareResponses(prev => ({
                ...prev,
                [modelId]: { ...prev[modelId], done: true }
              }));
            } else if (type === 'error') {
              setCompareResponses(prev => ({
                ...prev,
                [modelId]: { ...prev[modelId], done: true, error: 'Error occurred' }
              }));
            }
          },
          compareAbortControllersRef.current[modelId].signal,
          attachedFiles.map((file) => file.filename),
          {},
          features
        );
      } catch (err) {
        if (err.name !== 'AbortError') {
          setCompareResponses(prev => ({
            ...prev,
            [modelId]: { ...prev[modelId], done: true, error: err.message }
          }));
        }
      }
    });

    try {
      await Promise.all(streamPromises);
    } finally {
      setIsComparing(false);
      compareAbortControllersRef.current = {};
    }
  };

  return {
    compareModels,
    setCompareModels,
    compareResponses,
    isComparing,
    compareVote,
    setCompareVote,
    compareQuery,
    showCompareModelPicker,
    setShowCompareModelPicker,
    handleCompareSubmit,
    handleStopCompare,
  };
}

export default useCompareMode;
