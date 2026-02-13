import { useState, useRef, useEffect, useCallback } from 'react';
import SafeMarkdown from '../../../shared/components/SafeMarkdown';
import {
  createConversation,
  sendMessageStream,
  sendQuickMessageStream,
} from '../../../api/conversations.js';
import { createCard } from '../../../api/boards.js';
import '../styles/CardChatPanel.css';

export default function CardChatPanel({ card, boardId, onClose, onCardCreated }) {
  const [mode, setMode] = useState('quick'); // 'quick' or 'council'
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState(null);
  const [selectedText, setSelectedText] = useState('');
  const [selectionRect, setSelectionRect] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [councilStage, setCouncilStage] = useState(null);
  const [error, setError] = useState(null);
  const [contextExpanded, setContextExpanded] = useState(false);
  const abortRef = useRef(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const messageAppendedRef = useRef(false);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  // Abort on unmount
  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  // Escape to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const ensureConversation = useCallback(async () => {
    if (conversationId) return conversationId;
    const conv = await createConversation();
    const id = conv.id;
    setConversationId(id);
    return id;
  }, [conversationId]);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    setInput('');
    setError(null);

    // Build the message content - prepend card context on first message
    const isFirst = messages.length === 0;
    const fullContent = isFirst
      ? `<card-context title="${card.title}" type="${card.card_type}">\n${card.content || ''}\n</card-context>\n\nUser request: ${trimmed}`
      : trimmed;

    // Optimistic user message
    setMessages((prev) => [...prev, { role: 'user', content: trimmed }]);
    messageAppendedRef.current = false;
    setIsLoading(true);
    setStreamingText('');
    setCouncilStage(null);

    abortRef.current = new AbortController();

    try {
      const convId = await ensureConversation();

      if (mode === 'quick') {
        // Quick mode - single model streaming
        let accumulated = '';
        await sendQuickMessageStream(
          convId,
          fullContent,
          null, // default model
          (eventType, event) => {
            switch (eventType) {
              case 'chunk':
                accumulated += event.text || event.data || '';
                setStreamingText(accumulated);
                break;
              case 'complete':
                if (!messageAppendedRef.current) {
                  messageAppendedRef.current = true;
                  setMessages((prev) => [
                    ...prev,
                    { role: 'assistant', content: accumulated },
                  ]);
                }
                setStreamingText('');
                setIsLoading(false);
                break;
              case 'error':
                setError(event.message || 'An error occurred');
                setIsLoading(false);
                setStreamingText('');
                break;
            }
          },
          abortRef.current.signal,
        );
      } else {
        // Council mode - 3-stage streaming
        let stage3Content = '';
        await sendMessageStream(
          convId,
          fullContent,
          (eventType, event) => {
            switch (eventType) {
              case 'stage1_start':
                setCouncilStage('Stage 1: Gathering opinions...');
                break;
              case 'stage1_complete':
                setCouncilStage('Stage 1 complete');
                break;
              case 'stage2_start':
                setCouncilStage('Stage 2: Peer review...');
                break;
              case 'stage2_complete':
                setCouncilStage('Stage 2 complete');
                break;
              case 'stage3_start':
                setCouncilStage('Stage 3: Chairman synthesizing...');
                break;
              case 'stage3_complete':
                stage3Content = event.data?.response || '';
                if (!messageAppendedRef.current) {
                  messageAppendedRef.current = true;
                  setMessages((prev) => [
                    ...prev,
                    { role: 'assistant', content: stage3Content, isCouncil: true },
                  ]);
                }
                setCouncilStage(null);
                setIsLoading(false);
                break;
              case 'complete':
                setIsLoading(false);
                setCouncilStage(null);
                break;
              case 'error':
                setError(event.message || 'An error occurred');
                setIsLoading(false);
                setCouncilStage(null);
                break;
            }
          },
          abortRef.current.signal,
        );
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Failed to send message');
        setIsLoading(false);
        setStreamingText('');
        setCouncilStage(null);
      }
    } finally {
      abortRef.current = null;
    }
  }, [input, isLoading, messages.length, card, mode, ensureConversation]);

  const handleStop = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setIsLoading(false);
    setStreamingText('');
    setCouncilStage(null);
  }, []);

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
    }
  }, []);

  // Enhance native text drag so dropping selected text onto canvas creates a card
  const handleMessageDragStart = useCallback((e) => {
    const sel = window.getSelection();
    const text = sel?.toString().trim();
    if (text && text.length > 2) {
      const payload = JSON.stringify({
        text,
        title: text.slice(0, 60),
        sourceCardId: card?.id || null,
      });
      e.dataTransfer.setData('application/x-council-card', payload);
      e.dataTransfer.setData('text/plain', text);
      e.dataTransfer.effectAllowed = 'copy';
    }
  }, [card]);

  const handlePinToBoard = useCallback(async (content) => {
    try {
      const newCard = await createCard(boardId, {
        card_type: 'council_response',
        title: `Re: ${card.title}`,
        content,
        position_x: (parseFloat(card.id) || 0) + 320,
        position_y: 0,
      });
      onCardCreated?.(newCard);
    } catch (err) {
      setError('Failed to pin to board: ' + err.message);
    }
  }, [boardId, card, onCardCreated]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const truncatedContent = card.content
    ? card.content.length > 300
      ? card.content.slice(0, 300) + '...'
      : card.content
    : 'No content';

  return (
    <div className="card-chat-panel" role="complementary" aria-label="Card Discussion">
      {/* Header */}
      <div className="card-chat-panel__header">
        <div className="card-chat-panel__header-left">
          <span className="card-chat-panel__header-icon">💬</span>
          <h3 className="card-chat-panel__title" title={card.title}>
            Discuss: {card.title || 'Untitled'}
          </h3>
        </div>
        <div className="card-chat-panel__header-right">
          <div className="card-chat-panel__mode-toggle">
            <button
              className={`card-chat-panel__mode-btn ${mode === 'quick' ? 'card-chat-panel__mode-btn--active' : ''}`}
              onClick={() => setMode('quick')}
              disabled={isLoading}
            >
              Quick
            </button>
            <button
              className={`card-chat-panel__mode-btn ${mode === 'council' ? 'card-chat-panel__mode-btn--active' : ''}`}
              onClick={() => setMode('council')}
              disabled={isLoading}
            >
              Council
            </button>
          </div>
          <button
            className="card-chat-panel__close"
            onClick={onClose}
            title="Close panel"
            aria-label="Close discussion panel"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Card Context */}
      <div className="card-chat-panel__context">
        <button
          className="card-chat-panel__context-toggle"
          onClick={() => setContextExpanded(!contextExpanded)}
        >
          <svg
            className={`card-chat-panel__context-chevron ${contextExpanded ? 'card-chat-panel__context-chevron--open' : ''}`}
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M9 18l6-6-6-6" />
          </svg>
          <span className="card-chat-panel__context-label">
            Card context ({card.card_type})
          </span>
        </button>
        {contextExpanded && (
          <div className="card-chat-panel__context-body">
            <SafeMarkdown>{truncatedContent}</SafeMarkdown>
          </div>
        )}
      </div>

      {/* Text selection → drag to canvas */}
      {selectedText && selectionRect && (
        <div
          className="card-chat-panel__selection-action"
          style={{ position: 'fixed', top: selectionRect.top, left: selectionRect.left, transform: 'translateX(-50%)', zIndex: 1000 }}
        >
          <span
            className="card-chat-panel__drag-handle"
            draggable
            onDragStart={(e) => {
              const payload = JSON.stringify({ text: selectedText, title: selectedText.slice(0, 60), sourceCardId: card?.id || null });
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
            className="card-chat-panel__card-btn"
            onClick={async () => {
              try {
                const newCard = await createCard(boardId, {
                  card_type: 'note',
                  title: selectedText.slice(0, 60),
                  content: selectedText,
                });
                onCardCreated?.(newCard);
              } catch (err) {
                setError('Failed to create card: ' + err.message);
              }
              setSelectedText('');
              setSelectionRect(null);
              window.getSelection()?.removeAllRanges();
            }}
          >
            + Card
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="card-chat-panel__messages" onMouseUp={handleMessageMouseUp} onDragStart={handleMessageDragStart}>
        {messages.length === 0 && !isLoading && (
          <div className="card-chat-panel__empty">
            Ask a question about this card. {mode === 'council' ? 'The council will deliberate.' : 'A single model will respond.'}
          </div>
        )}
        {messages.map((msg, idx) => (
          <div key={idx} className={`card-chat-panel__msg card-chat-panel__msg--${msg.role}`}>
            {msg.role === 'assistant' && (
              <div className="card-chat-panel__msg-header">
                {msg.isCouncil && <span className="card-chat-panel__council-badge">Council</span>}
                <button
                  className="card-chat-panel__pin-btn"
                  onClick={() => handlePinToBoard(msg.content)}
                  title="Pin to board as card"
                >
                  📌 Pin to Board
                </button>
              </div>
            )}
            <div className="card-chat-panel__msg-body">
              {msg.role === 'assistant' ? (
                <div className="markdown-content">
                  <SafeMarkdown>{msg.content}</SafeMarkdown>
                </div>
              ) : (
                <span>{msg.content}</span>
              )}
            </div>
          </div>
        ))}

        {/* Streaming indicator */}
        {isLoading && streamingText && (
          <div className="card-chat-panel__msg card-chat-panel__msg--assistant">
            <div className="card-chat-panel__msg-body">
              <div className="markdown-content">
                <SafeMarkdown>{streamingText}</SafeMarkdown>
              </div>
            </div>
          </div>
        )}

        {/* Council stage indicator */}
        {isLoading && councilStage && (
          <div className="card-chat-panel__stage-indicator">
            <div className="card-chat-panel__stage-dot" />
            <span>{councilStage}</span>
          </div>
        )}

        {/* Generic loading */}
        {isLoading && !streamingText && !councilStage && (
          <div className="card-chat-panel__stage-indicator">
            <div className="card-chat-panel__stage-dot" />
            <span>Thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="card-chat-panel__error" role="alert">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error">&times;</button>
        </div>
      )}

      {/* Input */}
      <div className="card-chat-panel__input-area">
        <textarea
          ref={textareaRef}
          className="card-chat-panel__input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={`Ask about "${card.title}"...`}
          rows={2}
          disabled={isLoading}
        />
        {isLoading ? (
          <button
            className="card-chat-panel__send-btn card-chat-panel__send-btn--stop"
            onClick={handleStop}
            aria-label="Stop"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" />
            </svg>
          </button>
        ) : (
          <button
            className="card-chat-panel__send-btn"
            onClick={handleSend}
            disabled={!input.trim()}
            aria-label="Send message"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
