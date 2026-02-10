/**
 * TiptapEditor — Rich text editor wrapping Tiptap for canvas card editing.
 *
 * Renders an inline WYSIWYG editor with markdown I/O, a floating
 * BubbleToolbar for formatting, and keyboard shortcuts for save/cancel.
 *
 * @module canvas/editor/TiptapEditor
 */
import { useEffect, useRef, useState, Component } from 'react';
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
export default function TiptapEditor({
  content,
  onSave,
  onCancel,
  onContentChange,
  placeholder = 'Start writing...',
  autoFocus = true,
  boardCards = [],
}) {
  // Keep latest callbacks in refs to avoid stale closures inside editorProps
  const callbacksRef = useRef({ onSave, onCancel, onContentChange });
  callbacksRef.current = { onSave, onCancel, onContentChange };

  // Ref to hold the editor instance for use inside editorProps.handleKeyDown
  const editorRef = useRef(null);
  const [initError, setInitError] = useState(null);

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

  // Auto-focus the editor on mount
  useEffect(() => {
    if (!editor || !autoFocus) return;

    const timer = setTimeout(() => {
      try { editor.commands.focus('end'); } catch { /* ignore */ }
    }, 50);

    return () => clearTimeout(timer);
  }, [editor, autoFocus]);

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
        <BubbleToolbar editor={editor} />
      </PluginBoundary>
      <PluginBoundary>
        <FloatingAddMenu editor={editor} />
      </PluginBoundary>
      <EditorContent editor={editor} />
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
