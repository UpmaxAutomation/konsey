/**
 * FloatingAddMenu — "+" button that appears on empty lines.
 * Opens a compact block menu for inserting headings, lists, code, etc.
 *
 * Uses the FloatingMenuPlugin from @tiptap/extension-floating-menu
 * imperatively (same pattern as BubbleToolbar) since tiptap v3
 * does not ship a React wrapper component.
 *
 * @module canvas/editor/FloatingAddMenu
 */
import { useRef, useEffect, useState } from 'react';
import { FloatingMenuPlugin } from '@tiptap/extension-floating-menu';
import './FloatingAddMenu.css';

/** Block-type actions available from the floating menu. */
const BLOCKS = [
  { label: 'H1', action: (ed) => ed.chain().focus().toggleHeading({ level: 1 }).run() },
  { label: 'H2', action: (ed) => ed.chain().focus().toggleHeading({ level: 2 }).run() },
  { label: '\u2022', action: (ed) => ed.chain().focus().toggleBulletList().run() },
  { label: '\u2610', action: (ed) => ed.chain().focus().toggleTaskList().run() },
  { label: '<>', action: (ed) => ed.chain().focus().toggleCodeBlock().run() },
  { label: '\u201C', action: (ed) => ed.chain().focus().toggleBlockquote().run() },
  { label: '\u2014', action: (ed) => ed.chain().focus().setHorizontalRule().run() },
];

/**
 * FloatingAddMenu component.
 *
 * @param {Object} props
 * @param {import('@tiptap/react').Editor} props.editor - Tiptap editor instance
 * @returns {JSX.Element|null}
 */
export default function FloatingAddMenu({ editor }) {
  const containerRef = useRef(null);
  const [expanded, setExpanded] = useState(false);

  // Register the floating menu plugin imperatively
  useEffect(() => {
    if (!editor || !containerRef.current) return;

    try {
      const plugin = FloatingMenuPlugin({
        pluginKey: 'floatingAddMenu',
        editor,
        element: containerRef.current,
        shouldShow: ({ state }) => {
          const { $from } = state.selection;
          const isEmptyParagraph =
            $from.parent.type.name === 'paragraph' &&
            $from.parent.textContent === '' &&
            editor.isEditable;
          return isEmptyParagraph;
        },
      });

      editor.registerPlugin(plugin);
    } catch (err) {
      console.warn('FloatingAddMenu plugin registration failed:', err);
    }

    return () => {
      try { editor.unregisterPlugin('floatingAddMenu'); } catch { /* already gone */ }
    };
  }, [editor]);

  // Close the block palette whenever the editor content changes
  useEffect(() => {
    if (!editor) return;
    const close = () => setExpanded(false);
    editor.on('update', close);
    return () => editor.off('update', close);
  }, [editor]);

  if (!editor) return null;

  return (
    <div
      ref={containerRef}
      className={`floating-add-menu${expanded ? ' floating-add-menu--expanded' : ''}`}
      style={{ visibility: 'hidden', position: 'absolute' }}
    >
      <button
        type="button"
        className="floating-add-menu__trigger"
        onClick={(e) => {
          e.preventDefault();
          setExpanded(!expanded);
        }}
        aria-label="Add block"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          aria-hidden="true"
        >
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>

      {expanded && (
        <div className="floating-add-menu__blocks" role="toolbar" aria-label="Block types">
          {BLOCKS.map((b) => (
            <button
              key={b.label}
              type="button"
              className="floating-add-menu__block-btn"
              onClick={() => {
                b.action(editor);
                setExpanded(false);
              }}
            >
              {b.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
