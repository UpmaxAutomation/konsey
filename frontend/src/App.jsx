import { useState, useEffect, useRef, useCallback } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
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
  const [isLoading, setIsLoading] = useState(false);
  const [isCreatingConversation, setIsCreatingConversation] = useState(false);
  const [budgetAlerts, setBudgetAlerts] = useState({ alerts: [], exceeded: false, exceeded_periods: [] });
  const [showBudgetBanner, setShowBudgetBanner] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showTeamManager, setShowTeamManager] = useState(false);
  const [showAPIKeysManager, setShowAPIKeysManager] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const toast = useToast();
  // Council progress tracking
  const [councilProgress, setCouncilProgress] = useState({
    stage: 0,
    models: [],
    modelProgress: {},
    chairmanModel: '',
    chairmanStatus: 'pending'
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

  // Load conversations and budget alerts on mount
  useEffect(() => {
    // Check backend connection first
    const checkBackend = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout
        
        // Check root endpoint (not /api/) - backend root is at /
        const baseUrl = API_BASE.replace('/api', '');
        const response = await fetch(`${baseUrl}/`, { 
          method: 'GET',
          signal: controller.signal
        });
        
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H5',location:'App.jsx:63',message:'checkBackend:response',data:{url:`${API_BASE}/`,status:response.status,ok:response.ok},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        if (response.ok) {
          // Backend is available, load data
          loadConversations();
          loadBudgetAlerts();
        } else {
          console.warn('Backend responded with error:', response.status);
          toast.error('Backend server error. Please check if the server is running correctly.');
        }
      } catch (error) {
        console.error('Backend connection check failed:', error);
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H5',location:'App.jsx:71',message:'checkBackend:error',data:{url:`${API_BASE}/`,name:error?.name || 'unknown',message:error?.message || 'unknown'},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        // Don't show error toast here - let individual API calls handle it
        // Just try to load anyway in case it's a temporary issue
        loadConversations();
        loadBudgetAlerts();
      }
    };
    
    checkBackend();
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
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
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
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H1',location:'App.jsx:166',message:'handleNewConversation:start',data:{hasCurrentConversation:Boolean(currentConversationId),isCreatingConversation},timestamp:Date.now()})}).catch(()=>{});
    // #endregion
    setIsCreatingConversation(true);
    try {
      const newConv = await api.createConversation();
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
      // Close sidebar on mobile after creating conversation
      if (window.innerWidth <= 768) {
        setIsSidebarOpen(false);
      }
      toast.success('New chat created');
    } catch (error) {
      console.error('Failed to create conversation:', error);
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H1',location:'App.jsx:182',message:'handleNewConversation:error',data:{name:error?.name || 'unknown',message:error?.message || 'unknown'},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
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

  const handleSendMessage = async (content, attachedFiles = []) => {
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
      chairmanStatus: 'pending'
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
              // Reload conversations to get updated title
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
                chairmanStatus: 'pending'
              });
              break;

            case 'error':
              console.error('Stream error:', event.message);
              setIsLoading(false);
              setCouncilProgress({
                stage: 0,
                models: [],
                modelProgress: {},
                chairmanModel: '',
                chairmanStatus: 'pending'
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
        attachedFiles // Pass files to API
      );
    } catch (error) {
      // Don't log or rollback if it was intentionally aborted
      if (error.name === 'AbortError') {
        console.log('Council request cancelled by user');
        return;
      }
      console.error('Failed to send message:', error);
      // Rollback to state before optimistic updates using stored count
      setCurrentConversation((prev) => ({
        ...prev,
        messages: (prev?.messages || []).slice(0, messageCountBeforeOptimistic),
      }));
      setIsLoading(false);
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

      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onConversationsChange={loadConversations}
        isMobileOpen={isSidebarOpen}
        onToggleMobile={toggleSidebar}
        isCreatingConversation={isCreatingConversation}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        onStopCouncil={handleStopCouncil}
        onToggleSidebar={toggleSidebar}
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
