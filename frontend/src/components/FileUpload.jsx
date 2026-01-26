import { useEffect, useState, useRef } from 'react';
import { api } from '../api';
import './FileUpload.css';

const FILE_ICONS = {
  '.pdf': '📄',
  '.doc': '📝',
  '.docx': '📝',
  '.txt': '📃',
  '.md': '📋',
  '.py': '🐍',
  '.js': '📜',
  '.jsx': '⚛️',
  '.ts': '📘',
  '.tsx': '⚛️',
  '.json': '📦',
  '.csv': '📊',
  '.png': '🖼️',
  '.jpg': '🖼️',
  '.jpeg': '🖼️',
  '.gif': '🎞️',
  '.webp': '🖼️',
  '.html': '🌐',
  '.css': '🎨',
  default: '📎'
};

export default function FileUpload({ conversationId, onFileUploaded, onClose }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState([]);
  const [error, setError] = useState(null);
  const [loadingExisting, setLoadingExisting] = useState(true);
  const fileInputRef = useRef(null);
  useEffect(() => {
    const loadExistingFiles = async () => {
      if (!conversationId) return;
      setLoadingExisting(true);
      setError(null);
      try {
        const result = await api.listFiles(conversationId);
        setFiles(result.files || []);
      } catch (err) {
        setError(`Failed to load existing files: ${err.message}`);
      } finally {
        setLoadingExisting(false);
      }
    };
    loadExistingFiles();
  }, [conversationId]);

  const getFileIcon = (filename) => {
    const ext = '.' + filename.split('.').pop().toLowerCase();
    return FILE_ICONS[ext] || FILE_ICONS.default;
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  };

  const handleFileSelect = (e) => {
    const selectedFiles = Array.from(e.target.files);
    handleFiles(selectedFiles);
  };

  const handleFiles = async (newFiles) => {
    setError(null);
    setUploading(true);

    const uploadedFiles = [];

    for (const file of newFiles) {
      try {
        const result = await api.uploadFile(conversationId, file);
        uploadedFiles.push({
          ...result,
          name: file.name,
          size: file.size,
          type: file.type
        });
      } catch (err) {
        setError(`Failed to upload ${file.name}: ${err.message}`);
      }
    }

    setFiles(prev => [...prev, ...uploadedFiles]);
    setUploading(false);

    if (onFileUploaded && uploadedFiles.length > 0) {
      onFileUploaded(uploadedFiles);
    }
  };

  const removeFile = async (fileToRemove) => {
    try {
      await api.deleteFile(conversationId, fileToRemove.filename);
      setFiles(prev => prev.filter((file) => file.filename !== fileToRemove.filename));
    } catch (err) {
      setError(`Failed to remove ${fileToRemove.filename}: ${err.message}`);
    }
  };

  const isImage = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    return ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext);
  };

  return (
    <div className="file-upload-overlay">
      <div className="file-upload-modal">
        <div className="file-upload-header">
          <h3>Upload Files</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div
          className={`file-upload-dropzone ${isDragging ? 'dragging' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <div className="dropzone-icon">📁</div>
          <div className="dropzone-text">
            <strong>Drop files here</strong> or click to browse
          </div>
          <div className="dropzone-hint">
            Supports images, PDFs, code files, and documents (max 25MB)
          </div>
        </div>

        {error && (
          <div className="file-upload-error">{error}</div>
        )}

        {loadingExisting && (
          <div className="file-upload-progress">
            <div className="spinner"></div>
            <span>Loading attachments...</span>
          </div>
        )}

        {uploading && (
          <div className="file-upload-progress">
            <div className="spinner"></div>
            <span>Uploading...</span>
          </div>
        )}

        {files.length > 0 && (
          <div className="file-list">
            <h4>Attachments ({files.length})</h4>
            {files.map((file) => {
              const filename = file.name || file.filename;
              const isImg = isImage(filename);
              const isCode = /\.(py|js|jsx|ts|tsx|json|html|css|go|rs|java|c|cpp|h|sh|sql|yaml|yml)$/i.test(filename);

              return (
                <div key={file.filename} className={`file-item ${isImg ? 'file-item-image' : ''}`}>
                  {isImg ? (
                    <div className="file-thumbnail">
                      <img
                        src={`/api/conversations/${conversationId}/files/${file.filename}`}
                        alt={filename}
                        loading="lazy"
                      />
                    </div>
                  ) : (
                    <span className="file-icon">{getFileIcon(filename)}</span>
                  )}
                  <div className="file-info">
                    <div className="file-name" title={filename}>{filename}</div>
                    <div className="file-meta">
                      <span className="file-size">{formatSize(file.size)}</span>
                      {isCode && <span className="file-type-badge">Code</span>}
                      {isImg && <span className="file-type-badge image">Image</span>}
                    </div>
                  </div>
                  <button
                    className="remove-file-btn"
                    onClick={() => removeFile(file)}
                    title="Remove file"
                  >
                    ×
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <div className="file-upload-actions">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={onClose}
            disabled={files.length === 0}
          >
            Done ({files.length} file{files.length !== 1 ? 's' : ''})
          </button>
        </div>
      </div>
    </div>
  );
}
