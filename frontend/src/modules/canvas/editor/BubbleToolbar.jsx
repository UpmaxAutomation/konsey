/**
 * BubbleToolbar — Floating formatting toolbar that appears on text selection.
 *
 * Uses the BubbleMenuPlugin from @tiptap/extension-bubble-menu to position
 * a toolbar element near the current selection. In tiptap v3 there is no
 * React <BubbleMenu> wrapper, so we manage the DOM element via a ref and
 * register the plugin imperatively.
 *
 * @module canvas/editor/BubbleToolbar
 */
import { useRef, useEffect, useState, useCallback } from 'react';
import { BubbleMenuPlugin } from '@tiptap/extension-bubble-menu';

/**
 * A single toolbar button.
 * @param {Object} props
 * @param {string} props.label - Button text
 * @param {boolean} props.isActive - Whether format is currently active
 * @param {function} props.onClick - Click handler
 */
function ToolbarButton({ label, isActive, onClick }) {
  return (
    <button
      type="button"
      className={`bubble-toolbar__btn${isActive ? ' bubble-toolbar__btn--active' : ''}`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

/**
 * Divider between button groups.
 */
function Divider() {
  return <span className="bubble-toolbar__divider" />;
}

/**
 * BubbleToolbar component.
 *
 * @param {Object} props
 * @param {import('@tiptap/react').Editor} props.editor - Tiptap editor instance
 * @returns {JSX.Element|null}
 */
export default function BubbleToolbar({ editor }) {
  const containerRef = useRef(null);
  // Force re-render on selection change to update active states
  const [, setTick] = useState(0);

  const forceUpdate = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!editor || !containerRef.current) return;

    // Listen for selection and transaction changes to re-render active states
    editor.on('selectionUpdate', forceUpdate);
    editor.on('transaction', forceUpdate);

    // Register the bubble menu plugin
    try {
      const plugin = BubbleMenuPlugin({
        pluginKey: 'bubbleToolbar',
        editor,
        element: containerRef.current,
        shouldShow: ({ view: _view, state }) => {
          const { empty } = state.selection;
          return !empty && editor.isEditable;
        },
      });

      editor.registerPlugin(plugin);
    } catch (err) {
      console.warn('BubbleToolbar plugin registration failed:', err);
    }

    return () => {
      editor.off('selectionUpdate', forceUpdate);
      editor.off('transaction', forceUpdate);
      try { editor.unregisterPlugin('bubbleToolbar'); } catch { /* already gone */ }
    };
  }, [editor, forceUpdate]);

  if (!editor) return null;

  return (
    <div
      ref={containerRef}
      className="bubble-toolbar"
      style={{ visibility: 'hidden', position: 'absolute' }}
    >
      {/* Inline formatting */}
      <ToolbarButton
        label="B"
        isActive={editor.isActive('bold')}
        onClick={() => editor.chain().focus().toggleBold().run()}
      />
      <ToolbarButton
        label="I"
        isActive={editor.isActive('italic')}
        onClick={() => editor.chain().focus().toggleItalic().run()}
      />
      <ToolbarButton
        label="S"
        isActive={editor.isActive('strike')}
        onClick={() => editor.chain().focus().toggleStrike().run()}
      />
      <ToolbarButton
        label="Code"
        isActive={editor.isActive('code')}
        onClick={() => editor.chain().focus().toggleCode().run()}
      />
      <ToolbarButton
        label="Hi"
        isActive={editor.isActive('highlight')}
        onClick={() => editor.chain().focus().toggleHighlight().run()}
      />

      <Divider />

      {/* Headings */}
      <ToolbarButton
        label="H1"
        isActive={editor.isActive('heading', { level: 1 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
      />
      <ToolbarButton
        label="H2"
        isActive={editor.isActive('heading', { level: 2 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
      />
      <ToolbarButton
        label="H3"
        isActive={editor.isActive('heading', { level: 3 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
      />

      <Divider />

      {/* Block formatting */}
      <ToolbarButton
        label="List"
        isActive={editor.isActive('bulletList')}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
      />
      <ToolbarButton
        label="1."
        isActive={editor.isActive('orderedList')}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
      />
      <ToolbarButton
        label={'"'}
        isActive={editor.isActive('blockquote')}
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
      />
      <ToolbarButton
        label="<>"
        isActive={editor.isActive('codeBlock')}
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
      />
    </div>
  );
}
