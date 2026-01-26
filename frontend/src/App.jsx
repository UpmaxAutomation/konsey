import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import ClaudeSidebar from './components/ClaudeSidebar';
import ChatInterface from './components/ChatInterface';
import ProjectView from './components/ProjectView';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import SharedConversation from './pages/SharedConversation';
import TeamManager from './components/TeamManager';
import APIKeysManager from './components/APIKeysManager';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import { useAuth } from './contexts/AuthContext';
import { useToast } from './components/Toast';
import { api, API_BASE } from './api';
import { getUserFriendlyMessage, NetworkError } from './utils/errors';
import './App.css';
import './pages/Auth.css';

// Main app content (protected)
function MainApp() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [currentProjectId, setCurrentProjectId] = useState(null); // null = all chats
  const [selectedProject, setSelectedProject] = useState(null); // Full project object for ProjectView
  const [isLoading, setIsLoading] = useState(false);
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);
  const [budgetAlerts, setBudgetAlerts] = useState({ alerts: [], exceeded: false, exceeded_periods: [] });
  const [showBudgetBanner, setShowBudgetBanner] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showTeamManager, setShowTeamManager] = useState(false);
  const [showAPIKeysManager, setShowAPIKeysManager] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const toast = useToast();
  const autoCreateChatRef = useRef(false);
  // Council progress tracking
  const [councilProgress, setCouncilProgress] = useState({
    stage: 0,
    models: [],
    modelProgress: {},
    chairmanModel: '',
    chairmanStatus: 'pending',
    contextStatus: null,
    searchType: null
  });
  const budgetTimeoutRef = useRef(null);
  const councilAbortRef = useRef(null);

  // Clean up budget timeout on unmount
  useEffect(() => {
    return () => {
      if (budgetTimeoutRef.current) {
        clearTimeout(budgetTimeoutRef.current);
      }
    };
  }, []);

  // Check API keys on mount and warn if missing
  const checkApiKeys = async () => {
    try {
      const keysData = await api.getApiKeys();
      // Response format: { api_keys: { openrouter: "sk-o...xxxx" or "", ... }, providers: [...] }
      const openRouterKey = keysData?.api_keys?.openrouter;
      const hasOpenRouter = openRouterKey && openRouterKey.length > 0;
      if (!hasOpenRouter) {
        // Delay the warning to not overwhelm on first load
        setTimeout(() => {
          toast.error(
            'No OpenRouter API key configured. Go to Settings → API Keys to add your key.',
            8000
          );
        }, 2000);
      }
    } catch (e) {
      // Silently fail - user might not be logged in yet
      console.log('Could not check API keys:', e.message);
    }
  };

  // Load conversations and budget alerts on mount - load immediately for fast UX
  useEffect(() => {
    // Load immediately without waiting for backend health check
    // This makes the app feel faster like ChatGPT
    loadConversations();
    loadBudgetAlerts();
    checkApiKeys();
  }, []);

  // Listen for custom events to open managers
  useEffect(() => {
    const handleOpenTeamManager = () => setShowTeamManager(true);
    const handleOpenAPIKeysManager = () => setShowAPIKeysManager(true);
    const handleOpenAnalytics = () => setShowAnalytics(true);

    window.addEventListener('openTeamManager', handleOpenTeamManager);
    window.addEventListener('openAPIKeysManager', handleOpenAPIKeysManager);
    window.addEventListener('openAnalytics', handleOpenAnalytics);

    return () => {
      window.removeEventListener('openTeamManager', handleOpenTeamManager);
      window.removeEventListener('openAPIKeysManager', handleOpenAPIKeysManager);
      window.removeEventListener('openAnalytics', handleOpenAnalytics);
    };
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Cmd/Ctrl + K = New conversation
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        handleNewConversation();
      }
      // Escape = Close sidebar on mobile
      if (e.key === 'Escape' && isSidebarOpen) {
        setIsSidebarOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isSidebarOpen]);

  // Removed annoying 30-second polling
  // Budget alerts now only checked on mount

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
      if (!currentConversationId && !autoCreateChatRef.current) {
        autoCreateChatRef.current = true;
        if (convs.length > 0 && convs[0].message_count === 0) {
          // Select existing empty conversation and load it immediately
          setCurrentConversationId(convs[0].id);
          setCurrentConversation({
            id: convs[0].id,
            created_at: convs[0].created_at,
            messages: [],
            project_id: convs[0].project_id,
          });
        } else {
          await handleNewConversation();
        }
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
      toast.error(getUserFriendlyMessage(error));
    }
  };

  // Filter conversations by project
  const filteredConversations = useMemo(() => {
    if (!currentProjectId) {
      // Show all conversations when "All Chats" is selected
      return conversations;
    }
    // Filter by project_id
    return conversations.filter((c) => c.project_id === currentProjectId);
  }, [conversations, currentProjectId]);

  // Handle project change from sidebar
  const handleProjectChange = (projectId) => {
    setCurrentProjectId(projectId);
    // Clear current conversation if it's not in the selected project
    if (projectId && currentConversation?.project_id !== projectId) {
      setCurrentConversationId(null);
      setCurrentConversation(null);
    }
  };

  // Handle project selection (opens ProjectView)
  const handleProjectSelect = async (project) => {
    if (!project || project.id === 'all') {
      setSelectedProject(null);
      setCurrentProjectId(null);
      return;
    }

    setSelectedProject(project);
    setCurrentProjectId(project.id);

    // Find existing conversations for this project
    const projectConversations = conversations.filter(c => c.project_id === project.id);

    if (projectConversations.length > 0) {
      // Select the first conversation
      const conv = projectConversations[0];
      setCurrentConversationId(conv.id);
      setCurrentConversation({
        id: conv.id,
        created_at: conv.created_at,
        messages: [],
        project_id: conv.project_id,
        title: conv.title,
      });
      // Load full conversation
      loadConversation(conv.id);
    } else {
      // Create a new conversation for this project
      try {
        const response = await api.createConversationInProject(project.id);
        // Backend returns { conversation: {...}, project_id: "..." }
        const newConv = response.conversation || response;
        const convProjectId = response.project_id || project.id;

        setConversations(prev => [
          { id: newConv.id, created_at: newConv.created_at, message_count: 0, project_id: convProjectId },
          ...prev,
        ]);
        setCurrentConversationId(newConv.id);
        setCurrentConversation({
          id: newConv.id,
          created_at: newConv.created_at,
          messages: [],
          project_id: convProjectId,
        });
      } catch (error) {
        console.error('Failed to create conversation for project:', error);
      }
    }
  };

  // Handle back from ProjectView
  const handleBackFromProject = () => {
    setSelectedProject(null);
    setCurrentProjectId(null);
    setCurrentConversationId(null);
    setCurrentConversation(null);
  };

  // Handle project update from ProjectView
  const handleProjectUpdate = (updatedProject) => {
    setSelectedProject(updatedProject);
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const loadBudgetAlerts = async () => {
    try {
      const alerts = await api.getBudgetAlerts();
      setBudgetAlerts(alerts);
      // Only show banner if budget is ACTUALLY EXCEEDED (not just warnings)
      if (alerts.exceeded) {
        setShowBudgetBanner(true);
        // Clear any existing timeout to prevent memory leaks
        if (budgetTimeoutRef.current) {
          clearTimeout(budgetTimeoutRef.current);
        }
        // Auto-dismiss after 10 seconds
        budgetTimeoutRef.current = setTimeout(() => setShowBudgetBanner(false), 10000);
      }
    } catch (error) {
      console.error('Failed to load budget alerts:', error);
    }
  };

  const handleNewConversation = async () => {
    if (isCreatingConversation) return; // Prevent double-clicks
    setIsCreatingConversation(true);
    try {
      let newConv;
      if (currentProjectId) {
        // Create conversation in the selected project
        const response = await api.createConversationInProject(currentProjectId);
        // Backend returns { conversation: {...}, project_id: "..." }
        newConv = response.conversation || response;
        newConv.project_id = response.project_id || currentProjectId;
      } else {
        // Create standalone conversation
        newConv = await api.createConversation();
      }
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0, project_id: newConv.project_id },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
      // Set currentConversation immediately so chat opens right away
      setCurrentConversation({
        id: newConv.id,
        created_at: newConv.created_at,
        messages: [],
        project_id: newConv.project_id,
      });
      // Close sidebar on mobile after creating conversation
      if (window.innerWidth <= 768) {
        setIsSidebarOpen(false);
      }
    } catch (error) {
      console.error('Failed to create conversation:', error);
      const errorMessage = getUserFriendlyMessage(error);
      // Show connection errors longer
      const duration = error instanceof NetworkError ? 10000 : 5000;
      toast.error(errorMessage, duration);
    } finally {
      setIsCreatingConversation(false);
    }
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
    // Set a minimal conversation object immediately so chat shows right away
    // The full conversation will be loaded by the useEffect
    const conv = conversations.find(c => c.id === id);
    if (conv) {
      setCurrentConversation({
        id: conv.id,
        created_at: conv.created_at,
        messages: currentConversation?.id === id ? currentConversation.messages : [],
        project_id: conv.project_id,
        title: conv.title,
      });
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
      // Remove from local state
      setConversations((prev) => prev.filter((c) => c.id !== id));
      // If we deleted the current conversation, clear the view
      if (currentConversationId === id) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  // Stop council request handler
  const handleStopCouncil = useCallback(async () => {
    // Abort client-side fetch
    if (councilAbortRef.current) {
      councilAbortRef.current.abort();
      councilAbortRef.current = null;
    }

    // Also signal backend to stop processing (saves tokens)
    if (currentConversationId) {
      try {
        await api.cancelStream(currentConversationId);
      } catch (e) {
        // Ignore cancel errors - the stream may have already finished
        console.debug('Cancel council stream request:', e.message);
      }
    }

    setIsLoading(false);
    // Remove the incomplete assistant message
    setCurrentConversation((prev) => {
      if (!prev?.messages?.length) return prev;
      const messages = [...prev.messages];
      const lastMsg = messages[messages.length - 1];
      // Only remove if it's an incomplete assistant message
      if (lastMsg?.role === 'assistant' && !lastMsg.stage3) {
        messages.pop();
      }
      return { ...prev, messages };
    });
  }, [currentConversationId]);

  const handleSendMessage = async (content, attachedFiles = [], features = null) => {
    console.log('📨 App.handleSendMessage received features:', features);
    if (!currentConversationId) return;

    // Store message count before adding optimistic updates for safe rollback
    const messageCountBeforeOptimistic = currentConversation?.messages?.length || 0;

    // Create abort controller for this request
    councilAbortRef.current = new AbortController();

    setIsLoading(true);
    // Reset council progress
    setCouncilProgress({
      stage: 0,
      models: [],
      modelProgress: {},
      chairmanModel: '',
      chairmanStatus: 'pending',
      contextStatus: null,
      searchType: null
    });
    try {
      // Optimistically add user message to UI
      const userMessage = {
        role: 'user',
        content,
        attached_files: attachedFiles
      };

      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...(prev?.messages || []), userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...(prev?.messages || []), assistantMessage],
      }));

      // Send message with streaming and abort signal
      await api.sendMessageStream(
        currentConversationId,
        content,
        (eventType, event) => {
          switch (eventType) {
            // Context gathering events (web search / deep search)
            case 'context_start':
              setCouncilProgress(prev => ({
                ...prev,
                stage: 0,
                contextStatus: 'loading',
                searchType: event.search_type
              }));
              break;

            case 'context_complete':
              setCouncilProgress(prev => ({
                ...prev,
                contextStatus: event.success ? 'completed' : 'failed',
                contextError: event.error || null
              }));
              break;

            // Model-level progress events for Stage 1
            case 'stage1_model_start':
              setCouncilProgress(prev => ({
                ...prev,
                stage: 1,
                models: prev.models.includes(event.model) ? prev.models : [...prev.models, event.model],
                modelProgress: { ...prev.modelProgress, [event.model]: 'loading' }
              }));
              break;

            case 'stage1_model_complete':
              setCouncilProgress(prev => ({
                ...prev,
                modelProgress: { ...prev.modelProgress, [event.model]: 'completed' }
              }));
              break;

            case 'stage1_model_error':
              setCouncilProgress(prev => ({
                ...prev,
                modelProgress: { ...prev.modelProgress, [event.model]: 'error' }
              }));
              break;

            case 'stage1_start':
              setCouncilProgress(prev => ({ ...prev, stage: 1 }));
              setCurrentConversation((prev) => {
                if (!prev?.messages?.length) return prev;
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                if (lastMsg?.loading) lastMsg.loading.stage1 = true;
                return { ...prev, messages };
              });
              break;

            case 'stage1_complete':
              setCurrentConversation((prev) => {
                if (!prev?.messages?.length) return prev;
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                if (lastMsg) {
                  lastMsg.stage1 = event.data;
                  if (lastMsg.loading) lastMsg.loading.stage1 = false;
                }
                return { ...prev, messages };
              });
              break;

            // Model-level progress events for Stage 2
            case 'stage2_model_start':
              setCouncilProgress(prev => ({
                ...prev,
                stage: 2,
                modelProgress: { ...prev.modelProgress, [event.model]: 'loading' }
              }));
              break;

            case 'stage2_model_complete':
              setCouncilProgress(prev => ({
                ...prev,
                modelProgress: { ...prev.modelProgress, [event.model]: 'completed' }
              }));
              break;

            case 'stage2_model_error':
              setCouncilProgress(prev => ({
                ...prev,
                modelProgress: { ...prev.modelProgress, [event.model]: 'error' }
              }));
              break;

            case 'stage2_start':
              // Reset model progress for stage 2 (same models, fresh status)
              setCouncilProgress(prev => ({
                ...prev,
                stage: 2,
                modelProgress: prev.models.reduce((acc, model) => ({ ...acc, [model]: 'pending' }), {})
              }));
              setCurrentConversation((prev) => {
                if (!prev?.messages?.length) return prev;
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                if (lastMsg?.loading) lastMsg.loading.stage2 = true;
                return { ...prev, messages };
              });
              break;

            case 'stage2_complete':
              setCurrentConversation((prev) => {
                if (!prev?.messages?.length) return prev;
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                if (lastMsg) {
                  lastMsg.stage2 = event.data;
                  lastMsg.metadata = event.metadata;
                  if (lastMsg.loading) lastMsg.loading.stage2 = false;
                }
                return { ...prev, messages };
              });
              break;

            case 'stage3_start':
              // Get chairman model from metadata if available
              setCouncilProgress(prev => ({
                ...prev,
                stage: 3,
                chairmanStatus: 'loading',
                chairmanModel: event.model || prev.chairmanModel
              }));
              setCurrentConversation((prev) => {
                if (!prev?.messages?.length) return prev;
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                if (lastMsg?.loading) lastMsg.loading.stage3 = true;
                return { ...prev, messages };
              });
              break;

            case 'stage3_complete':
              setCouncilProgress(prev => ({
                ...prev,
                chairmanStatus: 'completed',
                chairmanModel: event.data?.model || prev.chairmanModel
              }));
              setCurrentConversation((prev) => {
                if (!prev?.messages?.length) return prev;
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                if (lastMsg) {
                  lastMsg.stage3 = event.data;
                  if (lastMsg.loading) lastMsg.loading.stage3 = false;
                }
                return { ...prev, messages };
              });
              break;

            case 'title_complete':
              // Update current conversation title directly
              if (event.data?.title) {
                setCurrentConversation((prev) => {
                  if (!prev) return prev;
                  return { ...prev, title: event.data.title };
                });
                // Also update in conversations list
                setConversations((prev) =>
                  prev.map((conv) =>
                    conv.id === currentConversation?.id
                      ? { ...conv, title: event.data.title }
                      : conv
                  )
                );
              }
              // Also reload to ensure sync
              loadConversations();
              break;

            case 'complete':
              // Stream complete, reload conversations list
              loadConversations();
              setIsLoading(false);
              // Reset progress
              setCouncilProgress({
                stage: 0,
                models: [],
                modelProgress: {},
                chairmanModel: '',
                chairmanStatus: 'pending',
                contextStatus: null,
                searchType: null
              });
              break;

            case 'error':
              console.error('Stream error:', event.message);
              // Show toast notification for errors
              const errorMsg = event.message || 'An error occurred';
              if (errorMsg.includes('API key') || errorMsg.includes('api key')) {
                toast.error('API key missing or invalid. Go to Settings → API Keys to configure your keys.');
              } else if (errorMsg.includes('No OpenRouter')) {
                toast.error('OpenRouter API key required. Go to Settings → API Keys to add it.');
              } else {
                toast.error(errorMsg);
              }
              // Show error message in conversation
              setCurrentConversation((prev) => {
                if (!prev?.messages?.length) return prev;
                const messages = [...prev.messages];
                const lastMsg = messages[messages.length - 1];
                if (lastMsg) {
                  lastMsg.stage3 = {
                    model: 'error',
                    response: event.message || 'An error occurred. Please try again.'
                  };
                  if (lastMsg.loading) {
                    lastMsg.loading.stage1 = false;
                    lastMsg.loading.stage2 = false;
                    lastMsg.loading.stage3 = false;
                  }
                }
                return { ...prev, messages };
              });
              setIsLoading(false);
              setCouncilProgress({
                stage: 0,
                models: [],
                modelProgress: {},
                chairmanModel: '',
                chairmanStatus: 'pending',
                contextStatus: null,
                searchType: null
              });
              break;

            default:
              // Log unknown events for debugging but don't break
              if (!eventType.includes('chunk')) {
                console.log('Unknown event type:', eventType, event);
              }
          }
        },
        councilAbortRef.current?.signal,
        attachedFiles, // Pass files to API
        {},
        features
      );
    } catch (error) {
      // Don't log or rollback if it was intentionally aborted
      if (error.name === 'AbortError') {
        console.log('Council request cancelled by user');
        return;
      }
      console.error('Failed to send message:', error);
      // Show error message to user instead of just rolling back
      setCurrentConversation((prev) => {
        const messages = [...(prev?.messages || [])];
        // Keep user message but add error message
        if (messages.length > messageCountBeforeOptimistic) {
          const lastMsg = messages[messages.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.stage3 = {
              model: 'error',
              response: error.message || 'Failed to send message. Please check your API key in Settings → API Keys.'
            };
            if (lastMsg.loading) {
              lastMsg.loading.stage1 = false;
              lastMsg.loading.stage2 = false;
              lastMsg.loading.stage3 = false;
            }
          } else {
            // Add error message
            messages.push({
              role: 'assistant',
              stage3: {
                model: 'error',
                response: error.message || 'Failed to send message. Please check your API key in Settings → API Keys.'
              }
            });
          }
        }
        return { ...prev, messages };
      });
      setIsLoading(false);
      setCouncilProgress({
        stage: 0,
        models: [],
        modelProgress: {},
        chairmanModel: '',
        chairmanStatus: 'pending',
        contextStatus: null,
        searchType: null
      });
    } finally {
      councilAbortRef.current = null;
    }
  };

  // Get the most severe alert level
  const getHighestAlertLevel = () => {
    if (budgetAlerts.exceeded) return 'exceeded';
    if (budgetAlerts.alerts.length === 0) return 'none';

    const levels = budgetAlerts.alerts.map(a => a.level);
    if (levels.includes('exceeded')) return 'exceeded';
    if (levels.includes('critical')) return 'critical';
    if (levels.includes('warning')) return 'warning';
    if (levels.includes('info')) return 'info';
    return 'none';
  };

  // Get banner message
  const getBudgetBannerMessage = () => {
    if (budgetAlerts.exceeded) {
      const periods = budgetAlerts.exceeded_periods.join(', ');
      return `Budget exceeded for: ${periods}. Consider pausing queries or increasing limits.`;
    }

    if (budgetAlerts.alerts.length > 0) {
      const highestAlert = budgetAlerts.alerts.reduce((max, alert) => {
        const levels = { info: 1, warning: 2, critical: 3, exceeded: 4 };
        return (levels[alert.level] || 0) > (levels[max.level] || 0) ? alert : max;
      }, budgetAlerts.alerts[0]);

      return highestAlert.message;
    }

    return '';
  };

  const alertLevel = getHighestAlertLevel();
  // Only show banner when budget is actually exceeded (not for warnings/info)
  const shouldShowBanner = showBudgetBanner && budgetAlerts.exceeded;

  // If a project is selected, show the dedicated ProjectView
  if (selectedProject) {
    return (
      <div className="app">
        {shouldShowBanner && (
          <div className={`budget-banner ${alertLevel}`}>
            <div className="budget-banner-content">
              <span className="budget-banner-icon">
                {alertLevel === 'exceeded' ? '🚫' : alertLevel === 'critical' ? '⚠️' : '💰'}
              </span>
              <span className="budget-banner-message">{getBudgetBannerMessage()}</span>
            </div>
            <button
              className="budget-banner-close"
              onClick={() => setShowBudgetBanner(false)}
              aria-label="Dismiss budget alert"
            >
              ×
            </button>
          </div>
        )}
        <ProjectView
          project={selectedProject}
          conversations={filteredConversations}
          currentConversationId={currentConversationId}
          currentConversation={currentConversation}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onBack={handleBackFromProject}
          onDeleteConversation={handleDeleteConversation}
          onProjectUpdate={handleProjectUpdate}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          onStopCouncil={handleStopCouncil}
          onConversationUpdate={loadConversation}
          councilProgress={councilProgress}
        />

        {/* Manager Modals */}
        {showTeamManager && (
          <>
            <div className="modal-overlay" onClick={() => setShowTeamManager(false)} />
            <TeamManager onClose={() => setShowTeamManager(false)} />
          </>
        )}

        {showAPIKeysManager && (
          <>
            <div className="modal-overlay" onClick={() => setShowAPIKeysManager(false)} />
            <APIKeysManager onClose={() => setShowAPIKeysManager(false)} />
          </>
        )}

        {showAnalytics && (
          <>
            <div className="modal-overlay" onClick={() => setShowAnalytics(false)} />
            <AnalyticsDashboard onClose={() => setShowAnalytics(false)} />
          </>
        )}
      </div>
    );
  }

  return (
    <div className="app">
      {shouldShowBanner && (
        <div className={`budget-banner ${alertLevel}`}>
          <div className="budget-banner-content">
            <span className="budget-banner-icon">
              {alertLevel === 'exceeded' ? '🚫' : alertLevel === 'critical' ? '⚠️' : '💰'}
            </span>
            <span className="budget-banner-message">{getBudgetBannerMessage()}</span>
          </div>
          <button
            className="budget-banner-close"
            onClick={() => setShowBudgetBanner(false)}
            aria-label="Dismiss budget alert"
          >
            ×
          </button>
        </div>
      )}

      {/* Mobile hamburger menu button */}
      <button
        className="mobile-menu-button"
        onClick={toggleSidebar}
        aria-label={isSidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          {isSidebarOpen ? (
            <>
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </>
          ) : (
            <>
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </>
          )}
        </svg>
      </button>

      <ErrorBoundary>
        <ClaudeSidebar
          conversations={conversations}
          currentConversationId={currentConversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          isMobileOpen={isSidebarOpen}
          onToggleMobile={toggleSidebar}
          isCreatingConversation={isCreatingConversation}
          onProjectChange={handleProjectChange}
          onProjectSelect={handleProjectSelect}
          onMoveToProject={async (conversationId, projectId) => {
            try {
              await api.moveConversationToProject(conversationId, projectId);
              // Update local state
              setConversations((prev) =>
                prev.map((c) =>
                  c.id === conversationId ? { ...c, project_id: projectId } : c
                )
              );
              if (currentConversation?.id === conversationId) {
                setCurrentConversation((prev) => ({ ...prev, project_id: projectId }));
              }
              toast.success(projectId ? 'Moved to project' : 'Removed from project');
          } catch (error) {
            toast.error(error.message || 'Failed to move conversation');
            }
          }}
        />
      </ErrorBoundary>

      {/* Main content area wrapper for mobile-first layout */}
      <main className="app-main">
        <ErrorBoundary>
          <ChatInterface
            conversation={currentConversation}
            currentConversationId={currentConversationId}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            onStopCouncil={handleStopCouncil}
            onToggleSidebar={toggleSidebar}
            onConversationUpdate={loadConversation}
            councilProgress={councilProgress}
            currentProjectId={currentProjectId}
            onMoveToProject={async (conversationId, projectId) => {
              try {
                await api.moveConversationToProject(conversationId, projectId);
                // Update local state
                setConversations((prev) =>
                  prev.map((c) =>
                    c.id === conversationId ? { ...c, project_id: projectId } : c
                  )
                );
                if (currentConversation?.id === conversationId) {
                  setCurrentConversation((prev) => ({ ...prev, project_id: projectId }));
                }
                toast.success(projectId ? 'Moved to project' : 'Removed from project');
          } catch (error) {
            toast.error(error.message || 'Failed to move conversation');
              }
            }}
          />
        </ErrorBoundary>
      </main>

      {/* Manager Modals */}
      {showTeamManager && (
        <>
          <div className="modal-overlay" onClick={() => setShowTeamManager(false)} />
          <TeamManager onClose={() => setShowTeamManager(false)} />
        </>
      )}

      {showAPIKeysManager && (
        <>
          <div className="modal-overlay" onClick={() => setShowAPIKeysManager(false)} />
          <APIKeysManager onClose={() => setShowAPIKeysManager(false)} />
        </>
      )}

      {showAnalytics && (
        <>
          <div className="modal-overlay" onClick={() => setShowAnalytics(false)} />
          <AnalyticsDashboard onClose={() => setShowAnalytics(false)} />
        </>
      )}
    </div>
  );
}

// Root App with routing
function App() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Login />}
      />
      <Route
        path="/register"
        element={isAuthenticated ? <Navigate to="/" replace /> : <Register />}
      />
      <Route
        path="/share/:token"
        element={<SharedConversation />}
      />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <MainApp />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
