import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './ChatInterface.css';
import { api } from '../api';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import FileUpload from './FileUpload';
import ProgressIndicator from './ProgressIndicator';
import CostEstimate from './CostEstimate';

// Estimate tokens for cost calculation
const ESTIMATED_INPUT_TOKENS = 500;  // Average input tokens per model
const ESTIMATED_OUTPUT_TOKENS = 1000; // Average output tokens per model

// localStorage keys for favorites and recent models
const FAVORITES_STORAGE_KEY = 'llm-council-favorites';
const RECENT_STORAGE_KEY = 'llm-council-recent';
const MAX_RECENT_MODELS = 5;

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
  onSendMessage,
  isLoading,
  onStopCouncil,
  onConversationUpdate,
  councilProgress = { stage: 0, models: [], modelProgress: {}, chairmanModel: '', chairmanStatus: 'pending' },
}) {
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
  // Settings panel state
  const [showSettings, setShowSettings] = useState(false);
  const [features, setFeatures] = useState({ memory: true, web_search: true, code_execution: true });
  const [memoryContext, setMemoryContext] = useState('');
  const [memoryStats, setMemoryStats] = useState(null);
  const [systemInstructions, setSystemInstructions] = useState('');
  // File upload state
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  // Cost estimate state
  const [showCostEstimate, setShowCostEstimate] = useState(false);
  const [pendingMessage, setPendingMessage] = useState(null);
  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const textareaRef = useRef(null);
  const recognitionRef = useRef(null);
  const abortControllerRef = useRef(null);

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

  const toggleListening = () => {
    if (!recognitionRef.current) return;

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.start();
      setIsListening(true);
      textareaRef.current?.focus();
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
    }).catch(() => {
      setSelectedModel('anthropic/claude-sonnet-4');
    });
  }, []);

  // Load features (memory, web_search, etc.)
  useEffect(() => {
    api.getFeatures().then(setFeatures).catch(console.error);
  }, []);

  // Load memory when settings panel opens
  const loadMemory = useCallback(async () => {
    try {
      const [context, stats] = await Promise.all([
        api.getMemoryContext(),
        api.getMemoryStats()
      ]);
      setMemoryContext(context.context || 'No memories stored yet.');
      setMemoryStats(stats);
    } catch (e) {
      console.error('Failed to load memory:', e);
    }
  }, []);

  useEffect(() => {
    if (showSettings) {
      loadMemory();
    }
  }, [showSettings, loadMemory]);

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

  // Clear memory
  const handleClearMemory = async () => {
    if (!confirm('Clear all stored memories? This cannot be undone.')) return;
    try {
      await api.clearMemory();
      await loadMemory();
    } catch (e) {
      console.error('Failed to clear memory:', e);
    }
  };

  // Save system instructions as preference
  const saveInstructions = async () => {
    try {
      await api.setPreference('system_instructions', systemInstructions);
      alert('Instructions saved!');
    } catch (e) {
      console.error('Failed to save instructions:', e);
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

  // Filter models by search
  const filteredModels = useMemo(() => {
    if (!modelSearch) return groupedModels;

    const query = modelSearch.toLowerCase();
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
  }, [groupedModels, modelSearch]);

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
          compareAbortControllersRef.current[modelId].signal
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

      onSendMessage(messageWithImages, files);
    } else if (mode === 'compare') {
      // Compare mode - parallel queries to multiple models
      // Comparison typically doesn't support complex file context yet across all models easily
      handleCompareSubmit(message);
    } else {
      // Quick mode - stream directly
      setStreamingText('');
      setRouteInfo(null);

      // Create abort controller for cancellation
      abortControllerRef.current = new AbortController();
      let streamCompleted = false;

      // Determine which model to use
      let modelToUse = selectedModel;
      if (autoMode) {
        try {
          // Get smart recommendation based on query
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
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'quick-frontend',hypothesisId:'H36',location:'ChatInterface.jsx:587',message:'quick_event_received',data:{event_type:type,has_data:!!event.data,has_message:!!event.message},timestamp:Date.now()})}).catch(()=>{});
            // #endregion
            if (type === 'chunk') {
              setStreamingText(prev => prev + event.data);
            } else if (type === 'complete' || type === 'title_complete') {
              streamCompleted = true;
              setStreamingText('');
              onConversationUpdate?.(conversation.id);
            } else if (type === 'error') {
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'quick-frontend-error',hypothesisId:'H37',location:'ChatInterface.jsx:595',message:'quick_error_received',data:{error_message:event.message||'unknown',event:event},timestamp:Date.now()})}).catch(()=>{});
              // #endregion
              streamCompleted = true;
              setStreamingText('');
              console.error('Quick message error:', event.message || event);
            }
          },
          abortControllerRef.current.signal,
          files // Pass attached files
        );
      } catch (err) {
        if (err.name !== 'AbortError') {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'quick-frontend-exception',hypothesisId:'H38',location:'ChatInterface.jsx:602',message:'quick_exception',data:{error_name:err.name,error_message:err.message,error_stack:err.stack?.substring(0,500)},timestamp:Date.now()})}).catch(()=>{});
          // #endregion
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
      onSendMessage(pendingMessage.message, pendingMessage.files);
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
      <div className="chat">
        <div className="chat-empty">
          <div className="empty-icon">🤖</div>
          <h1>AI Konsey</h1>
          <p>Multi-model AI deliberation system</p>
          <p className="empty-hint">Create a new conversation to start</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat">
      {/* Header with mode toggle and model selector */}
      <div className="chat-header">
        {/* Mode Toggle Tabs */}
        <div className="mode-tabs">
          <button
            className={`mode-tab ${mode === 'quick' ? 'active' : ''}`}
            onClick={() => setMode('quick')}
          >
            <span className="mode-icon">⚡</span>
            Quick
          </button>
          <button
            className={`mode-tab ${mode === 'council' ? 'active' : ''}`}
            onClick={() => setMode('council')}
          >
            <span className="mode-icon">👥</span>
            Council
          </button>
          <button
            className={`mode-tab ${mode === 'compare' ? 'active' : ''}`}
            onClick={() => setMode('compare')}
          >
            <span className="mode-icon">⚖️</span>
            Compare
          </button>
        </div>

        {/* Model Selector (only in quick mode) */}
        {mode === 'quick' && (
          <div className="model-selector-wrapper">
            {/* Auto mode toggle */}
            <button
              className={`auto-mode-btn ${autoMode ? 'active' : ''}`}
              onClick={() => setAutoMode(!autoMode)}
              title={autoMode ? "Auto-select enabled: Best model chosen based on query" : "Click to enable auto model selection"}
            >
              <span className="auto-icon">🎯</span>
              <span className="auto-label">Auto</span>
            </button>

            <div className="model-selector">
              <button
                className={`model-selector-btn ${autoMode ? 'auto-mode' : ''}`}
                onClick={() => !autoMode && setShowModelPicker(!showModelPicker)}
                disabled={autoMode}
                title={autoMode ? "Auto mode is selecting the best model" : "Select a model"}
              >
                <span className="model-name">{autoMode ? 'Auto-Select' : getModelName(selectedModel)}</span>
                {!autoMode && (
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                )}
              </button>

              {showModelPicker && (
                <>
                  <div className="model-picker-backdrop" onClick={() => { setShowModelPicker(false); setModelSearch(''); }} />
                  <div className="model-picker">
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
                      {/* Favorites section */}
                      {!modelSearch && favoriteModels.length > 0 && (
                        <div className="model-group model-group-favorites">
                          <div className="model-group-header">Favorites</div>
                          {favoriteModels
                            .filter(id => models[id])
                            .map(id => {
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
                        </div>
                      )}

                      {/* Recent models section */}
                      {!modelSearch && recentModels.length > 0 && (
                        <div className="model-group model-group-recent">
                          <div className="model-group-header">Recent</div>
                          {recentModels
                            .filter(id => models[id] && !favoriteModels.includes(id))
                            .slice(0, 5)
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
                        </div>
                      )}

                      {/* Popular models */}
                      {!modelSearch && filteredModels.popular.length > 0 && (
                        <div className="model-group">
                          <div className="model-group-header">Popular</div>
                          {filteredModels.popular.map(m => (
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
                      )}

                      {/* Grouped by provider */}
                      {Object.entries(filteredModels.groups).map(([provider, modelList]) => (
                        <div key={provider} className="model-group">
                          <div className="model-group-header">{provider}</div>
                          {modelList.slice(0, modelSearch ? 100 : 5).map(m => (
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
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Route info badge when auto mode is used */}
            {routeInfo && (
              <div className="route-info-badge">
                <span className="route-model">Using: {routeInfo.model}</span>
                <span className="route-reason">({routeInfo.queryType} - {routeInfo.reason})</span>
              </div>
            )}
          </div>
        )}

        {/* Council info badge */}
        {mode === 'council' && (
          <div className="council-badge">
            Multiple AI models will deliberate on your query
          </div>
        )}

        {/* Compare mode model selector */}
        {mode === 'compare' && (
          <div className="compare-model-selector">
            <button
              className="compare-selector-btn"
              onClick={() => setShowCompareModelPicker(!showCompareModelPicker)}
            >
              <span className="compare-models-label">
                {compareModels.length === 0
                  ? 'Select 2-3 models'
                  : `${compareModels.length} model${compareModels.length > 1 ? 's' : ''}`}
              </span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M6 9l6 6 6-6" />
              </svg>
            </button>

            {compareModels.length > 0 && (
              <div className="compare-selected-chips">
                {compareModels.map(modelId => (
                  <span key={modelId} className="compare-chip">
                    {getModelName(modelId)}
                    <button
                      className="compare-chip-remove"
                      onClick={(e) => {
                        e.stopPropagation();
                        setCompareModels(prev => prev.filter(m => m !== modelId));
                      }}
                    >
                      x
                    </button>
                  </span>
                ))}
              </div>
            )}

            {showCompareModelPicker && (
              <>
                <div className="model-picker-backdrop" onClick={() => { setShowCompareModelPicker(false); setModelSearch(''); }} />
                <div className="model-picker compare-picker">
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

        {/* Export button */}
        {conversation?.messages?.length > 0 && (
          <button
            className="export-btn"
            onClick={exportConversation}
            title="Export conversation as Markdown"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
          </button>
        )}

        {/* Keyboard shortcuts button */}
        <button
          className="shortcuts-btn"
          onClick={() => setShowShortcuts(true)}
          title="Keyboard shortcuts"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="4" width="20" height="16" rx="2" />
            <path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10" />
          </svg>
        </button>

        {/* Settings button */}
        <button
          className={`settings-btn ${showSettings ? 'active' : ''}`}
          onClick={() => setShowSettings(!showSettings)}
          title="Settings & Memory"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="3" />
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
          </svg>
        </button>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="settings-panel">
          <div className="settings-header">
            <h3>⚙️ Settings & Memory</h3>
            <button className="close-btn" onClick={() => setShowSettings(false)}>×</button>
          </div>

          {/* Feature Toggles */}
          <div className="settings-section">
            <h4>Features</h4>
            <div className="feature-toggles">
              <label className="toggle-item">
                <input
                  type="checkbox"
                  checked={features.memory}
                  onChange={() => toggleFeature('memory')}
                />
                <span className="toggle-label">🧠 Memory</span>
                <span className="toggle-desc">Remember facts & decisions across sessions</span>
              </label>
              <label className="toggle-item">
                <input
                  type="checkbox"
                  checked={features.web_search}
                  onChange={() => toggleFeature('web_search')}
                />
                <span className="toggle-label">🔍 Web Search</span>
                <span className="toggle-desc">Search the web for current information</span>
              </label>
              <label className="toggle-item">
                <input
                  type="checkbox"
                  checked={features.code_execution}
                  onChange={() => toggleFeature('code_execution')}
                />
                <span className="toggle-label">💻 Code Execution</span>
                <span className="toggle-desc">Run Python/JavaScript code</span>
              </label>
            </div>
          </div>

          {/* System Instructions */}
          <div className="settings-section">
            <h4>System Instructions</h4>
            <p className="section-desc">Custom instructions for all conversations</p>
            <textarea
              className="instructions-input"
              value={systemInstructions}
              onChange={(e) => setSystemInstructions(e.target.value)}
              placeholder="e.g., Always respond in a formal tone. Focus on technical accuracy..."
              rows={4}
            />
            <button className="save-btn" onClick={saveInstructions}>
              Save Instructions
            </button>
          </div>

          {/* Memory View */}
          <div className="settings-section">
            <h4>Memory</h4>
            {memoryStats && (
              <div className="memory-stats">
                <span>📝 {memoryStats.facts_count} facts</span>
                <span>📋 {memoryStats.decisions_count} decisions</span>
                <span>⚙️ {memoryStats.preferences_count} preferences</span>
              </div>
            )}
            <div className="memory-content">
              <pre>{memoryContext}</pre>
            </div>
            <div className="memory-actions">
              <button className="refresh-btn" onClick={loadMemory}>
                🔄 Refresh
              </button>
              <button className="clear-btn" onClick={handleClearMemory}>
                🗑️ Clear All
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages" ref={messagesContainerRef} onScroll={handleScroll}>
        {(!conversation.messages || conversation.messages.length === 0) ? (
          <div className="chat-welcome">
            <h2>{mode === 'council' ? '👥 Council Mode' : mode === 'compare' ? '⚖️ Compare Mode' : '⚡ Quick Mode'}</h2>
            <p className="welcome-subtitle">
              {mode === 'council'
                ? 'Get perspectives from multiple AI models'
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
              <div key={i} className={`message ${msg.role}`}>
                {msg.role === 'assistant' && (
                  <div className="message-avatar">
                    <span>{isCouncilResponse ? '👥' : '🤖'}</span>
                  </div>
                )}
                <div className="message-content">
                  <ReactMarkdown components={{ code: CodeBlock }}>
                    {content}
                  </ReactMarkdown>

                  {/* Council details toggle */}
                  {isCouncilResponse && msg.role === 'assistant' && (
                    <div className="council-details">
                      <button
                        className="council-toggle-btn"
                        onClick={() => setExpandedCouncil(prev => ({ ...prev, [i]: !prev[i] }))}
                      >
                        {isExpanded ? '▼ Hide Council Details' : '▶ Show Council Details'}
                      </button>

                      {isExpanded && (
                        <div className="council-stages">
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
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <>
                    <div className="message-actions">
                      <button
                        className="fork-btn"
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
                    </div>
                    <div className="message-avatar user-avatar">
                      <span>👤</span>
                    </div>
                  </>
                )}
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
                        <ReactMarkdown components={{ code: CodeBlock }}>
                          {response.text}
                        </ReactMarkdown>
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
          <div className="message assistant">
            <div className="message-avatar">
              <span>🤖</span>
            </div>
            <div className="message-content">
              <ReactMarkdown components={{ code: CodeBlock }}>
                {streamingText}
              </ReactMarkdown>
              <span className="cursor">|</span>
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
            <div className="message assistant">
              <div className="message-skeleton">
                <div className="skeleton skeleton-line"></div>
                <div className="skeleton skeleton-line"></div>
                <div className="skeleton skeleton-line"></div>
              </div>
            </div>
          )
        )}

        <div ref={messagesEndRef} />
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
      <form className="chat-input" onSubmit={handleSubmit}>
        {/* Uploaded Files Preview */}
        {uploadedFiles.length > 0 && (
          <div className="uploaded-files-preview">
            {uploadedFiles.map((file, index) => (
              <div key={index} className="uploaded-file-chip">
                <span className="uploaded-file-icon">📎</span>
                <span className="uploaded-file-name">{file.name || file.filename}</span>
                <button
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

        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={isListening ? "Listening... speak now" : (mode === 'council' ? "Ask the council..." : mode === 'compare' ? "Ask the same question to all models..." : pastedImages.length > 0 ? "Add a message about your image(s)..." : "Message (paste images with Ctrl+V)...")}
          disabled={isLoading || isStreaming || isComparing}
          rows={1}
        />

        {/* File upload button */}
        <button
          type="button"
          onClick={() => setShowFileUpload(true)}
          className="file-btn"
          disabled={isLoading || isStreaming || isComparing || !conversation}
          title="Upload files"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
              <svg viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            )}
            {isListening && <span className="listening-indicator"></span>}
          </button>
        )}

        {/* Stop button when loading/streaming/comparing */}
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
            className="stop-btn"
            title="Stop generating"
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          </button>
        ) : (
          <button
            type="submit"
            disabled={(!input.trim() && pastedImages.length === 0) || (mode === 'compare' && compareModels.length < 2)}
            className="send-btn"
            title="Send message"
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 21l21-9-21-9v7l15 2-15 2z" />
            </svg>
          </button>
        )}
      </form>

      {/* Cost estimate for council mode */}
      {mode === 'council' && councilCostEstimate && (
        <div className="cost-estimate">
          <span className="cost-estimate-icon">$</span>
          <span className="cost-estimate-text">
            Est. cost: {councilCostEstimate.cost} for {councilCostEstimate.modelCount} model{councilCostEstimate.modelCount !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Keyboard hint */}
      {(!conversation.messages || conversation.messages.length === 0) && (
        <div className="keyboard-hint">
          <kbd>Enter</kbd> to send · <kbd>Shift</kbd> + <kbd>Enter</kbd> for new line
        </div>
      )}

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
      {showFileUpload && conversation && (
        <FileUpload
          conversationId={conversation.id}
          onFileUploaded={(files) => {
            setUploadedFiles(prev => [...prev, ...files]);
          }}
          onClose={() => setShowFileUpload(false)}
        />
      )}
    </div>
  );
}
