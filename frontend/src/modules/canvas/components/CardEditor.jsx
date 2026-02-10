import { useState, useRef, useEffect, useCallback, lazy, Suspense, Component } from 'react';
import useAutoSave from '../editor/useAutoSave';

const LazyTiptapEditor = lazy(() =>
  import('../editor').then((mod) => ({ default: mod.default }))
);

const PLACEHOLDERS = {
  note: 'Write your note...',
  link: 'URL or description...',
  knowledge: 'Knowledge content...',
};

function FallbackTextarea({ content, placeholder, onSave, onCancel, onContentChange }) {
  const [text, setText] = useState(content || '');
  return (
    <textarea
      className="card-editor__content nodrag nowheel"
      value={text}
      placeholder={placeholder}
      onChange={(e) => {
        setText(e.target.value);
        onContentChange?.(e.target.value);
      }}
      onKeyDown={(e) => {
        e.stopPropagation();
        if (e.key === 'Escape') onCancel?.();
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') onSave?.(text);
      }}
      autoFocus
    />
  );
}

export default function CardEditor({ title, content, onSave, onAutoSave, onCancel, cardType, boardCards = [] }) {
  const [editTitle, setEditTitle] = useState(title);
  const [tiptapFailed, setTiptapFailed] = useState(false);
  const contentRef = useRef(content);
  const titleRef = useRef(null);
  const editorRef = useRef(null);

  const editTitleRef = useRef(editTitle);
  editTitleRef.current = editTitle;

  const { status: saveStatus, scheduleAutoSave, flush } = useAutoSave(onAutoSave || onSave);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (titleRef.current) {
        titleRef.current.focus();
        titleRef.current.select();
      }
    }, 150);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    scheduleAutoSave(editTitle, contentRef.current);
  }, [editTitle, scheduleAutoSave]);

  const save = useCallback(() => {
    flush();
    onSave(editTitle, contentRef.current);
  }, [onSave, editTitle, flush]);

  const placeholder = PLACEHOLDERS[cardType] || 'Content...';

  const handleContentChange = useCallback((md) => {
    contentRef.current = md;
    scheduleAutoSave(editTitleRef.current, md);
  }, [scheduleAutoSave]);

  return (
    <div
      className="card-editor nodrag nowheel nopan"
      ref={editorRef}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
    >
      <input
        ref={titleRef}
        className="card-editor__title nodrag nowheel"
        value={editTitle}
        onChange={(e) => setEditTitle(e.target.value)}
        placeholder="Title"
        onKeyDown={(e) => {
          e.stopPropagation();
          if (e.key === 'Escape') { flush(); onCancel(); }
          if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { save(); }
        }}
      />
      {tiptapFailed ? (
        <FallbackTextarea
          content={content}
          placeholder={placeholder}
          onSave={(md) => { flush(); onSave(editTitle, md); }}
          onCancel={() => { flush(); onCancel(); }}
          onContentChange={handleContentChange}
        />
      ) : (
        <Suspense fallback={<div style={{ padding: '10px 16px', fontSize: 12, color: 'var(--text-muted)' }}>Loading editor...</div>}>
          <TiptapErrorBoundary onError={() => setTiptapFailed(true)}>
            <LazyTiptapEditor
              content={content}
              placeholder={placeholder}
              onSave={(md) => { flush(); onSave(editTitle, md); }}
              onCancel={() => { flush(); onCancel(); }}
              onContentChange={handleContentChange}
              autoFocus={false}
              boardCards={boardCards}
            />
          </TiptapErrorBoundary>
        </Suspense>
      )}
      {saveStatus !== 'idle' && (
        <div
          className={`card-editor__save-status card-editor__save-status--${saveStatus}`}
          aria-live="polite"
        >
          {saveStatus === 'saving' && 'Saving...'}
          {saveStatus === 'saved' && 'Saved'}
          {saveStatus === 'error' && 'Save failed'}
        </div>
      )}
    </div>
  );
}

class TiptapErrorBoundary extends Component {
  state = { hasError: false };
  static getDerivedStateFromError() { return { hasError: true }; }
  componentDidCatch(err) {
    console.error('TiptapEditor failed to load:', err);
    this.props.onError?.();
  }
  render() {
    if (this.state.hasError) return null;
    return this.props.children;
  }
}
