import { useState, useEffect, useRef, useCallback } from 'react';
import SafeMarkdown from '../../../shared/components/SafeMarkdown';
import '../styles/ChatInterface.css';
import '../styles/ClaudeChat.css';
import { api } from '../../../api';
import { useToast } from '../../../shared/components/Toast';
import Stage1 from './Stage1';
import Stage2 from './Stage2';
import BoardPicker from '../../canvas/components/BoardPicker';
import FileUpload from './FileUpload';
import ProgressIndicator from './ProgressIndicator';
import CostEstimate from './CostEstimate';

// Hooks
import { useModelSelection } from '../hooks/useModelSelection';
import { useFeatures } from '../hooks/useFeatures';
import { useFileAttach } from '../hooks/useFileAttach';
import { useVoiceInput } from '../hooks/useVoiceInput';
import { useCompareMode } from '../hooks/useCompareMode';
import { useMessageActions } from '../hooks/useMessageActions.jsx';
import { useMessageSend } from '../hooks/useMessageSend';

export default function ChatInterface({
  conversation,
  currentConversationId,
  onSendMessage,
  isLoading,
  onStopCouncil,
  onConversationUpdate,
  councilProgress = { stage: 0, models: [], modelProgress: {}, chairmanModel: '', chairmanStatus: 'pending', contextStatus: null, searchType: null },
  currentProjectId,
  onMoveToProject,
}) {
  const activeConversationId = conversation?.id || currentConversationId || null;
  const toast = useToast();

  // --- Local UI state ---
  const [mode, setMode] = useState('quick');
  const [showScrollFab, setShowScrollFab] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [projectInfo, setProjectInfo] = useState(null);
  const [selectedText, setSelectedText] = useState('');
  const [selectionRect, setSelectionRect] = useState(null);
  const [showSelectionBoardPicker, setShowSelectionBoardPicker] = useState(false);

  const messagesEndRef = useRef(null);
  const messagesContainerRef = useRef(null);
  const textareaRef = useRef(null);
  // Stable ref for setInput so useVoiceInput can call it before useMessageSend is composed
  const setInputRef = useRef(null);

  // --- Compose hooks ---
  const modelSelection = useModelSelection({ toast });
  const {
    selectedModel, setSelectedModel, models, councilModels,
    autoMode, setAutoMode, hasPerplexityKey,
    showModelPicker, setShowModelPicker,
    modelSearch, setModelSearch,
    filteredModels, groupedModels, councilCostEstimate,
    favoriteModels, recentModels, collapsedGroups,
    toggleFavorite, selectModel, toggleProviderGroup, getModelName,
  } = modelSelection;

  const { features, setFeatures, toggleFeature, setAutoPreference, setSearchMode, cycleSearchMode } =
    useFeatures({ hasPerplexityKey });

  const fileAttach = useFileAttach({ activeConversationId, toast });
  const {
    showFileUpload, setShowFileUpload,
    attachedFiles, setAttachedFiles,
    isDraggingOver, uploadingFiles,
    loadAttachedFiles, removeAttachedFile,
    handleDragEnter, handleDragLeave, handleDragOver, handleDrop,
  } = fileAttach;

  const { isListening, speechSupported, interimTranscript, toggleListening } =
    useVoiceInput({ setInput: (fn) => setInputRef.current?.(fn), toast, textareaRef });

  const compareMode = useCompareMode({ conversation, attachedFiles, features, toast });
  const {
    compareModels, setCompareModels,
    compareResponses, isComparing,
    compareVote, setCompareVote, compareQuery,
    showCompareModelPicker, setShowCompareModelPicker,
    handleCompareSubmit, handleStopCompare,
  } = compareMode;

  const messageSend = useMessageSend({
    conversation, activeConversationId, mode,
    selectedModel, autoMode, councilModels, features,
    attachedFiles, setAttachedFiles,
    onSendMessage, onConversationUpdate, toast,
    compareModels, handleCompareSubmit,
    isLoading, isComparing,
  });
  const {
    input, setInput, streamingText, setStreamingText,
    isStreaming, setIsStreaming, pendingUserMessage, routeInfo,
    pastedImages, handleSubmit, handleStop, handleKeyDown,
    handlePaste, removePastedImage,
    showCostEstimate, pendingMessage,
    handleCostEstimateConfirm, handleCostEstimateCancel,
    abortControllerRef,
  } = messageSend;

  // Wire the stable ref so useVoiceInput's closure can reach the real setInput
  setInputRef.current = setInput;

  const messageActions = useMessageActions({
    conversation, mode, selectedModel,
    isLoading, isStreaming, attachedFiles, features,
    onSendMessage, onConversationUpdate, toast,
    setStreamingText, setIsStreaming, abortControllerRef, setInput,
  });
  const {
    copiedCode, copiedMessageIndex,
    editingMessageIndex, editingText, regeneratingIndex,
    expandedCouncil, setExpandedCouncil,
    boardPickerIndex, setBoardPickerIndex,
    showShortcuts, setShowShortcuts,
    copyCode, copyMessage, copyConversation,
    handleAddTurnToBoard, regenerateMessage,
    startEditMessage, saveEditMessage, cancelEditMessage,
    handleForkConversation, exportConversation, formatMessageTime,
    CodeBlock,
  } = messageActions;

  // --- Local effects ---

  // Load project info when project context is active
  useEffect(() => {
    if (!currentProjectId) {
      setProjectInfo(null);
      return;
    }
    const loadProjectInfo = async () => {
      try {
        const project = await api.getProject(currentProjectId);
        setProjectInfo(project);
      } catch (err) {
        console.error('Failed to load project:', err);
        setProjectInfo(null);
      }
    };
    loadProjectInfo();
  }, [currentProjectId]);

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
  }, [conversation, streamingText, pendingUserMessage]);

  // Handle scroll to show/hide FAB
  const handleScroll = useCallback((e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.target;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setShowScrollFab(!isNearBottom && scrollHeight > clientHeight + 200);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleMessageMouseUp = useCallback(() => {
    const sel = window.getSelection();
    if (sel && sel.toString().trim().length > 5) {
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      setSelectedText(sel.toString().trim());
      setSelectionRect({ top: rect.top - 40, left: rect.left + rect.width / 2 });
    } else {
      setSelectedText('');
      setSelectionRect(null);
      setShowSelectionBoardPicker(false);
    }
  }, []);

  const handleChatAreaClick = (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;
    const isInteractive = target.closest(
      'button, a, input, textarea, select, label, [role="button"], .model-picker, .options-panel, .claude-input-container, .uploaded-files-preview, .pasted-images-preview'
    );
    if (isInteractive) return;
    textareaRef.current?.focus();
  };

  // --- Render ---

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
          <h1 className="claude-welcome-title">AI Konsey</h1>
          <p className="claude-welcome-subtitle">Multi-model AI deliberation system. Select or create a conversation to get started.</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`claude-chat ${isDraggingOver ? 'drag-over' : ''}`}
      onClick={handleChatAreaClick}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drop overlay */}
      {isDraggingOver && (
        <div className="drop-overlay">
          <div className="drop-overlay-content">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span>Drop files to attach</span>
            <span className="drop-hint">Images, code, PDFs, documents (max 25MB)</span>
          </div>
        </div>
      )}

      {/* Upload progress overlay */}
      {uploadingFiles && (
        <div className="upload-progress-overlay">
          <div className="upload-progress-content">
            <div className="spinner"></div>
            <span>Uploading files...</span>
          </div>
        </div>
      )}

      {/* Project context badge */}
      {projectInfo && (
        <div className="project-context-badge">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          </svg>
          <span className="project-context-name">{projectInfo.name}</span>
          {projectInfo.system_prompt && (
            <span className="project-context-indicator" title="Has custom instructions">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="12" cy="12" r="4" />
              </svg>
            </span>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="claude-messages" ref={messagesContainerRef} onScroll={handleScroll}>
        <div className="claude-messages-inner">
        {(!conversation.messages || conversation.messages.length === 0) ? (
          <div className="claude-welcome claude-welcome-minimal">
            <div className="claude-welcome-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                {mode === 'council' ? (
                  <><circle cx="9" cy="7" r="4" /><circle cx="17" cy="11" r="4" /><path d="M3 21v-2a4 4 0 0 1 4-4h4" /><path d="M21 21v-2a4 4 0 0 0-3-3.85" /></>
                ) : mode === 'compare' ? (
                  <><path d="M12 3v18M3 12h18" /><path d="M3 6l3 3-3 3" /><path d="M21 6l-3 3 3 3" /></>
                ) : (
                  <><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></>
                )}
              </svg>
            </div>
            <h1 className="claude-welcome-title">
              {mode === 'council'
                ? 'What would you like the council to discuss?'
                : mode === 'compare'
                  ? 'What would you like to compare?'
                  : 'How can I help you today?'}
            </h1>
            <p className="claude-welcome-hint">
              {mode === 'council'
                ? 'Multiple AI models will deliberate on your question'
                : mode === 'compare'
                  ? 'Get side-by-side responses from different models'
                  : `Using ${getModelName(selectedModel)}`
              }
            </p>
          </div>
        ) : (
          (conversation.messages || []).map((msg, i) => {
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
                    <span className="role-name">
                      {msg.role === 'user' ? 'You' : isCouncilResponse ? 'Council' : 'Assistant'}
                    </span>
                    {isCouncilResponse && (
                      <span className="claude-model-badge">Multi-model</span>
                    )}
                    {msg.timestamp && (
                      <span className="message-timestamp" title={new Date(msg.timestamp).toLocaleString()}>
                        {formatMessageTime(msg.timestamp)}
                      </span>
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
                  <div className="claude-message-text" onMouseUp={handleMessageMouseUp}>
                    <SafeMarkdown components={{ code: CodeBlock }}>
                      {content}
                    </SafeMarkdown>
                  </div>

                  {/* Per-message attachments */}
                  {msg.attached_files && msg.attached_files.length > 0 && (
                    <div className="message-attachments">
                      {msg.attached_files.map((filename, fileIdx) => {
                        const isImage = /\.(png|jpg|jpeg|gif|webp)$/i.test(filename);
                        const isCode = /\.(py|js|jsx|ts|tsx|json|html|css|go|rs|java|c|cpp|h|sh|sql|yaml|yml|md)$/i.test(filename);
                        return (
                          <div key={fileIdx} className={`message-attachment ${isImage ? 'image' : ''}`}>
                            {isImage ? (
                              <img
                                src={`/api/conversations/${conversation.id}/files/${filename}`}
                                alt={filename}
                                loading="lazy"
                                onClick={() => window.open(`/api/conversations/${conversation.id}/files/${filename}`, '_blank')}
                              />
                            ) : (
                              <a
                                href={`/api/conversations/${conversation.id}/files/${filename}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="attachment-link"
                              >
                                <span className="attachment-icon">{isCode ? '📄' : '📎'}</span>
                                <span className="attachment-name">{filename}</span>
                              </a>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

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

                    {msg.role === 'user' && (
                      <button
                        className="message-action-btn"
                        onClick={() => startEditMessage(i)}
                        title="Edit and resend"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                        Edit
                      </button>
                    )}

                    {msg.role === 'assistant' && (
                      <button
                        className={`message-action-btn ${regeneratingIndex === i ? 'loading' : ''}`}
                        onClick={() => regenerateMessage(i)}
                        disabled={isLoading || isStreaming || regeneratingIndex !== null}
                        title="Regenerate response"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={regeneratingIndex === i ? 'spinning' : ''}>
                          <path d="M23 4v6h-6" />
                          <path d="M1 20v-6h6" />
                          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                        </svg>
                        {regeneratingIndex === i ? 'Regenerating...' : 'Regenerate'}
                      </button>
                    )}

                    {isCouncilResponse && msg.role === 'assistant' && (
                      <div className="pin-to-board-wrapper">
                        <button
                          className="message-action-btn"
                          onClick={() => setBoardPickerIndex(boardPickerIndex === i ? null : i)}
                          title="Add full council turn to board"
                        >
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="3" y="3" width="18" height="18" rx="2" />
                            <path d="M3 9h18M9 21V9" />
                          </svg>
                          Board
                        </button>
                        {boardPickerIndex === i && (
                          <BoardPicker
                            onSelect={(boardId) => handleAddTurnToBoard(boardId, msg)}
                            onClose={() => setBoardPickerIndex(null)}
                          />
                        )}
                      </div>
                    )}
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

        {/* Pending user message */}
        {pendingUserMessage && (
          <div className="claude-message user">
            <div className="claude-message-content">
              <div className="claude-message-role">You</div>
              <div className="claude-message-text">
                <SafeMarkdown components={{ code: CodeBlock }}>
                  {pendingUserMessage.content}
                </SafeMarkdown>
              </div>
              {pendingUserMessage.attached_files?.length > 0 && (
                <div className="message-attachments">
                  {pendingUserMessage.attached_files.map((filename, idx) => (
                    <span key={idx} className="attachment-chip">📎 {filename}</span>
                  ))}
                </div>
              )}
            </div>
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

        {/* Loading indicator */}
        {(isLoading || (isStreaming && !streamingText)) && (
          mode === 'council' && (councilProgress.stage > 0 || councilProgress.contextStatus === 'loading') ? (
            <ProgressIndicator
              stage={councilProgress.stage}
              models={councilProgress.models}
              modelProgress={councilProgress.modelProgress}
              chairmanModel={councilProgress.chairmanModel}
              chairmanStatus={councilProgress.chairmanStatus}
              contextStatus={councilProgress.contextStatus}
              searchType={councilProgress.searchType}
              fastMode={features.fast_mode}
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

      {/* Text selection → Card action (drag handle + button) */}
      {selectedText && selectionRect && (
        <div
          className="chat-selection-action"
          style={{ position: 'fixed', top: selectionRect.top, left: selectionRect.left, transform: 'translateX(-50%)' }}
        >
          <span
            className="chat-selection-action__drag-handle"
            draggable
            onDragStart={(e) => {
              const payload = JSON.stringify({ text: selectedText, title: selectedText.slice(0, 60) });
              e.dataTransfer.setData('application/x-council-card', payload);
              e.dataTransfer.setData('text/plain', selectedText);
              e.dataTransfer.effectAllowed = 'copy';
            }}
            onDragEnd={() => {
              setSelectedText('');
              setSelectionRect(null);
              window.getSelection()?.removeAllRanges();
            }}
            title="Drag to canvas to create card"
          >
            ⠿
          </span>
          <button
            className="chat-selection-action__btn"
            onClick={() => setShowSelectionBoardPicker(true)}
          >
            + Card
          </button>
          {showSelectionBoardPicker && (
            <BoardPicker
              onSelect={async (boardId) => {
                try {
                  const { createCard } = await import('../../../api/boards');
                  await createCard(boardId, {
                    card_type: 'note',
                    title: selectedText.slice(0, 60),
                    content: selectedText,
                  });
                  toast?.success('Card created from selection');
                } catch (err) {
                  console.error('Failed to create card:', err);
                }
                setSelectedText('');
                setSelectionRect(null);
                setShowSelectionBoardPicker(false);
                window.getSelection()?.removeAllRanges();
              }}
              onClose={() => setShowSelectionBoardPicker(false)}
            />
          )}
        </div>
      )}

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
        <div className={`claude-input-container ${isListening ? 'listening' : ''}`}>
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
            {mode === 'auto' && (
              <div className="auto-preference-group" role="group" aria-label="Auto preference">
                <button
                  type="button"
                  className={`auto-preference-btn ${features.auto_preference === 'quality' ? 'active' : ''}`}
                  onClick={() => setAutoPreference('quality')}
                  title="Prefer the best quality models"
                >
                  Quality
                </button>
                <button
                  type="button"
                  className={`auto-preference-btn ${features.auto_preference === 'speed' ? 'active' : ''}`}
                  onClick={() => setAutoPreference('speed')}
                  title="Prefer faster responses"
                >
                  Speed
                </button>
                <button
                  type="button"
                  className={`auto-preference-btn ${features.auto_preference === 'cost' ? 'active' : ''}`}
                  onClick={() => setAutoPreference('cost')}
                  title="Prefer lower-cost models"
                >
                  Cost
                </button>
              </div>
            )}

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
                                .slice(0, 3)
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
            {/* Attached Files */}
            {attachedFiles.length > 0 && (
              <div className="uploaded-files-preview">
                <div className="uploaded-files-header">
                  <span className="uploaded-files-count">{attachedFiles.length} file{attachedFiles.length !== 1 ? 's' : ''} attached</span>
                  <button
                    type="button"
                    className="clear-all-files"
                    onClick={() => setAttachedFiles([])}
                    title="Remove all"
                  >
                    Clear all
                  </button>
                </div>
                <div className="uploaded-files-list">
                  {attachedFiles.map((file) => {
                    const filename = file.name || file.filename;
                    const ext = filename.split('.').pop()?.toLowerCase();
                    const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext);
                    const isCode = ['py', 'js', 'jsx', 'ts', 'tsx', 'json', 'html', 'css', 'go', 'rs', 'java', 'c', 'cpp', 'h', 'sql'].includes(ext);
                    const isPdf = ext === 'pdf';
                    const icon = isImage ? '🖼️' : isCode ? '💻' : isPdf ? '📄' : '📎';

                    return (
                      <div
                        key={file.filename}
                        className={`uploaded-file-chip ${isImage ? 'has-thumbnail' : ''}`}
                        onClick={() => {
                          if (!activeConversationId) return;
                          const url = `/api/conversations/${activeConversationId}/files/${file.filename}`;
                          window.open(url, '_blank', 'noopener,noreferrer');
                        }}
                        role="button"
                        tabIndex={0}
                        title={`Open ${filename}`}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            const url = `/api/conversations/${activeConversationId}/files/${file.filename}`;
                            window.open(url, '_blank', 'noopener,noreferrer');
                          }
                        }}
                      >
                        {isImage && activeConversationId ? (
                          <img
                            src={`/api/conversations/${activeConversationId}/files/${file.filename}`}
                            alt={filename}
                            className="uploaded-file-thumbnail"
                          />
                        ) : (
                          <span className="uploaded-file-icon">{icon}</span>
                        )}
                        <span className="uploaded-file-name">{filename}</span>
                        <button
                          type="button"
                          className="remove-uploaded-file"
                          onClick={(event) => {
                            event.stopPropagation();
                            removeAttachedFile(file.filename);
                          }}
                          title="Remove attachment"
                        >
                          ×
                        </button>
                      </div>
                    );
                  })}
                </div>
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
                placeholder={isListening ? (interimTranscript || "Listening...") : (mode === 'council' ? "Ask the council..." : mode === 'compare' ? "Compare models..." : "Message...")}
                disabled={isLoading || isStreaming || isComparing}
                rows={1}
              />

              {/* Bottom toolbar */}
              <div className="claude-input-toolbar">
                <div className="claude-input-tools">
                  {/* Search toggle */}
                  <button
                    type="button"
                    onClick={cycleSearchMode}
                    className={`search-toggle-btn ${features.web_search || features.deep_search ? 'active' : ''} ${features.deep_search ? 'deep' : ''}`}
                    disabled={isLoading || isStreaming || isComparing}
                    title={`Search: ${features.deep_search ? `Deep (${hasPerplexityKey ? 'Perplexity' : 'Unavailable'})` : features.web_search ? 'Online (DuckDuckGo)' : 'Off'} (Ctrl+Shift+S)`}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <circle cx="11" cy="11" r="8"/>
                      <path d="m21 21-4.35-4.35"/>
                    </svg>
                    {(features.web_search || features.deep_search) && (
                      <span className="search-mode-badge">
                        {features.deep_search ? 'Deep' : 'Web'}
                      </span>
                    )}
                  </button>

                  {/* File upload button */}
                  <button
                    type="button"
                    onClick={() => setShowFileUpload(true)}
                    className={`file-btn ${attachedFiles.length > 0 ? 'has-files' : ''}`}
                    disabled={isLoading || isStreaming || isComparing || !activeConversationId}
                    title={!activeConversationId ? "Start a conversation first" : "Attach files (or drag & drop anywhere)"}
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                    </svg>
                    {attachedFiles.length > 0 && (
                      <span className="file-badge">{attachedFiles.length}</span>
                    )}
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
                    className={`options-toggle-btn ${showOptions ? 'active' : ''} ${(features.web_search || features.deep_search || features.memory || features.code_execution || features.fast_mode) ? 'has-active' : ''}`}
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
                      <div className="options-panel-v2">
                        {/* Search Section */}
                        <div className="options-section">
                          <div className="options-section-header">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                              <circle cx="11" cy="11" r="8"/>
                              <path d="m21 21-4.35-4.35"/>
                            </svg>
                            <span>Search</span>
                            <span className="options-provider">
                              {hasPerplexityKey ? 'Perplexity' : 'DuckDuckGo'}
                            </span>
                          </div>
                          <div className="options-toggle-group">
                            <button
                              type="button"
                              className={`option-toggle ${!features.web_search && !features.deep_search ? 'active' : ''}`}
                              onClick={() => setSearchMode('off')}
                            >
                              Off
                            </button>
                            <button
                              type="button"
                              className={`option-toggle ${features.web_search && !features.deep_search ? 'active' : ''}`}
                              onClick={() => setSearchMode('online')}
                            >
                              Online
                            </button>
                            <button
                              type="button"
                              className={`option-toggle ${features.deep_search ? 'active' : ''} ${!hasPerplexityKey ? 'tooltip' : ''}`}
                              onClick={() => setSearchMode('deep')}
                              disabled={!hasPerplexityKey}
                              data-tooltip={!hasPerplexityKey ? 'Deep search requires a Perplexity API key.' : undefined}
                              title={!hasPerplexityKey ? 'Deep search requires a Perplexity API key.' : 'Deep search'}
                            >
                              Deep
                            </button>
                          </div>
                        </div>

                      {/* Tools Section */}
                      <div className="options-section">
                        <div className="options-section-header">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
                          </svg>
                          <span>Tools</span>
                        </div>
                        <div className="options-chips">
                          <button
                            type="button"
                            className={`option-chip ${features.memory ? 'active' : ''}`}
                            onClick={() => toggleFeature('memory')}
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                              <path d="M12 8v4l3 3"/>
                            </svg>
                            Memory
                          </button>
                          <button
                            type="button"
                            className={`option-chip ${features.code_execution ? 'active' : ''}`}
                            onClick={() => toggleFeature('code_execution')}
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <polyline points="16 18 22 12 16 6"/>
                              <polyline points="8 6 2 12 8 18"/>
                            </svg>
                            Code
                          </button>
                        </div>
                      </div>

                      {/* Speed Section */}
                      <div className="options-section">
                        <div className="options-section-header">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                          </svg>
                          <span>Speed</span>
                        </div>
                        <div className="options-chips">
                          <button
                            type="button"
                            className={`option-chip ${features.fast_mode ? 'active' : ''}`}
                            onClick={() => setFeatures(prev => ({ ...prev, fast_mode: !prev.fast_mode }))}
                            title="Skip peer review (Stage 2) for faster Council results"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                            </svg>
                            Fast Mode
                          </button>
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
              </div>

              {/* Send/Stop button */}
              <div className="claude-input-actions">
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
              </div>
            </div>
          </form>

          {/* Input hints */}
          <div className="claude-input-hints">
            <span className="claude-input-hint">
              <kbd>Enter</kbd> send
            </span>
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
            setAttachedFiles(prev => [...prev, ...files]);
            toast.success(`${files.length} file${files.length !== 1 ? 's' : ''} attached`);
            loadAttachedFiles();
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
