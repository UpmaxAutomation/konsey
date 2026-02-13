import { useState, useCallback, useRef, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import { useAnnotations, useAddAnnotation, useDeleteAnnotation } from '../../../api/queries/annotationQueries';
import '../styles/PdfViewer.css';

// Configure pdf.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

/**
 * Inline PDF viewer with annotation (highlight) support.
 * Renders inside card attachments area.
 *
 * @param {Object} props
 * @param {string} props.attachmentId - Attachment UUID for annotation CRUD
 * @param {string} props.url - PDF data URL or remote URL
 * @param {string} props.filename - Display filename
 */
export default function PdfViewer({ attachmentId, url, filename }) {
  const [numPages, setNumPages] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [selectedText, setSelectedText] = useState(null);
  const [selectionPosition, setSelectionPosition] = useState(null);
  const [highlightColor, setHighlightColor] = useState('#FFEB3B');
  const [loadError, setLoadError] = useState(null);
  const documentRef = useRef(null);

  const { data: annotations = [] } = useAnnotations(attachmentId);
  const addAnnotation = useAddAnnotation(attachmentId);
  const deleteAnnotation = useDeleteAnnotation(attachmentId);

  const currentAnnotations = annotations.filter(a => a.page === currentPage);

  const onDocumentLoadSuccess = useCallback(({ numPages: total }) => {
    setNumPages(total);
    setLoadError(null);
  }, []);

  const onDocumentLoadError = useCallback((error) => {
    setLoadError('Failed to load PDF');
    console.error('PDF load error:', error);
  }, []);

  // Handle text selection for creating highlights
  const handleMouseUp = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !selection.toString().trim()) {
      setSelectedText(null);
      setSelectionPosition(null);
      return;
    }

    const text = selection.toString().trim();
    if (!text) return;

    // Get selection bounding rects relative to the document container
    const range = selection.getRangeAt(0);
    const containerEl = documentRef.current;
    if (!containerEl) return;

    const containerRect = containerEl.getBoundingClientRect();
    const rangeRects = Array.from(range.getClientRects());

    // Convert to relative positions within the document container
    const rects = rangeRects.map(r => ({
      x: r.left - containerRect.left,
      y: r.top - containerRect.top,
      width: r.width,
      height: r.height,
    }));

    if (rects.length === 0) return;

    // Position the highlight button near the selection
    const lastRect = rects[rects.length - 1];
    setSelectionPosition({
      x: lastRect.x + lastRect.width / 2,
      y: lastRect.y - 8,
    });

    setSelectedText({ text, rects });
  }, []);

  // Create highlight annotation from selection
  const handleCreateHighlight = useCallback(() => {
    if (!selectedText) return;

    addAnnotation.mutate({
      page: currentPage,
      type: 'highlight',
      content: selectedText.text,
      rects: selectedText.rects,
      color: highlightColor,
    });

    // Clear selection
    window.getSelection()?.removeAllRanges();
    setSelectedText(null);
    setSelectionPosition(null);
  }, [selectedText, currentPage, highlightColor, addAnnotation]);

  // Clear selection when changing pages
  useEffect(() => {
    setSelectedText(null);
    setSelectionPosition(null);
  }, [currentPage]);

  const handleDeleteAnnotation = useCallback((annotId) => {
    deleteAnnotation.mutate(annotId);
  }, [deleteAnnotation]);

  const COLOR_OPTIONS = ['#FFEB3B', '#4CAF50', '#2196F3', '#FF5722', '#E91E63', '#9C27B0'];

  return (
    <div className="pdf-viewer">
      {/* Toolbar */}
      <div className="pdf-viewer__toolbar">
        <div className="pdf-viewer__nav">
          <button
            className="pdf-viewer__btn"
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
            title="Previous page"
          >
            &#8249;
          </button>
          <span className="pdf-viewer__page-info">
            {currentPage} / {numPages || '?'}
          </span>
          <button
            className="pdf-viewer__btn"
            onClick={() => setCurrentPage(p => Math.min(numPages || p, p + 1))}
            disabled={currentPage >= numPages}
            title="Next page"
          >
            &#8250;
          </button>
        </div>
        <div className="pdf-viewer__zoom">
          <button
            className="pdf-viewer__btn"
            onClick={() => setScale(s => Math.max(0.5, s - 0.25))}
            disabled={scale <= 0.5}
            title="Zoom out"
          >
            &minus;
          </button>
          <span className="pdf-viewer__zoom-level">{Math.round(scale * 100)}%</span>
          <button
            className="pdf-viewer__btn"
            onClick={() => setScale(s => Math.min(3, s + 0.25))}
            disabled={scale >= 3}
            title="Zoom in"
          >
            +
          </button>
        </div>
        <div className="pdf-viewer__color-picker">
          {COLOR_OPTIONS.map(c => (
            <button
              key={c}
              className={`pdf-viewer__color-swatch${highlightColor === c ? ' pdf-viewer__color-swatch--active' : ''}`}
              style={{ backgroundColor: c }}
              onClick={() => setHighlightColor(c)}
              title={`Highlight color: ${c}`}
            />
          ))}
        </div>
      </div>

      {/* Document */}
      <div
        className="pdf-viewer__document"
        ref={documentRef}
        onMouseUp={handleMouseUp}
      >
        {loadError ? (
          <div className="pdf-viewer__error">{loadError}</div>
        ) : (
          <Document
            file={url}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={<div className="pdf-viewer__loading">Loading PDF...</div>}
          >
            <div className="pdf-viewer__page-wrapper">
              <Page
                pageNumber={currentPage}
                scale={scale}
                renderTextLayer={true}
                renderAnnotationLayer={true}
              />
              {/* Render highlight overlays for current page */}
              {currentAnnotations.map(annot =>
                annot.rects?.map((rect, i) => (
                  <div
                    key={`${annot.id}-${i}`}
                    className="pdf-viewer__highlight"
                    style={{
                      left: `${rect.x}px`,
                      top: `${rect.y}px`,
                      width: `${rect.width}px`,
                      height: `${rect.height}px`,
                      backgroundColor: annot.color || '#FFEB3B',
                    }}
                    title={annot.content}
                    onClick={() => handleDeleteAnnotation(annot.id)}
                  />
                ))
              )}
            </div>
          </Document>
        )}

        {/* Floating highlight button on text selection */}
        {selectedText && selectionPosition && (
          <div
            className="pdf-viewer__selection-toolbar"
            style={{
              left: `${selectionPosition.x}px`,
              top: `${selectionPosition.y}px`,
            }}
          >
            <button
              className="pdf-viewer__highlight-btn"
              onClick={handleCreateHighlight}
              disabled={addAnnotation.isPending}
            >
              {addAnnotation.isPending ? 'Saving...' : 'Highlight'}
            </button>
          </div>
        )}
      </div>

      {/* Annotation list */}
      {currentAnnotations.length > 0 && (
        <div className="pdf-viewer__annotations">
          <span className="pdf-viewer__annot-label">
            Annotations on page {currentPage} ({currentAnnotations.length})
          </span>
          <div className="pdf-viewer__annot-list">
            {currentAnnotations.map(annot => (
              <div key={annot.id} className="pdf-viewer__annot-item">
                <span
                  className="pdf-viewer__annot-color"
                  style={{ backgroundColor: annot.color || '#FFEB3B' }}
                />
                <span className="pdf-viewer__annot-text">
                  {annot.content.length > 80
                    ? annot.content.slice(0, 80) + '...'
                    : annot.content}
                </span>
                <button
                  className="pdf-viewer__annot-delete"
                  onClick={() => handleDeleteAnnotation(annot.id)}
                  title="Delete annotation"
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
