import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { api } from '../api';
import './SharedConversation.css';

export default function SharedConversation() {
  const { token } = useParams();
  const [conversation, setConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadConversation = async () => {
      try {
        const data = await api.getSharedConversation(token);
        setConversation(data);
      } catch (err) {
        setError(err.message);
      }
      setLoading(false);
    };

    loadConversation();
  }, [token]);

  if (loading) {
    return (
      <div className="shared-loading">
        <div className="spinner"></div>
        <p>Loading shared conversation...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="shared-error">
        <div className="error-icon">🔒</div>
        <h1>Link Not Found</h1>
        <p>{error}</p>
        <Link to="/" className="back-link">Go to AI Konsey</Link>
      </div>
    );
  }

  return (
    <div className="shared-conversation">
      <header className="shared-header">
        <div className="shared-branding">
          <span className="logo">👥</span>
          <span>AI Konsey</span>
        </div>
        <div className="shared-title">
          <h1>{conversation.title}</h1>
          <span className="shared-badge">Shared</span>
        </div>
        <Link to="/" className="try-council-btn">
          Try AI Konsey
        </Link>
      </header>

      <main className="shared-messages">
        {conversation.messages?.map((msg, index) => (
          <div key={index} className={`shared-message ${msg.role}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? '👤' : '👥'}
            </div>
            <div className="message-body">
              {msg.role === 'assistant' ? (
                <>
                  {/* Show final synthesis if available */}
                  {msg.stage3 && (
                    <div className="final-response">
                      <ReactMarkdown>
                        {typeof msg.stage3 === 'object' ? msg.stage3.response : msg.stage3}
                      </ReactMarkdown>
                    </div>
                  )}

                  {/* Show individual responses */}
                  {msg.stage1 && (
                    <details className="stage-details">
                      <summary>View Council Responses ({msg.stage1.length} models)</summary>
                      <div className="stage1-responses">
                        {msg.stage1.map((resp, i) => (
                          <div key={i} className="model-response">
                            <div className="model-name">{resp.model}</div>
                            <ReactMarkdown>{resp.response}</ReactMarkdown>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </>
              ) : (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              )}
            </div>
          </div>
        ))}
      </main>

      <footer className="shared-footer">
        <p>
          Powered by <a href="/">AI Konsey</a> - Multi-model AI deliberation
        </p>
      </footer>
    </div>
  );
}
