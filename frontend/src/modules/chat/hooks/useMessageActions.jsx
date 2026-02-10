import { useState, useCallback } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ChartRenderer, { isChartLanguage, getChartType } from '../../../shared/components/ChartRenderer';
import { api } from '../../../api';
import { createCardsFromCouncilTurn } from '../../../api/boards';

/**
 * Hook for message-level actions: copy, edit, regenerate, fork, export, board picker.
 *
 * @param {Object} params
 * @param {Object} params.conversation - Current conversation object
 * @param {string} params.mode - Current mode ('quick', 'council', 'compare', 'auto')
 * @param {string} params.selectedModel - Currently selected model ID
 * @param {boolean} params.isLoading - Whether a council request is loading
 * @param {boolean} params.isStreaming - Whether a streaming response is active
 * @param {Array} params.attachedFiles - Currently attached files
 * @param {Object} params.features - Feature toggles
 * @param {Function} params.onSendMessage - Callback to send a council message
 * @param {Function} params.onConversationUpdate - Callback to refresh a conversation
 * @param {Object} params.toast - Toast notification instance
 * @param {Function} params.setStreamingText - Setter for streaming text state
 * @param {Function} params.setIsStreaming - Setter for isStreaming state
 * @param {React.RefObject} params.abortControllerRef - Ref to the abort controller
 * @param {Function} params.setInput - Setter for the text input state
 * @returns {Object} Message action state and handlers
 */
export function useMessageActions({
  conversation,
  mode,
  selectedModel,
  isLoading,
  isStreaming,
  attachedFiles,
  features,
  onSendMessage,
  onConversationUpdate,
  toast,
  setStreamingText,
  setIsStreaming,
  abortControllerRef,
  setInput,
}) {
  const [copiedCode, setCopiedCode] = useState(null);
  const [copiedMessageIndex, setCopiedMessageIndex] = useState(null);
  const [editingMessageIndex, setEditingMessageIndex] = useState(null);
  const [editingText, setEditingText] = useState('');
  const [regeneratingIndex, setRegeneratingIndex] = useState(null);
  const [expandedCouncil, setExpandedCouncil] = useState({});
  const [boardPickerIndex, setBoardPickerIndex] = useState(null);
  const [showShortcuts, setShowShortcuts] = useState(false);

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

  // Add a full council turn to a board
  const handleAddTurnToBoard = async (boardId, msg) => {
    try {
      const userMsg = conversation.messages?.find((m, idx) => m.role === 'user' && idx < conversation.messages.indexOf(msg));
      await createCardsFromCouncilTurn(boardId, {
        conversation_id: conversation.id,
        query: userMsg?.content || '',
        stage1: msg.stage1 || [],
        stage3: typeof msg.stage3 === 'object' ? msg.stage3 : { model: 'chairman', response: msg.stage3 || '' },
      });
      setBoardPickerIndex(null);
    } catch (err) {
      console.error('Failed to add turn to board:', err);
    }
  };

  // Regenerate an assistant response
  const regenerateMessage = async (messageIndex) => {
    if (!conversation?.messages || isLoading || isStreaming) return;

    const userMessageIndex = messageIndex - 1;
    if (userMessageIndex < 0 || conversation.messages[userMessageIndex]?.role !== 'user') {
      toast.error('Cannot regenerate: no user message found');
      return;
    }

    const userMessage = conversation.messages[userMessageIndex];
    const content = userMessage.content || '';

    setRegeneratingIndex(messageIndex);

    try {
      if (mode === 'council') {
        onSendMessage(content, attachedFiles.map(f => f.filename), features);
      } else {
        setStreamingText('');
        abortControllerRef.current = new AbortController();
        setIsStreaming(true);

        await api.sendQuickMessageStream(
          conversation.id,
          content,
          selectedModel,
          (type, event) => {
            if (type === 'chunk') {
              setStreamingText(prev => prev + event.data);
            } else if (type === 'complete' || type === 'title_complete') {
              setStreamingText('');
              onConversationUpdate?.(conversation.id);
            } else if (type === 'error') {
              setStreamingText('');
              toast.error('Regeneration failed');
            }
          },
          abortControllerRef.current.signal,
          attachedFiles.map(f => f.filename),
          {},
          features
        );

        setIsStreaming(false);
      }
      toast.success('Regenerating response...');
    } catch (err) {
      console.error('Failed to regenerate:', err);
      toast.error('Failed to regenerate response');
    } finally {
      setRegeneratingIndex(null);
    }
  };

  // Start editing a user message
  const startEditMessage = (messageIndex) => {
    const msg = conversation?.messages?.[messageIndex];
    if (!msg || msg.role !== 'user') return;

    setEditingMessageIndex(messageIndex);
    setEditingText(msg.content || '');
  };

  // Save edited message
  const saveEditMessage = async () => {
    if (editingMessageIndex === null || !editingText.trim()) return;
    setInput(editingText);
    cancelEditMessage();
    toast.info('Edit applied - send to update conversation');
  };

  // Cancel editing
  const cancelEditMessage = () => {
    setEditingMessageIndex(null);
    setEditingText('');
  };

  // Fork conversation from a specific message
  const handleForkConversation = async (messageIndex) => {
    if (!conversation?.id) return;

    try {
      const forked = await api.forkConversation(conversation.id, messageIndex);
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

    conversation.messages.forEach((msg) => {
      const role = msg.role === 'user' ? '**You**' : '**Assistant**';
      const stage3Content = typeof msg.stage3 === 'object' ? msg.stage3?.response : msg.stage3;
      const content = msg.content || stage3Content || '';

      markdown += `### ${role}\n\n${content}\n\n`;

      if (msg.stage1 && msg.role === 'assistant') {
        markdown += `<details>\n<summary>Council Deliberation</summary>\n\n`;
        msg.stage1.forEach(resp => {
          markdown += `**${resp.model}:**\n${resp.response}\n\n`;
        });
        markdown += `</details>\n\n`;
      }

      markdown += `---\n\n`;
    });

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

  // Format message timestamp
  const formatMessageTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;

    const isToday = date.toDateString() === now.toDateString();
    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  // Custom code block renderer with copy button and chart support
  const CodeBlock = useCallback(({ node, inline, className, children, ...props }) => {
    const match = /language-(\w+:?\w*)/.exec(className || '');
    const language = match ? match[1] : '';
    const code = String(children).replace(/\n$/, '');

    if (!inline && isChartLanguage(language)) {
      const chartType = getChartType(language);
      return <ChartRenderer type={chartType}>{code}</ChartRenderer>;
    }

    if (!inline && match) {
      return (
        <div className="code-block-wrapper">
          <div className="code-block-header">
            <span className="code-language">{language}</span>
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
            language={language}
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
  }, [copiedCode]);

  return {
    copiedCode,
    copiedMessageIndex,
    editingMessageIndex,
    editingText,
    regeneratingIndex,
    expandedCouncil,
    setExpandedCouncil,
    boardPickerIndex,
    setBoardPickerIndex,
    showShortcuts,
    setShowShortcuts,
    copyCode,
    copyMessage,
    copyConversation,
    handleAddTurnToBoard,
    regenerateMessage,
    startEditMessage,
    saveEditMessage,
    cancelEditMessage,
    handleForkConversation,
    exportConversation,
    formatMessageTime,
    CodeBlock,
  };
}

export default useMessageActions;
