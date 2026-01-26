import { useState, useRef } from 'react';
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
  const fileInputRef = useRef(null);

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

  const removeFile = (index) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
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

        {uploading && (
          <div className="file-upload-progress">
            <div className="spinner"></div>
            <span>Uploading...</span>
          </div>
        )}

        {files.length > 0 && (
          <div className="file-list">
            <h4>Uploaded Files</h4>
            {files.map((file, index) => (
              <div key={index} className="file-item">
                <span className="file-icon">{getFileIcon(file.name || file.filename)}</span>
                <div className="file-info">
                  <div className="file-name">{file.name || file.filename}</div>
                  <div className="file-size">{formatSize(file.size)}</div>
                </div>
                {isImage(file.name || file.filename) && (
                  <div className="file-preview">
                    <img
                      src={`/api/conversations/${conversationId}/files/${file.filename}`}
                      alt="Preview"
                    />
                  </div>
                )}
                <button
                  className="remove-file-btn"
                  onClick={() => removeFile(index)}
                >
                  ×
                </button>
              </div>
            ))}
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
