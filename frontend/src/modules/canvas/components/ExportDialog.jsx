import { useState } from 'react';
import { useExportBoard, useShareBoard } from '../../../api/queries/exportQueries';
import '../styles/ExportDialog.css';

const FORMATS = [
  { value: 'md', label: 'Markdown', desc: 'Readable text format with headings and sections' },
  { value: 'json', label: 'JSON', desc: 'Full board data for programmatic access' },
  { value: 'csv', label: 'CSV', desc: 'Spreadsheet format with card data as rows' },
  { value: 'zip', label: 'ZIP', desc: 'Complete archive with all formats and assets' },
];

export default function ExportDialog({ boardId, boardName, onClose }) {
  const [format, setFormat] = useState('md');
  const [shareLink, setShareLink] = useState(null);

  const exportMutation = useExportBoard();
  const shareMutation = useShareBoard();

  const handleExport = () => {
    exportMutation.mutate({ boardId, format });
  };

  const handleShare = async () => {
    try {
      const result = await shareMutation.mutateAsync(boardId);
      setShareLink(window.location.origin + result.share_url);
    } catch (err) {
      console.error('Failed to create share link:', err);
    }
  };

  const copyShareLink = () => {
    if (shareLink) {
      navigator.clipboard.writeText(shareLink);
    }
  };

  return (
    <div className="export-overlay" onClick={onClose}>
      <div className="export-dialog" role="dialog" aria-modal="true" aria-label="Export board" onClick={e => e.stopPropagation()}>
        <div className="export-header">
          <h2>Export Board</h2>
          <button className="export-close" onClick={onClose}>×</button>
        </div>

        <div className="export-section">
          <h3>Export Format</h3>
          <div className="export-formats">
            {FORMATS.map(f => (
              <label key={f.value} className={`export-format ${format === f.value ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name="format"
                  value={f.value}
                  checked={format === f.value}
                  onChange={e => setFormat(e.target.value)}
                />
                <div className="export-format-info">
                  <span className="export-format-label">{f.label}</span>
                  <span className="export-format-desc">{f.desc}</span>
                </div>
              </label>
            ))}
          </div>
          <button
            className="export-btn"
            onClick={handleExport}
            disabled={exportMutation.isPending}
          >
            {exportMutation.isPending ? 'Exporting...' : `Export as ${format.toUpperCase()}`}
          </button>
        </div>

        <div className="export-divider" />

        <div className="export-section">
          <h3>Share Link</h3>
          <p className="export-share-desc">
            Create a public, read-only link to share this board.
          </p>
          {shareLink ? (
            <div className="export-share-link">
              <input type="text" value={shareLink} readOnly className="export-share-input" />
              <button className="export-copy-btn" onClick={copyShareLink}>Copy</button>
            </div>
          ) : (
            <button
              className="export-share-btn"
              onClick={handleShare}
              disabled={shareMutation.isPending}
            >
              {shareMutation.isPending ? 'Creating...' : 'Generate Share Link'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
