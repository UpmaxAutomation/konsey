import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../../../api';

/**
 * Hook for file attachment, upload, and drag-and-drop functionality.
 *
 * @param {Object} params
 * @param {string|null} params.activeConversationId - Current conversation ID
 * @param {Object} params.toast - Toast notification instance
 * @returns {Object} File attachment state and handlers
 */
export function useFileAttach({ activeConversationId, toast }) {
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState([]);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState(false);
  const dragCounterRef = useRef(0);

  const loadAttachedFiles = useCallback(async () => {
    if (!activeConversationId) {
      setAttachedFiles([]);
      return;
    }
    try {
      const result = await api.listFiles(activeConversationId);
      setAttachedFiles(result.files || []);
    } catch (err) {
      console.error('Failed to load attachments:', err);
    }
  }, [activeConversationId]);

  useEffect(() => {
    loadAttachedFiles();
  }, [loadAttachedFiles]);

  const removeAttachedFile = async (filename) => {
    if (!activeConversationId) return;
    try {
      await api.deleteFile(activeConversationId, filename);
      setAttachedFiles((prev) => prev.filter((file) => file.filename !== filename));
    } catch (err) {
      console.error('Failed to remove attachment:', err);
      toast.error('Failed to remove attachment');
    }
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDraggingOver(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDraggingOver(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
    dragCounterRef.current = 0;

    if (!activeConversationId) {
      toast.error('Please select or create a conversation first');
      return;
    }

    const files = Array.from(e.dataTransfer.files);
    if (files.length === 0) return;

    setUploadingFiles(true);
    const uploadedFiles = [];

    for (const file of files) {
      try {
        const result = await api.uploadFile(activeConversationId, file);
        uploadedFiles.push({
          ...result,
          name: file.name,
          size: file.size,
          type: file.type
        });
      } catch (err) {
        toast.error(`Failed to upload ${file.name}: ${err.message}`);
      }
    }

    if (uploadedFiles.length > 0) {
      setAttachedFiles(prev => [...prev, ...uploadedFiles]);
      toast.success(`${uploadedFiles.length} file${uploadedFiles.length !== 1 ? 's' : ''} attached`);
    }
    setUploadingFiles(false);
  };

  return {
    showFileUpload,
    setShowFileUpload,
    attachedFiles,
    setAttachedFiles,
    isDraggingOver,
    uploadingFiles,
    loadAttachedFiles,
    removeAttachedFile,
    handleDragEnter,
    handleDragLeave,
    handleDragOver,
    handleDrop,
  };
}

export default useFileAttach;
