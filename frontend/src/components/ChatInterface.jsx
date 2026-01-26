import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import SafeMarkdown from './SafeMarkdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './ChatInterface.css';
import './ClaudeChat.css';
import { api } from '../api';
import { useToast } from './Toast';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import FileUpload from './FileUpload';
import ProgressIndicator from './ProgressIndicator';
import CostEstimate from './CostEstimate';
import { useDebounce } from '../hooks/useDebounce';

// Estimate tokens for cost calculation
const ESTIMATED_INPUT_TOKENS = 500;  // Average input tokens per model
const ESTIMATED_OUTPUT_TOKENS = 1000; // Average output tokens per model

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

export default function ChatInterface({
  conversation,
  currentConversationId,
  onSendMessage,
  isLoading,
  onStopCouncil,
  onConversationUpdate,
  councilProgress = { stage: 0, models: [], modelProgress: {}, chairmanModel: '', chairmanStatus: 'pending' },
  currentProjectId,
  onMoveToProject,
}) {
  const activeConversationId = conversation?.id || currentConversationId || null;
  const [input, setInput] = useState('');
  const [pastedImages, setPastedImages] = useState([]); // Array of {id, dataUrl, file}
  const [selectedModel, setSelectedModel] = useState('');
  const [autoMode, setAutoMode] = useState(false); // Auto model selection
  const [routeInfo, setRouteInfo] = useState(null); // Routing info for display
  const [models, setModels] = useState({});
  const [councilModels, setCouncilModels] = useState([]);
  const [streamingText, setStreamingText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [mode, setMode] = useState('quick'); // 'quick', 'council', or 'compare'
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [modelSearch, setModelSearch] = useState('');
  // Debounce search for performance - prevents filtering on every keystroke
  const debouncedModelSearch = useDebounce(modelSearch, 200);
  // Compare mode state
  const [compareModels, setCompareModels] = useState([]); // Selected models for comparison (2-3)
  const [compareResponses, setCompareResponses] = useState({}); // {modelId: {text, done, error}}
  const [isComparing, setIsComparing] = useState(false);
  const [compareVote, setCompareVote] = useState(null); // Which model user voted for
  const [compareQuery, setCompareQuery] = useState(''); // Current query being compared
  const [showCompareModelPicker, setShowCompareModelPicker] = useState(false);
  const compareAbortControllersRef = useRef({});
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [showScrollFab, setShowScrollFab] = useState(false);
  const [copiedCode, setCopiedCode] = useState(null);
  const [copiedMessageIndex, setCopiedMessageIndex] = useState(null); // Track which message was copied
  const [expandedCouncil, setExpandedCouncil] = useState({}); // Track which messages show council details
  const [showShortcuts, setShowShortcuts] = useState(false); // Keyboard shortcuts modal
  // Favorites and Recent models state
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
  // Feature toggles (for quick access in input area)
  const [features, setFeatures] = useState({
    memory: true,
    web_search: true,
    deep_search: false,
    code_execution: true
  });
  // File upload state
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  // Collapsed provider groups in model picker (start collapsed by default)
  const [collapsedGroups, setCollapsedGroups] = useState({});
  // Options panel visibility
  const [showOptions, setShowOptions] = useState(false);
  // Cost estimate state
  const [showCostEstimate, setShowCostEstimate] = useState(false);
  const [pendingMessage, setPendingMessage] = useState(null);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const textareaRef = useRef(null);
  const recognitionRef = useRef(null);
  const abortControllerRef = useRef(null);
  const toast = useToast();

  // Handle scroll to show/hide FAB
  const handleScroll = useCallback((e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setShowScrollFab(!isNearBottom && scrollHeight > clientHeight + 200);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Copy code to clipboard
  const copyCode = async (code) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCode(code);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Copy a single message to clipboard
  const copyMessage = async (msg, index) => {
    const stage3Content = typeof msg.stage3 === 'object' ? msg.stage3?.response : msg.stage3;
    const content = msg.content || stage3Content || '';
    const role = msg.role === 'user' ? 'You' : 'Assistant';
    const text = `**${role}:**\n${content}`;

    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageIndex(index);
      toast.success('Message copied!');
      setTimeout(() => setCopiedMessageIndex(null), 2000);
    } catch (err) {
      console.error('Failed to copy message:', err);
      toast.error('Failed to copy message');
    }
  };

  // Copy entire conversation to clipboard
  const copyConversation = async () => {
    if (!conversation?.messages?.length) return;

    const title = conversation.title || 'Conversation';
    let text = `# ${title}\n\n`;

    conversation.messages.forEach((msg) => {
      const stage3Content = typeof msg.stage3 === 'object' ? msg.stage3?.response : msg.stage3;
      const content = msg.content || stage3Content || '';
      const role = msg.role === 'user' ? 'You' : 'Assistant';
      text += `**${role}:**\n${content}\n\n---\n\n`;
    });

    try {
      await navigator.clipboard.writeText(text);
      toast.success('Conversation copied!');
    } catch (err) {
      console.error('Failed to copy conversation:', err);
      toast.error('Failed to copy conversation');
    }
  };

  // Custom code block renderer with copy button
  const CodeBlock = ({ node, inline, className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || '');
    const code = String(children).replace(/\n$/, '');

    if (!inline && match) {
      return (
        <div className="code-block-wrapper">
          <div className="code-block-header">
            <span className="code-language">{match[1]}</span>
            <button
              className="copy-code-btn"
              onClick={() => copyCode(code)}
              title="Copy code"
            >
              {copiedCode === code ? (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  Copied!
                </>
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                  Copy
                </>
              )}
            </button>
          </div>
          <SyntaxHighlighter
            style={oneDark}
            language={match[1]}
            PreTag="div"
            customStyle={{
              margin: 0,
              borderRadius: '0 0 12px 12px',
              padding: '16px 20px',
            }}
            {...props}
          >
            {code}
          </SyntaxHighlighter>
        </div>
      );
    }

    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  };

  // Check for speech recognition support
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      setSpeechSupported(true);
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        if (finalTranscript) {
          setInput(prev => prev + finalTranscript + ' ');
        }
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
        // Show user-friendly error messages for common errors
        switch (event.error) {
          case 'no-speech':
            // Silent - user just didn't speak, not an error
            break;
          case 'audio-capture':
            toast.error('No microphone found. Please connect a microphone.');
            break;
          case 'not-allowed':
            toast.error('Microphone access denied. Please allow microphone in browser settings.');
            break;
          case 'network':
            toast.error('Network error during speech recognition.');
            break;
          case 'aborted':
            // Silent - user aborted, not an error
            break;
          default:
            toast.error('Speech recognition error: ' + event.error);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const toggleListening = async () => {
    if (!recognitionRef.current) {
      toast.error('Speech recognition not available in this browser');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        // Request microphone permission first
        await navigator.mediaDevices.getUserMedia({ audio: true });
        recognitionRef.current.start();
        setIsListening(true);
        textareaRef.current?.focus();
      } catch (err) {
        console.error('Microphone permission error:', err);
        if (err.name === 'NotAllowedError') {
          toast.error('Microphone access denied. Please allow microphone in browser settings.');
        } else if (err.name === 'NotFoundError') {
          toast.error('No microphone found. Please connect a microphone.');
        } else {
          toast.error('Could not start voice input: ' + err.message);
        }
      }
    }
  };

  // Load models once
  useEffect(() => {
    api.getConfig().then(config => {
      setModels(config.available_models || {});
      setCouncilModels(config.council_models || []);
      // Default to Claude Sonnet 4 or first available
      const modelList = Object.keys(config.available_models || {});
      const defaultModel = modelList.find(m => m.includes('claude-sonnet-4')) || modelList[0];
      setSelectedModel(defaultModel || 'anthropic/claude-sonnet-4');
    }).catch((error) => {
      console.error('Failed to load config:', error);
      toast.error('Failed to load model configuration.');
      setSelectedModel('anthropic/claude-sonnet-4');
    });
  }, []);

  // Load features (memory, web_search, etc.)
  useEffect(() => {
    api.getFeatures().then(setFeatures).catch(console.error);
  }, []);

  // Toggle feature
  const toggleFeature = async (feature) => {
    const newValue = !features[feature];
    try {
      const updated = await api.setFeatures({ [feature]: newValue });
      setFeatures(updated);
    } catch (e) {
      console.error('Failed to toggle feature:', e);
    }
  };

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

  // Filter models by search (using debounced value for performance)
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
        // Costs are per 1M tokens, so divide by 1,000,000
        const inputCost = (modelInfo.input_cost * ESTIMATED_INPUT_TOKENS) / 1_000_000;
        const outputCost = (modelInfo.output_cost * ESTIMATED_OUTPUT_TOKENS) / 1_000_000;
        totalCost += inputCost + outputCost;
        modelCount++;
      }
    });

    if (modelCount === 0) return null;

    // Format the cost with appropriate precision
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

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation, streamingText]);

  // Stop/cancel ongoing request
  const handleStop = async () => {
    // Abort client-side fetch
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Also signal backend to stop processing (saves tokens)
    if (conversation?.id) {
      try {
        await api.cancelStream(conversation.id);
      } catch (e) {
        // Ignore cancel errors - the stream may have already finished
        console.debug('Cancel stream request:', e.message);
      }
    }

    setIsStreaming(false);
    setStreamingText('');
  };

  // Stop compare mode
  const handleStopCompare = () => {
    Object.values(compareAbortControllersRef.current).forEach(ctrl => ctrl?.abort());
    compareAbortControllersRef.current = {};
    setIsComparing(false);
  };

  // Handle compare mode submission
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
          [],
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

  // Threshold for showing cost estimate (characters)
  const COST_ESTIMATE_THRESHOLD = 500;

  const handleSubmit = async (e) => {
    e.preventDefault();
    const hasText = input.trim();
    const hasImages = pastedImages.length > 0;
    const hasFiles = uploadedFiles.length > 0;

    // Allow submit if there's text OR images OR files
    if ((!hasText && !hasImages && !hasFiles) || isLoading || isStreaming || isComparing || !conversation) return;

    const message = input.trim();
    const images = [...pastedImages]; // Copy images before clearing
    // Get filenames from uploadedFiles objects
    const files = uploadedFiles.map(f => f.filename);

    // Show cost estimate for council mode with long messages
    if (mode === 'council' && message.length > COST_ESTIMATE_THRESHOLD) {
      const messageWithImages = hasImages
        ? `${message}\n\n[${images.length} image(s) attached]`
        : message;
      setPendingMessage({ message: messageWithImages, files, images });
      setShowCostEstimate(true);
      return;
    }

    setInput('');
    setPastedImages([]); // Clear images
    setUploadedFiles([]); // Clear uploaded files

    if (mode === 'council') {
      // Council mode - use existing flow
      // Note: Images are currently handled by append to text (legacy way),
      // but we now pass 'files' as a separate argument which the backend prefers.
      // We'll keep the image text append for backward compatibility or visual feedback if needed,
      // but 'files' argument is the robust way.
      const messageWithImages = hasImages
        ? `${message}\n\n[${images.length} image(s) attached]`
        : message;

      // If we have pasted images that aren't in uploadedFiles, we might need to upload them first?
      // For now, let's assume 'uploadedFiles' covers the file upload button flow.
      // Pasted images flow (lines 570+) converts to base64 dataUrl but doesn't seem to upload to server as files yet?
      // Ideally, paste should also upload. For this task, we focus on the 'uploadedFiles' from the FileUpload component.

      onSendMessage(messageWithImages, files, features);
    } else if (mode === 'compare') {
      // Compare mode - parallel queries to multiple models
      // Comparison typically doesn't support complex file context yet across all models easily
      handleCompareSubmit(message);
    } else if (mode === 'auto') {
      // Auto mode - intelligent routing to best model
      setStreamingText('');
      setRouteInfo(null);

      // Create abort controller for cancellation
      abortControllerRef.current = new AbortController();
      let streamCompleted = false;

      // Get smart recommendation based on query
      let modelToUse = selectedModel || 'anthropic/claude-sonnet-4'; // Fallback
      try {
        const routeResult = await api.routeQuery({ query: message, num_recommendations: 1 });
        if (routeResult.recommended_models?.length > 0) {
          const recommended = routeResult.recommended_models[0];
          modelToUse = recommended.model_id;
          setRouteInfo({
            model: recommended.name,
            reason: recommended.reason,
            queryType: routeResult.query_type,
            confidence: routeResult.primary_confidence,
          });
          toast.info(`Auto-selected: ${recommended.name}`);
        }
      } catch (e) {
        console.error('Auto-routing failed, using fallback model:', e);
        toast.warning('Auto-routing unavailable, using default model');
      }

      try {
        setIsStreaming(true);
        await api.sendQuickMessageStream(
          conversation.id,
          message,
          modelToUse,
          (eventType, event) => {
            if (eventType === 'chunk') {
              setStreamingText((prev) => prev + event.text);
            } else if (eventType === 'complete') {
              streamCompleted = true;
              setIsStreaming(false);
              // Reload conversation to get the saved message
              if (onConversationUpdate) {
                onConversationUpdate(conversation.id);
              }
            } else if (eventType === 'error') {
              setIsStreaming(false);
              console.error('Stream error:', event.message);
            }
          },
          abortControllerRef.current?.signal,
          files,
          {},
          features
        );
      } catch (error) {
        if (error.name === 'AbortError') {
          // User cancelled - clean up
          setStreamingText('');
        } else {
          console.error('Auto mode error:', error);
        }
        setIsStreaming(false);
      } finally {
        abortControllerRef.current = null;
        // Only reload if stream completed successfully
        if (streamCompleted && onConversationUpdate) {
          onConversationUpdate(conversation.id);
        }
      }
    } else {
      // Quick mode - stream directly with manually selected model
      setStreamingText('');
      setRouteInfo(null);

      // Create abort controller for cancellation
      abortControllerRef.current = new AbortController();
      let streamCompleted = false;

      // Determine which model to use
      let modelToUse = selectedModel;
      if (autoMode) {
        try {
          // Get smart recommendation based on query (legacy autoMode flag)
          const routeResult = await api.routeQuery({ query: message, num_recommendations: 1 });
          if (routeResult.recommended_models?.length > 0) {
            const recommended = routeResult.recommended_models[0];
            modelToUse = recommended.model_id;
            setRouteInfo({
              model: recommended.name,
              reason: recommended.reason,
              queryType: routeResult.query_type,
              confidence: routeResult.primary_confidence,
            });
          }
        } catch (e) {
          console.error('Auto-routing failed, using selected model:', e);
        }
      }

      try {
        setIsStreaming(true);
        await api.sendQuickMessageStream(
          conversation.id,
          message,
          modelToUse,
          (type, event) => {
            if (type === 'chunk') {
              setStreamingText(prev => prev + event.data);
            } else if (type === 'complete' || type === 'title_complete') {
              streamCompleted = true;
              setStreamingText('');
              onConversationUpdate?.(conversation.id);
            } else if (type === 'error') {
              streamCompleted = true;
              setStreamingText('');
              console.error('Quick message error:', event.message || event);
            }
          },
          abortControllerRef.current.signal,
          files, // Pass attached files
          {},
          features
        );
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Request failed:', err);
        }
        setStreamingText('');
      } finally {
        // Always clean up state regardless of how we exit
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Handle cost estimate confirmation - proceed with the pending message
  const handleCostEstimateConfirm = () => {
    if (pendingMessage) {
      setInput('');
      setPastedImages([]);
      setUploadedFiles([]);
      onSendMessage(pendingMessage.message, pendingMessage.files, features);
    }
    setShowCostEstimate(false);
    setPendingMessage(null);
  };

  // Handle cost estimate cancellation
  const handleCostEstimateCancel = () => {
    setShowCostEstimate(false);
    setPendingMessage(null);
  };

  // Handle paste for images
  const handlePaste = (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          const reader = new FileReader();
          reader.onload = (event) => {
            setPastedImages(prev => [...prev, {
              id: Date.now() + Math.random(),
              dataUrl: event.target.result,
              file: file,
              name: file.name || `image-${Date.now()}.png`
            }]);
          };
          reader.readAsDataURL(file);
        }
      }
    }
  };

  // Remove a pasted image
  const removePastedImage = (id) => {
    setPastedImages(prev => prev.filter(img => img.id !== id));
  };

  // Simple model name display
  const getModelName = (id) => {
    if (!id) return '';
    const name = id.split('/')[1] || id;
    return name.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  // Example prompts for empty state
  const examplePrompts = [
    { text: "Compare approaches to authentication", icon: "🔐" },
    { text: "Review this code for bugs", icon: "🐛" },
    { text: "Explain quantum computing simply", icon: "⚛️" },
    { text: "Design a REST API structure", icon: "🏗️" },
  ];

  const handleExampleClick = (prompt) => {
    setInput(prompt);
    textareaRef.current?.focus();
  };

  // Toggle favorite status of a model
  const toggleFavorite = (modelId, e) => {
    e.stopPropagation(); // Prevent selecting the model when clicking star
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
      // Remove if already exists, then add to front
      const filtered = prev.filter(id => id !== modelId);
      const newRecent = [modelId, ...filtered].slice(0, MAX_RECENT_MODELS);
      localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(newRecent));
      return newRecent;
    });
  };

  const selectModel = (modelId) => {
    setSelectedModel(modelId);
    addToRecent(modelId); // Track recently used models
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

  // Fork conversation from a specific message
  const handleForkConversation = async (messageIndex) => {
    if (!conversation?.id) return;

    try {
      const forked = await api.forkConversation(conversation.id, messageIndex);
      // Navigate to the forked conversation
      if (onConversationUpdate) {
        onConversationUpdate(forked.id);
      }
      alert(`Forked conversation with ${messageIndex + 1} messages as "${forked.title}"`);
    } catch (error) {
      console.error('Failed to fork conversation:', error);
      alert(`Failed to fork: ${error.message}`);
    }
  };

  // Export conversation to markdown
  const exportConversation = () => {
    if (!conversation?.messages?.length) return;

    const title = conversation.title || 'Conversation';
    const date = new Date(conversation.created_at || Date.now()).toLocaleDateString();

    let markdown = `# ${title}\n\n`;
    markdown += `*Exported on ${date}*\n\n---\n\n`;

    conversation.messages.forEach((msg, i) => {
      const role = msg.role === 'user' ? '**You**' : '**Assistant**';

      // Get content from various sources
      const stage3Content = typeof msg.stage3 === 'object' ? msg.stage3?.response : msg.stage3;
      const content = msg.content || stage3Content || '';

      markdown += `### ${role}\n\n${content}\n\n`;

      // Include council details if present
      if (msg.stage1 && msg.role === 'assistant') {
        markdown += `<details>\n<summary>Council Deliberation</summary>\n\n`;
        msg.stage1.forEach(resp => {
          markdown += `**${resp.model}:**\n${resp.response}\n\n`;
        });
        markdown += `</details>\n\n`;
      }

      markdown += `---\n\n`;
    });

    // Create and download file
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]/gi, '-').toLowerCase()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // No conversation selected
  if (!conversation) {
    return (
      <div className="claude-chat">
        <div className="claude-welcome">
          <div className="claude-welcome-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h1 className="claude-welcome-title">LLM Council</h1>
          <p className="claude-welcome-subtitle">Multi-model AI deliberation system. Select or create a conversation to get started.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="claude-chat">
      {/* Messages */}
      <div className="claude-messages" ref={messagesContainerRef} onScroll={handleScroll}>
        <div className="claude-messages-inner">
        {(!conversation.messages || conversation.messages.length === 0) ? (
          <div className="claude-welcome">
            <div className="claude-welcome-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {mode === 'council' ? (
                  <><circle cx="9" cy="7" r="4" /><circle cx="17" cy="11" r="4" /><path d="M3 21v-2a4 4 0 0 1 4-4h4" /><path d="M21 21v-2a4 4 0 0 0-3-3.85" /></>
                ) : mode === 'compare' ? (
                  <><path d="M12 3v18M3 12h18" /><path d="M3 6l3 3-3 3" /><path d="M21 6l-3 3 3 3" /></>
                ) : (
                  <><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></>
                )}
              </svg>
            </div>
            <h1 className="claude-welcome-title">{mode === 'council' ? 'Council Mode' : mode === 'compare' ? 'Compare Mode' : 'Quick Mode'}</h1>
            <p className="claude-welcome-subtitle">
              {mode === 'council'
                ? 'Get perspectives from multiple AI models working together'
                : mode === 'compare'
                  ? 'Compare responses from 2-3 models side by side'
                  : 'Fast responses from a single model'
              }
            </p>

            {/* Example prompts */}
            <div className="example-prompts">
              <p className="prompts-label">Try asking:</p>
              <div className="prompts-grid">
                {examplePrompts.map((prompt, i) => (
                  <button
                    key={i}
                    className="prompt-btn"
                    onClick={() => handleExampleClick(prompt.text)}
                  >
                    <span className="prompt-icon">{prompt.icon}</span>
                    {prompt.text}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          (conversation.messages || []).map((msg, i) => {
            // Get message content - handle council responses and regular messages
            // stage3 can be a string or {model, response} object
            const stage3Content = typeof msg.stage3 === 'object' ? msg.stage3?.response : msg.stage3;
            const content = msg.content || stage3Content || (msg.role === 'assistant' ? 'Response loading...' : '');
            const isCouncilResponse = msg.stage1 || msg.stage2 || msg.stage3;
            const isExpanded = expandedCouncil[i];

            return (
              <div key={i} className={`claude-message ${msg.role}`}>
                <div className="claude-message-avatar">
                  {msg.role === 'user' ? 'Y' : isCouncilResponse ? 'C' : 'A'}
                </div>
                <div className="claude-message-content">
                  <div className="claude-message-role">
                    {msg.role === 'user' ? 'You' : isCouncilResponse ? 'Council' : 'Assistant'}
                    {isCouncilResponse && (
                      <span className="claude-model-badge">Multi-model</span>
                    )}
                    {msg.role === 'user' && (
                      <button
                        className="claude-fork-btn"
                        onClick={() => handleForkConversation(i)}
                        title="Fork conversation from here"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="18" r="3" />
                          <circle cx="6" cy="6" r="3" />
                          <circle cx="18" cy="6" r="3" />
                          <path d="M18 9a9 9 0 0 1-9 9" />
                          <path d="M6 9a9 9 0 0 0 9 9" />
                        </svg>
                      </button>
                    )}
                  </div>
                  <div className="claude-message-text">
                    <SafeMarkdown components={{ code: CodeBlock }}>
                      {content}
                    </SafeMarkdown>
                  </div>

                  {/* Message actions */}
                  <div className="claude-message-actions">
                    <button
                      className={`message-action-btn ${copiedMessageIndex === i ? 'copied' : ''}`}
                      onClick={() => copyMessage(msg, i)}
                      title="Copy message"
                    >
                      {copiedMessageIndex === i ? (
                        <>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          Copied
                        </>
                      ) : (
                        <>
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                          </svg>
                          Copy
                        </>
                      )}
                    </button>
                  </div>

                  {/* Council details toggle */}
                  {isCouncilResponse && msg.role === 'assistant' && (
                    <>
                      <button
                        className="claude-council-toggle"
                        onClick={() => setExpandedCouncil(prev => ({ ...prev, [i]: !prev[i] }))}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d={isExpanded ? "M18 15l-6-6-6 6" : "M6 9l6 6 6-6"} />
                        </svg>
                        {isExpanded ? 'Hide Details' : 'View Council Details'}
                      </button>

                      {isExpanded && (
                        <div className="claude-council-details">
                          {msg.stage1 && (
                            <Stage1
                              responses={msg.stage1}
                              conversationId={conversation.id}
                              messageIndex={i}
                            />
                          )}
                          {msg.stage2 && (
                            <Stage2
                              rankings={msg.stage2}
                              labelToModel={msg.metadata?.label_to_model}
                              aggregateRankings={msg.metadata?.aggregate_rankings}
                            />
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Compare mode results - side by side */}
        {mode === 'compare' && (compareQuery || Object.keys(compareResponses).length > 0) && (
          <div className="compare-results">
            {compareQuery && (
              <div className="compare-query">
                <div className="message user">
                  <div className="message-content">
                    <p>{compareQuery}</p>
                  </div>
                  <div className="message-avatar user-avatar">
                    <span>👤</span>
                  </div>
                </div>
              </div>
            )}
            <div className={`compare-columns columns-${compareModels.length}`}>
              {compareModels.map(modelId => {
                const response = compareResponses[modelId] || { text: '', done: false, error: null };
                return (
                  <div key={modelId} className={`compare-column ${compareVote === modelId ? 'voted' : ''}`}>
                    <div className="compare-column-header">
                      <span className="compare-model-name">{getModelName(modelId)}</span>
                      {response.done && !response.error && (
                        <span className="compare-status done">✓</span>
                      )}
                      {!response.done && !response.error && (
                        <span className="compare-status loading">...</span>
                      )}
                      {response.error && (
                        <span className="compare-status error">!</span>
                      )}
                    </div>
                    <div className="compare-column-content">
                      {response.error ? (
                        <div className="compare-error">{response.error}</div>
                      ) : response.text ? (
                        <SafeMarkdown components={{ code: CodeBlock }}>
                          {response.text}
                        </SafeMarkdown>
                      ) : (
                        <div className="compare-loading">
                          <div className="skeleton skeleton-line"></div>
                          <div className="skeleton skeleton-line"></div>
                          <div className="skeleton skeleton-line"></div>
                        </div>
                      )}
                      {!response.done && response.text && (
                        <span className="cursor">|</span>
                      )}
                    </div>
                    {response.done && !response.error && (
                      <div className="compare-column-footer">
                        <button
                          className={`vote-btn ${compareVote === modelId ? 'voted' : ''}`}
                          onClick={() => setCompareVote(modelId)}
                          disabled={!response.done}
                        >
                          {compareVote === modelId ? '✓ Preferred' : 'This is better'}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            {compareVote && (
              <div className="compare-vote-result">
                You preferred: <strong>{getModelName(compareVote)}</strong>
              </div>
            )}
          </div>
        )}

        {/* Streaming response */}
        {streamingText && (
          <div className="claude-message assistant">
            <div className="claude-message-avatar">A</div>
            <div className="claude-message-content">
              <div className="claude-message-role">Assistant</div>
              <div className="claude-message-text">
                <SafeMarkdown components={{ code: CodeBlock }}>
                  {streamingText}
                </SafeMarkdown>
                <span className="cursor">|</span>
              </div>
            </div>
          </div>
        )}

        {/* Loading indicator - Progress for council mode, skeleton for others */}
        {(isLoading || (isStreaming && !streamingText)) && (
          mode === 'council' && councilProgress.stage > 0 ? (
            <ProgressIndicator
              stage={councilProgress.stage}
              models={councilProgress.models}
              modelProgress={councilProgress.modelProgress}
              chairmanModel={councilProgress.chairmanModel}
              chairmanStatus={councilProgress.chairmanStatus}
            />
          ) : (
            <div className="claude-thinking">
              <div className="claude-thinking-dots">
                <div className="claude-thinking-dot"></div>
                <div className="claude-thinking-dot"></div>
                <div className="claude-thinking-dot"></div>
              </div>
              <span>Thinking...</span>
            </div>
          )
        )}

        <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Scroll to bottom FAB */}
      {showScrollFab && (
        <button className="scroll-fab" onClick={scrollToBottom} title="Scroll to bottom">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12l7 7 7-7" />
          </svg>
        </button>
      )}

      {/* Input */}
      <div className="claude-input-area">
        <div className="claude-input-container">
          {/* Mode selector with inline model pickers */}
          <div className="claude-mode-selector">
            <button
              type="button"
              className={`claude-mode-btn ${mode === 'auto' ? 'active' : ''}`}
              onClick={() => setMode('auto')}
              data-tooltip="AI picks the best model for your question"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
              </svg>
              Auto
            </button>

            {/* Quick mode with model selector */}
            <div className="claude-mode-group">
              <button
                type="button"
                className={`claude-mode-btn ${mode === 'quick' ? 'active' : ''}`}
                onClick={() => setMode('quick')}
                data-tooltip="Fast response from one model"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                </svg>
                Quick
              </button>
              {mode === 'quick' && (
                <div className="inline-model-selector">
                  <button
                    type="button"
                    className="inline-model-btn"
                    onClick={() => setShowModelPicker(!showModelPicker)}
                    title="Select model"
                  >
                    <span className="inline-model-name">{getModelName(selectedModel)}</span>
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M6 9l6 6 6-6" />
                    </svg>
                  </button>
                  {showModelPicker && (
                    <>
                      <div className="model-picker-backdrop" onClick={() => { setShowModelPicker(false); setModelSearch(''); }} />
                      <div className="model-picker inline-picker">
                        <div className="model-picker-search">
                          <input
                            type="text"
                            placeholder="Search models..."
                            value={modelSearch}
                            onChange={(e) => setModelSearch(e.target.value)}
                            autoFocus
                          />
                        </div>
                        <div className="model-picker-list">
                          {!modelSearch && favoriteModels.length > 0 && (
                            <div className="model-group model-group-favorites">
                              <div className="model-group-header">
                                <span className="model-group-icon">⭐</span>
                                Favorites
                              </div>
                              {favoriteModels.filter(id => models[id]).map(id => {
                                const m = { id, ...models[id] };
                                return (
                                  <div
                                    key={m.id}
                                    className={`model-option ${selectedModel === m.id ? 'selected' : ''}`}
                                    onClick={() => selectModel(m.id)}
                                  >
                                    <span
                                      className="favorite-btn favorited"
                                      onClick={(e) => toggleFavorite(m.id, e)}
                                      title="Remove from favorites"
                                      role="button"
                                      tabIndex={0}
                                    >
                                      <svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth="1">
                                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                                      </svg>
                                    </span>
                                    <span className="model-option-name">{m.name}</span>
                                    {m.id.includes(':free') && <span className="model-badge free">FREE</span>}
                                  </div>
                                );
                              })}
                              <div className="model-group-divider" />
                            </div>
                          )}
                          {!modelSearch && recentModels.length > 0 && (
                            <div className="model-group model-group-recent">
                              <div className="model-group-header">
                                <span className="model-group-icon">🕐</span>
                                Recent
                              </div>
                              {recentModels
                                .filter(id => models[id] && !favoriteModels.includes(id))
                                .slice(0, MAX_RECENT_MODELS)
                                .map(id => {
                                  const m = { id, ...models[id] };
                                  return (
                                    <div
                                      key={m.id}
                                      className={`model-option ${selectedModel === m.id ? 'selected' : ''}`}
                                      onClick={() => selectModel(m.id)}
                                    >
                                      <span
                                        className="favorite-btn"
                                        onClick={(e) => toggleFavorite(m.id, e)}
                                        title="Add to favorites"
                                        role="button"
                                        tabIndex={0}
                                      >
                                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                                        </svg>
                                      </span>
                                      <span className="model-option-name">{m.name}</span>
                                      {m.id.includes(':free') && <span className="model-badge free">FREE</span>}
                                    </div>
                                  );
                                })}
                              <div className="model-group-divider" />
                            </div>
                          )}
                          {!modelSearch && filteredModels.popular.length > 0 && (
                            <div className="model-group model-group-popular">
                              <div className="model-group-header">
                                <span className="model-group-icon">🔥</span>
                                Popular
                              </div>
                              {filteredModels.popular.slice(0, 6).map(m => (
                                <div
                                  key={m.id}
                                  className={`model-option ${selectedModel === m.id ? 'selected' : ''}`}
                                  onClick={() => selectModel(m.id)}
                                >
                                  <span
                                    className={`favorite-btn ${favoriteModels.includes(m.id) ? 'favorited' : ''}`}
                                    onClick={(e) => toggleFavorite(m.id, e)}
                                    title={favoriteModels.includes(m.id) ? "Remove from favorites" : "Add to favorites"}
                                    role="button"
                                    tabIndex={0}
                                  >
                                    <svg viewBox="0 0 24 24" fill={favoriteModels.includes(m.id) ? "currentColor" : "none"} stroke="currentColor" strokeWidth={favoriteModels.includes(m.id) ? "1" : "2"}>
                                      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                                    </svg>
                                  </span>
                                  <span className="model-option-name">{m.name}</span>
                                  {m.id.includes(':free') && <span className="model-badge free">FREE</span>}
                                </div>
                              ))}
                              <div className="model-group-divider" />
                            </div>
                          )}
                          {!modelSearch && Object.keys(filteredModels.groups).length > 0 && (
                            <div className="model-providers-header">All Providers</div>
                          )}
                          {Object.entries(filteredModels.groups).map(([provider, modelList]) => {
                            const isCollapsed = !modelSearch && collapsedGroups[provider];
                            const displayList = modelSearch ? modelList : modelList.slice(0, 8);
                            return (
                              <div key={provider} className={`model-group model-group-provider ${isCollapsed ? 'collapsed' : ''}`}>
                                <div
                                  className="model-group-header model-group-accordion"
                                  onClick={() => !modelSearch && toggleProviderGroup(provider)}
                                  role="button"
                                  tabIndex={0}
                                >
                                  <span className="model-group-name">{provider}</span>
                                  <span className="model-group-count">{modelList.length}</span>
                                  {!modelSearch && (
                                    <svg className={`model-group-chevron ${isCollapsed ? '' : 'expanded'}`} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                      <path d="M6 9l6 6 6-6" />
                                    </svg>
                                  )}
                                </div>
                                {!isCollapsed && displayList.map(m => (
                                  <div
                                    key={m.id}
                                    className={`model-option ${selectedModel === m.id ? 'selected' : ''}`}
                                    onClick={() => selectModel(m.id)}
                                  >
                                    <span
                                      className={`favorite-btn ${favoriteModels.includes(m.id) ? 'favorited' : ''}`}
                                      onClick={(e) => toggleFavorite(m.id, e)}
                                      title={favoriteModels.includes(m.id) ? "Remove from favorites" : "Add to favorites"}
                                      role="button"
                                      tabIndex={0}
                                    >
                                      <svg viewBox="0 0 24 24" fill={favoriteModels.includes(m.id) ? "currentColor" : "none"} stroke="currentColor" strokeWidth={favoriteModels.includes(m.id) ? "1" : "2"}>
                                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                                      </svg>
                                    </span>
                                    <span className="model-option-name">{m.name}</span>
                                    {m.id.includes(':free') && <span className="model-badge free">FREE</span>}
                                  </div>
                                ))}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

            <button
              type="button"
              className={`claude-mode-btn ${mode === 'council' ? 'active' : ''}`}
              onClick={() => setMode('council')}
              data-tooltip="Multiple AIs discuss and synthesize an answer"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
              Council
            </button>

            {/* Compare mode with model selector */}
            <div className="claude-mode-group">
              <button
                type="button"
                className={`claude-mode-btn ${mode === 'compare' ? 'active' : ''}`}
                onClick={() => setMode('compare')}
                data-tooltip="See responses from 2-3 models side by side"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="7" height="18" rx="1"/>
                  <rect x="14" y="3" width="7" height="18" rx="1"/>
                </svg>
                Compare
              </button>
              {mode === 'compare' && (
                <div className="inline-compare-selector">
                  {compareModels.length > 0 && (
                    <div className="inline-compare-chips">
                      {compareModels.map(modelId => (
                        <span key={modelId} className="inline-compare-chip">
                          {getModelName(modelId)}
                          <button
                            type="button"
                            className="inline-chip-remove"
                            onClick={(e) => {
                              e.stopPropagation();
                              setCompareModels(prev => prev.filter(m => m !== modelId));
                            }}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                  <button
                    type="button"
                    className="inline-compare-add"
                    onClick={() => setShowCompareModelPicker(!showCompareModelPicker)}
                    title={compareModels.length < 3 ? "Add model" : "Max 3 models"}
                    disabled={compareModels.length >= 3}
                  >
                    {compareModels.length === 0 ? 'Select models' : '+'}
                  </button>
                  {showCompareModelPicker && (
                    <>
                      <div className="model-picker-backdrop" onClick={() => { setShowCompareModelPicker(false); setModelSearch(''); }} />
                      <div className="model-picker inline-picker compare-inline-picker">
                        <div className="model-picker-search">
                          <input
                            type="text"
                            placeholder="Search models..."
                            value={modelSearch}
                            onChange={(e) => setModelSearch(e.target.value)}
                            autoFocus
                          />
                        </div>
                        <div className="compare-picker-hint">
                          Select 2-3 models to compare
                        </div>
                        <div className="model-picker-list">
                          {!modelSearch && filteredModels.popular.length > 0 && (
                            <div className="model-group">
                              <div className="model-group-header">Popular</div>
                              {filteredModels.popular.map(m => (
                                <button
                                  key={m.id}
                                  type="button"
                                  className={`model-option ${compareModels.includes(m.id) ? 'selected' : ''} ${compareModels.length >= 3 && !compareModels.includes(m.id) ? 'disabled' : ''}`}
                                  onClick={() => {
                                    if (compareModels.includes(m.id)) {
                                      setCompareModels(prev => prev.filter(id => id !== m.id));
                                    } else if (compareModels.length < 3) {
                                      setCompareModels(prev => [...prev, m.id]);
                                    }
                                  }}
                                  disabled={compareModels.length >= 3 && !compareModels.includes(m.id)}
                                >
                                  <span className="model-option-checkbox">{compareModels.includes(m.id) ? '✓' : ''}</span>
                                  <span className="model-option-name">{m.name}</span>
                                </button>
                              ))}
                            </div>
                          )}
                          {Object.entries(filteredModels.groups).map(([provider, modelList]) => (
                            <div key={provider} className="model-group">
                              <div className="model-group-header">{provider}</div>
                              {modelList.slice(0, modelSearch ? 100 : 5).map(m => (
                                <button
                                  key={m.id}
                                  type="button"
                                  className={`model-option ${compareModels.includes(m.id) ? 'selected' : ''} ${compareModels.length >= 3 && !compareModels.includes(m.id) ? 'disabled' : ''}`}
                                  onClick={() => {
                                    if (compareModels.includes(m.id)) {
                                      setCompareModels(prev => prev.filter(id => id !== m.id));
                                    } else if (compareModels.length < 3) {
                                      setCompareModels(prev => [...prev, m.id]);
                                    }
                                  }}
                                  disabled={compareModels.length >= 3 && !compareModels.includes(m.id)}
                                >
                                  <span className="model-option-checkbox">{compareModels.includes(m.id) ? '✓' : ''}</span>
                                  <span className="model-option-name">{m.name}</span>
                                </button>
                              ))}
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            {/* Uploaded Files Preview */}
            {uploadedFiles.length > 0 && (
              <div className="uploaded-files-preview">
                {uploadedFiles.map((file, index) => (
                  <div key={index} className="uploaded-file-chip">
                    <span className="uploaded-file-icon">📎</span>
                    <span className="uploaded-file-name">{file.name || file.filename}</span>
                    <button
                      type="button"
                      className="remove-uploaded-file"
                      onClick={() => setUploadedFiles(prev => prev.filter((_, i) => i !== index))}
                      title="Remove file"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* Pasted Images Preview */}
            {pastedImages.length > 0 && (
              <div className="pasted-images-preview">
                {pastedImages.map(img => (
                  <div key={img.id} className="pasted-image-item">
                    <img src={img.dataUrl} alt="Pasted" />
                    <button
                      type="button"
                      className="remove-pasted-image"
                      onClick={() => removePastedImage(img.id)}
                      title="Remove image"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="claude-input-wrapper">
              <textarea
                ref={textareaRef}
                className="claude-textarea"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
                placeholder={isListening ? "Listening..." : (mode === 'council' ? "Ask the council..." : mode === 'compare' ? "Compare models..." : "Message...")}
                disabled={isLoading || isStreaming || isComparing}
                rows={1}
              />

              {/* File upload button */}
              <button
                type="button"
                onClick={() => setShowFileUpload(true)}
                className="file-btn"
                disabled={isLoading || isStreaming || isComparing || !activeConversationId}
                title={!activeConversationId ? "Start a conversation first to upload files" : "Upload files (PDF, docs, code)"}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </button>

              {/* Voice input button */}
              {speechSupported && (
                <button
                  type="button"
                  onClick={toggleListening}
                  className={`voice-btn ${isListening ? 'listening' : ''}`}
                  disabled={isLoading || isStreaming || isComparing}
                  title={isListening ? "Stop listening" : "Voice input"}
                >
                  {isListening ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                      <rect x="6" y="6" width="12" height="12" rx="2" />
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                      <line x1="12" y1="19" x2="12" y2="23" />
                      <line x1="8" y1="23" x2="16" y2="23" />
                    </svg>
                  )}
                </button>
              )}

              {/* Options toggle */}
              <div className="options-toggle-wrapper">
                <button
                  type="button"
                  className={`options-toggle-btn ${showOptions ? 'active' : ''} ${(features.web_search || features.deep_search || features.memory || features.code_execution) ? 'has-active' : ''}`}
                  onClick={() => setShowOptions(!showOptions)}
                  title="Options"
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                  </svg>
                </button>
                {showOptions && (
                  <>
                    <div className="options-backdrop" onClick={() => setShowOptions(false)} />
                    <div className="options-panel">
                      <div className="options-header">
                        <span>Options</span>
                        <button className="options-close" onClick={() => setShowOptions(false)}>×</button>
                      </div>
                      <div className="options-grid">
                        <button
                          type="button"
                          className={`option-btn ${features.web_search ? 'active' : ''}`}
                          onClick={() => toggleFeature('web_search')}
                        >
                          <span className="option-icon">🔍</span>
                          <span className="option-label">Web Search</span>
                        </button>
                        <button
                          type="button"
                          className={`option-btn ${features.deep_search ? 'active' : ''}`}
                          onClick={() => toggleFeature('deep_search')}
                        >
                          <span className="option-icon">🧭</span>
                          <span className="option-label">Deep Search</span>
                        </button>
                        <button
                          type="button"
                          className={`option-btn ${features.memory ? 'active' : ''}`}
                          onClick={() => toggleFeature('memory')}
                        >
                          <span className="option-icon">🧠</span>
                          <span className="option-label">Memory</span>
                        </button>
                        <button
                          type="button"
                          className={`option-btn ${features.code_execution ? 'active' : ''}`}
                          onClick={() => toggleFeature('code_execution')}
                        >
                          <span className="option-icon">💻</span>
                          <span className="option-label">Code Exec</span>
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Stop/Send button */}
              {(isLoading || isStreaming || isComparing) ? (
                <button
                  type="button"
                  onClick={() => {
                    if (mode === 'compare') {
                      handleStopCompare();
                    } else if (mode === 'council' && onStopCouncil) {
                      onStopCouncil();
                    } else {
                      handleStop();
                    }
                  }}
                  className="claude-stop-btn"
                  title="Stop generating"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="12" height="12" rx="2" />
                  </svg>
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={(!input.trim() && pastedImages.length === 0) || (mode === 'compare' && compareModels.length < 2)}
                  className="claude-send-btn"
                  title="Send message"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                  </svg>
                </button>
              )}
            </div>
          </form>

          {/* Input hints */}
          <div className="claude-input-hints">
            <span className="claude-input-hint">
              <kbd>Enter</kbd> send
            </span>
            <span className="claude-input-hint hint-separator">·</span>
            <button
              type="button"
              className="claude-input-hint hint-btn"
              onClick={() => setShowShortcuts(true)}
              title="Keyboard shortcuts"
            >
              <kbd>⌘?</kbd> shortcuts
            </button>
            {conversation?.messages?.length > 0 && (
              <>
                <span className="claude-input-hint hint-separator">·</span>
                <button
                  type="button"
                  className="claude-input-hint hint-btn"
                  onClick={copyConversation}
                  title="Copy entire conversation"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginRight: '4px', verticalAlign: 'middle'}}>
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                  </svg>
                  copy all
                </button>
                <span className="claude-input-hint hint-separator">·</span>
                <button
                  type="button"
                  className="claude-input-hint hint-btn"
                  onClick={exportConversation}
                  title="Export conversation"
                >
                  ↓ export
                </button>
              </>
            )}
            {mode === 'council' && councilCostEstimate && (
              <>
                <span className="claude-input-hint hint-separator">·</span>
                <span className="claude-input-hint">
                  ~{councilCostEstimate.cost}
                </span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Keyboard Shortcuts Modal */}
      {showShortcuts && (
        <div className="shortcuts-overlay" onClick={() => setShowShortcuts(false)}>
          <div className="shortcuts-modal" onClick={(e) => e.stopPropagation()}>
            <div className="shortcuts-header">
              <h2>⌨️ Keyboard Shortcuts</h2>
              <button className="close-btn" onClick={() => setShowShortcuts(false)}>×</button>
            </div>
            <div className="shortcuts-content">
              <div className="shortcut-group">
                <h3>Navigation</h3>
                <div className="shortcut-item">
                  <span className="shortcut-keys"><kbd>⌘</kbd> + <kbd>K</kbd></span>
                  <span className="shortcut-desc">New conversation / Search</span>
                </div>
                <div className="shortcut-item">
                  <span className="shortcut-keys"><kbd>⌘</kbd> + <kbd>N</kbd></span>
                  <span className="shortcut-desc">New conversation</span>
                </div>
                <div className="shortcut-item">
                  <span className="shortcut-keys"><kbd>⌘</kbd> + <kbd>/</kbd></span>
                  <span className="shortcut-desc">Toggle sidebar</span>
                </div>
                <div className="shortcut-item">
                  <span className="shortcut-keys"><kbd>Esc</kbd></span>
                  <span className="shortcut-desc">Close modals / sidebar</span>
                </div>
              </div>
              <div className="shortcut-group">
                <h3>Messaging</h3>
                <div className="shortcut-item">
                  <span className="shortcut-keys"><kbd>Enter</kbd></span>
                  <span className="shortcut-desc">Send message</span>
                </div>
                <div className="shortcut-item">
                  <span className="shortcut-keys"><kbd>Shift</kbd> + <kbd>Enter</kbd></span>
                  <span className="shortcut-desc">New line</span>
                </div>
              </div>
              <div className="shortcut-group">
                <h3>Actions</h3>
                <div className="shortcut-item">
                  <span className="shortcut-keys">🎤 Voice</span>
                  <span className="shortcut-desc">Click mic button for voice input</span>
                </div>
                <div className="shortcut-item">
                  <span className="shortcut-keys">📥 Export</span>
                  <span className="shortcut-desc">Download conversation as Markdown</span>
                </div>
                <div className="shortcut-item">
                  <span className="shortcut-keys">📎 Upload</span>
                  <span className="shortcut-desc">Upload files (PDF, docs, code)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* File Upload Modal */}
      {showFileUpload && activeConversationId && (
        <FileUpload
          conversationId={activeConversationId}
          onFileUploaded={(files) => {
            setUploadedFiles(prev => [...prev, ...files]);
          }}
          onClose={() => setShowFileUpload(false)}
        />
      )}

      {/* Cost Estimate Modal */}
      <CostEstimate
        messageLength={pendingMessage?.message?.length || 0}
        onConfirm={handleCostEstimateConfirm}
        onCancel={handleCostEstimateCancel}
        isVisible={showCostEstimate}
      />
    </div>
  );
}
