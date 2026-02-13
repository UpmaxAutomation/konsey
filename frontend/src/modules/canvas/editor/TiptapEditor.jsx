/**
 * TiptapEditor — Rich text editor wrapping Tiptap for canvas card editing.
 *
 * Renders an inline WYSIWYG editor with markdown I/O, a floating
 * BubbleToolbar for formatting, and keyboard shortcuts for save/cancel.
 *
 * @module canvas/editor/TiptapEditor
 */
import { useEffect, useRef, useState, Component, memo } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import { buildExtensions } from './extensions';
import BubbleToolbar from './BubbleToolbar';
import FloatingAddMenu from './FloatingAddMenu';
import './TiptapEditor.css';
import './BubbleToolbar.css';

/** Inline error boundary — prevents toolbar crashes from killing the editor */
class PluginBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(err) { console.warn('Editor plugin crashed:', err); }
  render() { return this.state.failed ? null : this.props.children; }
}

/**
 * TiptapEditor component.
 *
 * @param {Object} props
 * @param {string} props.content - Markdown content to load into the editor
 * @param {function} props.onSave - Called with markdown string on Cmd/Ctrl+Enter
 * @param {function} props.onCancel - Called on Escape
 * @param {function} [props.onContentChange] - Called with markdown string on every update
 * @param {string} [props.placeholder='Start writing...'] - Placeholder text
 * @param {boolean} [props.autoFocus=true] - Focus editor on mount
 * @returns {JSX.Element}
 */
