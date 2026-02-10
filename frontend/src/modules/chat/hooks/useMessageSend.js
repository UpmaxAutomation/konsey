import { useState, useRef } from 'react';
import { api } from '../../../api';

// Threshold for showing cost estimate (characters)
const COST_ESTIMATE_THRESHOLD = 500;

/**
 * Hook for core message sending logic: submit, stop, keyboard, paste, cost estimate.
 *
 * @param {Object} params
 * @param {Object} params.conversation - Current conversation object
 * @param {string|null} params.activeConversationId - Active conversation ID
 * @param {string} params.mode - Current mode ('quick', 'council', 'compare', 'auto')
 * @param {string} params.selectedModel - Currently selected model ID
 * @param {boolean} params.autoMode - Whether auto-mode (legacy) is enabled
 * @param {Array} params.councilModels - List of council model IDs
 * @param {Object} params.features - Feature toggles
 * @param {Array} params.attachedFiles - Currently attached files
 * @param {Function} params.setAttachedFiles - Setter for attached files
 * @param {Function} params.onSendMessage - Callback to send a council message
 * @param {Function} params.onConversationUpdate - Callback to refresh a conversation
 * @param {Object} params.toast - Toast notification instance
 * @param {Array} params.compareModels - Models selected for comparison
 * @param {Function} params.handleCompareSubmit - Compare mode submit handler
 * @param {boolean} params.isLoading - Whether a council request is loading
 * @param {boolean} params.isComparing - Whether compare mode is active
 * @returns {Object} Message send state and handlers
 */
