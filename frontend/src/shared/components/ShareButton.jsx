import { useState } from 'react';
import { api } from '../../api';
import { useToast } from './Toast';
import '../styles/ShareButton.css';

export default function ShareButton({ conversationId, conversationTitle }) {
  const [isOpen, setIsOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const handleShare = async () => {
    setLoading(true);
    try {
      const result = await api.shareConversation(conversationId);
      const fullUrl = `${window.location.origin}/share/${result.token}`;
      setShareUrl(fullUrl);
      setIsOpen(true);
    } catch (err) {
      toast.error('Failed to create share link');
    }
    setLoading(false);
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast.success('Link copied to clipboard!');
    } catch (err) {
      toast.error('Failed to copy link');
    }
  };

  const shareVia = (platform) => {
    const text = `Check out this AI Konsey conversation: ${conversationTitle || 'Untitled'}`;
    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(shareUrl)}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
      email: `mailto:?subject=${encodeURIComponent(conversationTitle || 'AI Konsey Conversation')}&body=${encodeURIComponent(text + '\n\n' + shareUrl)}`,
    };

    if (urls[platform]) {
      window.open(urls[platform], '_blank', 'width=600,height=400');
    }
  };

  return (
    <>
      <button
        className="share-btn"
        onClick={handleShare}
        disabled={loading}
        title="Share conversation"
      >
        {loading ? (
          <span className="share-spinner"></span>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
          </svg>
        )}
        <span>Share</span>
      </button>

      {isOpen && (
        <div className="share-modal-overlay" onClick={() => setIsOpen(false)}>
          <div className="share-modal" role="dialog" aria-modal="true" aria-label="Share conversation" onClick={(e) => e.stopPropagation()}>
            <div className="share-modal-header">
              <h3>Share Conversation</h3>
              <button className="share-close" onClick={() => setIsOpen(false)}>×</button>
            </div>

            <div className="share-modal-content">
              <p className="share-description">
                Anyone with this link can view this conversation (read-only).
              </p>

              <div className="share-url-container">
                <input
                  type="text"
                  value={shareUrl}
                  readOnly
                  className="share-url-input"
                />
                <button className="copy-btn" onClick={copyToClipboard}>
                  Copy
                </button>
              </div>

              <div className="share-platforms">
                <button className="platform-btn twitter" onClick={() => shareVia('twitter')}>
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                  </svg>
                </button>
                <button className="platform-btn linkedin" onClick={() => shareVia('linkedin')}>
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                  </svg>
                </button>
                <button className="platform-btn email" onClick={() => shareVia('email')}>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="4" width="20" height="16" rx="2"/>
                    <path d="m22 7-10 6L2 7"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
