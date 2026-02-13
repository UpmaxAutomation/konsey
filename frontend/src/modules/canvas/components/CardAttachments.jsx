import { useState, useCallback, useRef } from 'react';
import { useCardAttachments, useUploadAttachment, useAddEmbed, useDeleteAttachment } from '../../../api/queries/cardAttachmentQueries';
import PdfViewer from './PdfViewer';
import '../styles/CardAttachments.css';

const FILE_TYPE_ICONS = {
  image: '\uD83D\uDDBC\uFE0F',
  pdf: '\uD83D\uDCC4',
  video: '\uD83C\uDFA5',
  audio: '\uD83C\uDFB5',
  embed: '\uD83D\uDD17',
  file: '\uD83D\uDCC1',
};

function isYouTubeUrl(url) {
  return /(?:youtube\.com\/watch|youtu\.be\/|youtube\.com\/embed)/.test(url || '');
}

function getYouTubeEmbedUrl(url) {
  const match = url.match(/(?:v=|youtu\.be\/|embed\/)([a-zA-Z0-9_-]{11})/);
  return match ? `https://www.youtube.com/embed/${match[1]}` : null;
}

export default function CardAttachments({ cardId, compact = false }) {
  const { data, isLoading } = useCardAttachments(cardId);
  const uploadMutation = useUploadAttachment(cardId);
  const embedMutation = useAddEmbed(cardId);
  const deleteMutation = useDeleteAttachment(cardId);
  const fileInputRef = useRef(null);
  const [showEmbedInput, setShowEmbedInput] = useState(false);
  const [embedUrl, setEmbedUrl] = useState('');
  const [expandedPdf, setExpandedPdf] = useState(null);

  const togglePdfViewer = useCallback((attId) => {
    setExpandedPdf(prev => prev === attId ? null : attId);
  }, []);

  const attachments = data?.attachments || [];

  const handleFileSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadMutation.mutate(file);
    }
  }, [uploadMutation]);

  const handleAddEmbed = useCallback(() => {
    if (!embedUrl.trim()) return;
    embedMutation.mutate({ url: embedUrl.trim(), title: embedUrl.trim() });
    setEmbedUrl('');
    setShowEmbedInput(false);
  }, [embedUrl, embedMutation]);

  const handleDelete = useCallback((id) => {
    deleteMutation.mutate(id);
  }, [deleteMutation]);

  if (compact) {
    if (attachments.length === 0) return null;
    return (
      <div className="card-attachments card-attachments--compact">
        <span className="card-attachments__badge">{'\uD83D\uDCCE'} {attachments.length}</span>
      </div>
    );
  }

  return (
    <div className="card-attachments">
      <div className="card-attachments__header">
        <span className="card-attachments__label">Attachments ({attachments.length})</span>
        <div className="card-attachments__actions">
          <button className="card-attachments__add-btn" onClick={() => fileInputRef.current?.click()} title="Upload file">
            {'\uD83D\uDCCE'}
          </button>
          <button className="card-attachments__add-btn" onClick={() => setShowEmbedInput(!showEmbedInput)} title="Add embed">
            {'\uD83D\uDD17'}
          </button>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />
      </div>

      {showEmbedInput && (
        <div className="card-attachments__embed-input">
          <input
            placeholder="Paste YouTube or embed URL..."
            value={embedUrl}
            onChange={e => setEmbedUrl(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAddEmbed()}
          />
          <button onClick={handleAddEmbed}>Add</button>
        </div>
      )}

      {isLoading && <div className="card-attachments__loading">Loading...</div>}

      <div className="card-attachments__list">
        {attachments.map(att => (
          <div key={att.id} className="card-attachments__item">
            {att.file_type === 'embed' && att.embed_url && isYouTubeUrl(att.embed_url) ? (
              <div className="card-attachments__embed">
                <iframe
                  src={getYouTubeEmbedUrl(att.embed_url)}
                  width="100%"
                  height="160"
                  frameBorder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                  title={att.filename}
                />
              </div>
            ) : att.file_type === 'image' && att.url ? (
              <img className="card-attachments__thumb" src={att.url} alt={att.filename} />
            ) : att.file_type === 'pdf' || att.filename?.endsWith('.pdf') ? (
              <div className="card-attachments__pdf-section">
                <div className="card-attachments__pdf-header" onClick={() => togglePdfViewer(att.id)}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="1.5">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <text x="7" y="18" fontSize="6" fill="#dc2626" stroke="none" fontWeight="bold">PDF</text>
                  </svg>
                  <span className="card-attachments__filename">{att.filename}</span>
                  {att.metadata_json?.annotations?.length > 0 && (
                    <span className="card-attachments__annot-badge">
                      {att.metadata_json.annotations.length} annotation{att.metadata_json.annotations.length !== 1 ? 's' : ''}
                    </span>
                  )}
                  <button className="card-attachments__pdf-toggle" onClick={(e) => { e.stopPropagation(); togglePdfViewer(att.id); }}>
                    {expandedPdf === att.id ? 'Hide' : 'View'}
                  </button>
                </div>
                {expandedPdf === att.id && (
                  <PdfViewer attachmentId={att.id} url={att.url} filename={att.filename} />
                )}
              </div>
            ) : (
              <div className="card-attachments__file-info">
                <span className="card-attachments__file-icon">{FILE_TYPE_ICONS[att.file_type] || FILE_TYPE_ICONS.file}</span>
                <span className="card-attachments__filename">{att.filename}</span>
                {att.file_size && <span className="card-attachments__size">{(att.file_size / 1024).toFixed(0)}KB</span>}
              </div>
            )}
            <button className="card-attachments__remove" onClick={() => handleDelete(att.id)} title="Remove">{'\u00D7'}</button>
          </div>
        ))}
      </div>

      {uploadMutation.isPending && <div className="card-attachments__uploading">Uploading...</div>}
    </div>
  );
}