export function useMessageSend({
  conversation,
  activeConversationId,
  mode,
  selectedModel,
  autoMode,
  councilModels,
  features,
  attachedFiles,
  setAttachedFiles,
  onSendMessage,
  onConversationUpdate,
  toast,
  compareModels,
  handleCompareSubmit,
  isLoading,
  isComparing,
}) {
  const [input, setInput] = useState('');
  const [streamingText, setStreamingText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingUserMessage, setPendingUserMessage] = useState(null);
  const [routeInfo, setRouteInfo] = useState(null);
  const [pastedImages, setPastedImages] = useState([]);
  const [showCostEstimate, setShowCostEstimate] = useState(false);
  const [pendingMessage, setPendingMessage] = useState(null);
  const abortControllerRef = useRef(null);

  // Stop/cancel ongoing request
  const handleStop = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    if (conversation?.id) {
      try {
        await api.cancelStream(conversation.id);
      } catch (e) {
        console.debug('Cancel stream request:', e.message);
      }
    }

    setIsStreaming(false);
    setStreamingText('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const hasText = input.trim();
    const hasImages = pastedImages.length > 0;
    const hasFiles = attachedFiles.length > 0;

    const isBlocked =
      (!hasText && !hasImages && !hasFiles) ||
      isLoading ||
      isStreaming ||
      isComparing ||
      !conversation;
    if (isBlocked) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H_auto_1',location:'ChatInterface.jsx:handleSubmit',message:'submit_blocked',data:{mode,hasText,hasImages,hasFiles,isLoading,isStreaming,isComparing,hasConversation:!!conversation},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      return;
    }

    const message = input.trim();
    const images = [...pastedImages];
    const files = attachedFiles.map(f => f.filename);

    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H_auto_2',location:'ChatInterface.jsx:handleSubmit',message:'submit_allowed',data:{mode,activeConversationId,conversationId:conversation?.id||null,conversationTitle:conversation?.title||null,conversationMessagesLen:Array.isArray(conversation?.messages)?conversation.messages.length:null,messagePreview:String(message).slice(0,120)},timestamp:Date.now()})}).catch(()=>{});
    // #endregion

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
    setPastedImages([]);
    setAttachedFiles([]);

    if (mode === 'council') {
      let allFiles = [...files];

      if (hasImages) {
        for (const img of images) {
          try {
            const result = await api.uploadFile(activeConversationId, img.file);
            if (result?.filename) {
              allFiles.push(result.filename);
            }
          } catch (err) {
            console.error('Failed to upload pasted image:', err);
            toast.error(`Failed to upload image: ${img.name}`);
          }
        }
      }

      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H_council_1',location:'ChatInterface.jsx:handleSubmit',message:'council_submit',data:{conversationId:conversation?.id||null,councilModelsCount:councilModels.length,councilModels:councilModels.slice(0,8),selectedModel,featuresKeys:features?Object.keys(features):null,filesCount:allFiles.length},timestamp:Date.now()})}).catch(()=>{});
      // #endregion

      onSendMessage(message, allFiles, features);
    } else if (mode === 'compare') {
      handleCompareSubmit(message);
    } else if (mode === 'auto') {
      setStreamingText('');
      setRouteInfo(null);

      setPendingUserMessage({
        role: 'user',
        content: message,
        attached_files: files
      });

      abortControllerRef.current = new AbortController();
      let streamCompleted = false;

      let modelToUse = selectedModel || 'anthropic/claude-sonnet-4';
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H_auto_3',location:'ChatInterface.jsx:auto',message:'auto_route_start',data:{conversationId:conversation?.id||null,modelToUseFallback:modelToUse,messageLength:message.length,filesCount:files.length,hasImages:images.length>0},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      try {
        const routeResult = await api.routeQuery({
          query: message,
          num_recommendations: 1,
          preference: features.auto_preference || 'quality',
        });
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
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H_auto_3',location:'ChatInterface.jsx:auto',message:'auto_route_success',data:{selectedModel:modelToUse,queryType:routeResult.query_type,confidence:routeResult.primary_confidence},timestamp:Date.now()})}).catch(()=>{});
          // #endregion
        }
      } catch (e) {
        console.error('Auto-routing failed, using fallback model:', e);
        toast.warning('Auto-routing unavailable, using default model');
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H_auto_3',location:'ChatInterface.jsx:auto',message:'auto_route_error',data:{errorName:e?.name||null,errorMessage:String(e?.message||e).slice(0,200),fallbackModel:modelToUse},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
      }

      try {
        setIsStreaming(true);
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H_auto_4',location:'ChatInterface.jsx:auto',message:'auto_stream_start',data:{conversationId:conversation?.id||null,modelToUse,filesCount:files.length,featuresKeys:features?Object.keys(features):null},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
        await api.sendQuickMessageStream(
          conversation.id,
          message,
          modelToUse,
          (eventType, event) => {
            if (eventType === 'chunk') {
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H_auto_21',location:'ChatInterface.jsx:auto',message:'auto_chunk_received',data:{eventKeys:event&&typeof event==='object'?Object.keys(event).slice(0,12):null,hasText:typeof event?.text==='string',hasData:typeof event?.data==='string'},timestamp:Date.now()})}).catch(()=>{});
              // #endregion
              const chunkText = typeof event?.text === 'string' ? event.text : event?.data;
              setStreamingText((prev) => prev + (chunkText || ''));
            } else if (eventType === 'complete') {
              streamCompleted = true;
              setIsStreaming(false);
              setPendingUserMessage(null);
              if (onConversationUpdate) {
                onConversationUpdate(conversation.id);
              }
            } else if (eventType === 'error') {
              setIsStreaming(false);
              setPendingUserMessage(null);
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
          setStreamingText('');
        } else {
          console.error('Auto mode error:', error);
        }
        setIsStreaming(false);
        setPendingUserMessage(null);
      } finally {
        abortControllerRef.current = null;
        if (streamCompleted && onConversationUpdate) {
          onConversationUpdate(conversation.id);
        }
      }
    } else {
      // Quick mode
      setStreamingText('');
      setRouteInfo(null);

      setPendingUserMessage({
        role: 'user',
        content: message,
        attached_files: files
      });

      // Upload pasted images first
      let allFiles = [...files];
      if (hasImages) {
        for (const img of images) {
          try {
            const result = await api.uploadFile(activeConversationId, img.file);
            if (result?.filename) {
              allFiles.push(result.filename);
            }
          } catch (err) {
            console.error('Failed to upload pasted image:', err);
            toast.error(`Failed to upload image: ${img.name}`);
          }
        }
      }

      abortControllerRef.current = new AbortController();
      let streamCompleted = false;
      let debugFirstEventLogged = false;

      let modelToUse = selectedModel;
      if (autoMode) {
        try {
          const routeResult = await api.routeQuery({
            query: message,
            num_recommendations: 1,
            preference: features.auto_preference || 'quality',
          });
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
            if (!debugFirstEventLogged) {
              debugFirstEventLogged = true;
              const eventDataPreview =
                typeof event?.data === 'string'
                  ? event.data.slice(0, 200)
                  : typeof event?.data?.content === 'string'
                    ? event.data.content.slice(0, 200)
                    : null;
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H2',location:'ChatInterface.jsx:quick_stream',message:'first_stream_event',data:{type,conversationId:conversation?.id||null,eventKeys:event&&typeof event==='object'?Object.keys(event).slice(0,20):null,eventDataPreview},timestamp:Date.now()})}).catch(()=>{});
              // #endregion
            }
            if (type === 'chunk') {
              setStreamingText(prev => prev + event.data);
            } else if (type === 'complete' || type === 'title_complete') {
              streamCompleted = true;
              setStreamingText('');
              setPendingUserMessage(null);
              onConversationUpdate?.(conversation.id);
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H4',location:'ChatInterface.jsx:quick_stream',message:'stream_terminal_event',data:{type,conversationId:conversation?.id||null,streamCompleted:true},timestamp:Date.now()})}).catch(()=>{});
              // #endregion
            } else if (type === 'error') {
              streamCompleted = true;
              setStreamingText('');
              setPendingUserMessage(null);
              const errorMsg = event.message || 'An error occurred';
              console.error('Quick message error:', errorMsg);
              toast.error(errorMsg);
              // #region agent log
              fetch('http://127.0.0.1:7242/ingest/75f3ab5e-6780-409e-bc6a-473b28bdd0d8',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sessionId:'debug-session',runId:'run1',hypothesisId:'H4',location:'ChatInterface.jsx:quick_stream',message:'stream_terminal_event',data:{type,conversationId:conversation?.id||null,streamCompleted:true,errorPreview:String(errorMsg).slice(0,200)},timestamp:Date.now()})}).catch(()=>{});
              // #endregion
            }
          },
          abortControllerRef.current.signal,
          allFiles,
          {},
          features
        );
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Request failed:', err);
          const errorMsg = err.message || 'Request failed';
          toast.error(errorMsg);
        }
        setStreamingText('');
        setPendingUserMessage(null);
      } finally {
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

  // Handle cost estimate confirmation
  const handleCostEstimateConfirm = () => {
    if (pendingMessage) {
      setInput('');
      setPastedImages([]);
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

  return {
    input,
    setInput,
    streamingText,
    setStreamingText,
    isStreaming,
    setIsStreaming,
    pendingUserMessage,
    routeInfo,
    pastedImages,
    handleSubmit,
    handleStop,
    handleKeyDown,
    handlePaste,
    removePastedImage,
    showCostEstimate,
    pendingMessage,
    handleCostEstimateConfirm,
    handleCostEstimateCancel,
    abortControllerRef,
  };
}

export default useMessageSend;