function TiptapEditor({
  content,
  cardId,
  onSave,
  onCancel,
  onContentChange,
  placeholder = 'Start writing...',
  autoFocus = true,
  boardCards = [],
  onExtractToCard,
}) {
  // Keep latest callbacks in refs to avoid stale closures inside editorProps
  const callbacksRef = useRef({ onSave, onCancel, onContentChange, cardId });
  callbacksRef.current = { onSave, onCancel, onContentChange, cardId };

  // Ref to hold the editor instance for use inside editorProps.handleKeyDown
  const editorRef = useRef(null);
  const [initError, setInitError] = useState(null);
  const [slashInput, setSlashInput] = useState(null); // { type: 'image'|'embed' }
  const slashInputRef = useRef(null);

  const editor = useEditor({
    extensions: buildExtensions({ placeholder }),
    content: content || '',
    immediatelyRender: false,
    onCreate: () => setInitError(null),
    onUpdate: ({ editor: ed }) => {
      try {
        const md = ed.storage.markdown?.getMarkdown?.() ?? ed.getText();
        callbacksRef.current.onContentChange?.(md);
      } catch (err) {
        console.error('TiptapEditor onUpdate error:', err);
      }
    },
    editorProps: {
      attributes: {
        class: 'tiptap-editor__content nodrag nowheel nopan',
      },
      handleDOMEvents: {
        dragstart(view, event) {
          // When text is selected in the editor and dragged, tag the drag data
          // with the custom MIME type so the canvas drop handler can create a
          // new linked card. We read from ProseMirror state (not window.getSelection)
          // because ProseMirror owns the selection.
          const { from, to } = view.state.selection;
          if (from === to) return false;
          const text = view.state.doc.textBetween(from, to, '\n');
          if (text.trim().length < 5) return false;
          const cid = callbacksRef.current.cardId;
          if (!cid) return false;
          const trimmed = text.trim();
          const payload = JSON.stringify({
            text: trimmed,
            title: trimmed.slice(0, 60),
            sourceCardId: cid,
          });
          event.dataTransfer.setData('application/x-council-card', payload);
          event.dataTransfer.effectAllowed = 'copy';
          // Show a card-shaped drag ghost
          const ghost = document.createElement('div');
          ghost.textContent = trimmed.slice(0, 80) + (trimmed.length > 80 ? '\u2026' : '');
          Object.assign(ghost.style, {
            position: 'fixed', top: '-1000px', left: '-1000px',
            width: '200px', padding: '10px 14px',
            background: '#fff', border: '1px solid #e2e8f0',
            borderTop: '2.5px solid #6366f1',
            borderRadius: '8px', fontSize: '12px', lineHeight: '1.5',
            color: '#1e293b', fontFamily: 'Inter, system-ui, sans-serif',
            boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
            overflow: 'hidden', maxHeight: '60px',
          });
          document.body.appendChild(ghost);
          event.dataTransfer.setDragImage(ghost, 100, 20);
          requestAnimationFrame(() => ghost.remove());
          // Let ProseMirror handle its own internal drag too
          return false;
        },
      },
      handleKeyDown(_view, event) {
        if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
          event.preventDefault();
          const ed = editorRef.current;
          if (ed) {
            const md = ed.storage.markdown?.getMarkdown?.() ?? ed.getText();
            callbacksRef.current.onSave?.(md);
          }
          return true;
        }
        if (event.key === 'Escape') {
          event.preventDefault();
          callbacksRef.current.onCancel?.();
          return true;
        }
        return false;
      },
      handlePaste(_view, event) {
        const items = event.clipboardData?.items;
        if (!items) return false;

        for (const item of items) {
          if (item.type.startsWith('image/')) {
            event.preventDefault();
            const file = item.getAsFile();
            if (!file || file.size > 5 * 1024 * 1024) return true;

            const reader = new FileReader();
            reader.onload = () => {
              const ed = editorRef.current;
              if (ed && reader.result) {
                ed.chain().focus().setImage({ src: reader.result }).run();
              }
            };
            reader.readAsDataURL(file);
            return true;
          }
        }
        return false;
      },
      handleDrop(_view, event) {
        const files = event.dataTransfer?.files;
        if (!files?.length) return false;

        for (const file of files) {
          if (file.type.startsWith('image/') && file.size <= 5 * 1024 * 1024) {
            event.preventDefault();
            const reader = new FileReader();
            reader.onload = () => {
              const ed = editorRef.current;
              if (ed && reader.result) {
                ed.chain().focus().setImage({ src: reader.result }).run();
              }
            };
            reader.readAsDataURL(file);
            return true;
          }
        }
        return false;
      },
    },
  });

  editorRef.current = editor;

  // Sync board cards into editor storage for card mention autocomplete
  useEffect(() => {
    if (editor && boardCards) {
      editor.storage.cardMention = { cards: boardCards };
    }
  }, [editor, boardCards]);

  // Auto-focus the editor on mount
  useEffect(() => {
    if (!editor || !autoFocus) return;

    const timer = setTimeout(() => {
      try { editor.commands.focus('end'); } catch { /* ignore */ }
    }, 50);

    return () => clearTimeout(timer);
  }, [editor, autoFocus]);

  // Listen for slash-command-input events (Image / Embed URL input)
  useEffect(() => {
    if (!editor) return;
    const dom = editor.view.dom;
    const handler = (e) => {
      const { type } = e.detail;
      setSlashInput({ type, url: '' });
      setTimeout(() => slashInputRef.current?.focus(), 0);
    };
    dom.addEventListener('slash-command-input', handler);
    return () => dom.removeEventListener('slash-command-input', handler);
  }, [editor]);

  if (initError) {
    return (
      <div className="tiptap-editor nodrag nowheel nopan" style={{ padding: 12, color: '#e74c3c', fontSize: 13 }}>
        Editor failed to load: {initError}
      </div>
    );
  }

  if (!editor) return null;

  const text = editor.getText();
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;

  return (
    <div className="tiptap-editor nodrag nowheel nopan">
      <PluginBoundary>
        <BubbleToolbar editor={editor} onExtractToCard={onExtractToCard} />
      </PluginBoundary>
      <PluginBoundary>
        <FloatingAddMenu editor={editor} />
      </PluginBoundary>
      <EditorContent editor={editor} />
      {slashInput && (
        <div className="tiptap-editor__slash-input">
          <label className="tiptap-editor__slash-input-label">
            {slashInput.type === 'image' ? 'Image URL' : 'Embed URL'}
          </label>
          <div className="tiptap-editor__slash-input-row">
            <input
              ref={slashInputRef}
              type="url"
              className="tiptap-editor__slash-input-field"
              placeholder={slashInput.type === 'image' ? 'https://example.com/image.png' : 'https://youtube.com/...'}
              value={slashInput.url}
              onChange={(e) => setSlashInput({ ...slashInput, url: e.target.value })}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  const url = slashInput.url.trim();
                  if (url) {
                    if (slashInput.type === 'image') {
                      editor.chain().focus().setImage({ src: url }).run();
                    } else {
                      editor.chain().focus().insertContent({ type: 'embed', attrs: { url } }).run();
                    }
                  }
                  setSlashInput(null);
                }
                if (e.key === 'Escape') {
                  e.preventDefault();
                  setSlashInput(null);
                  editor.chain().focus().run();
                }
              }}
            />
            <button
              type="button"
              className="tiptap-editor__slash-input-btn"
              onClick={() => {
                const url = slashInput.url.trim();
                if (url) {
                  if (slashInput.type === 'image') {
                    editor.chain().focus().setImage({ src: url }).run();
                  } else {
                    editor.chain().focus().insertContent({ type: 'embed', attrs: { url } }).run();
                  }
                }
                setSlashInput(null);
              }}
            >
              Insert
            </button>
            <button
              type="button"
              className="tiptap-editor__slash-input-btn tiptap-editor__slash-input-btn--cancel"
              onClick={() => { setSlashInput(null); editor.chain().focus().run(); }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
      <div className="tiptap-editor__footer">
        <span className="tiptap-editor__charcount">{wordCount} words</span>
        <span className="tiptap-editor__hints">
          {typeof navigator !== 'undefined' && navigator.platform?.includes('Mac')
            ? 'Cmd'
            : 'Ctrl'}
          +Enter save &middot; Esc cancel
        </span>
      </div>
    </div>
  );
}

export default memo(TiptapEditor);
