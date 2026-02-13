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
 * @param {string} [props.title] - Tooltip text
 */
function ToolbarButton({ label, isActive, onClick, title }) {
  return (
    <button
      type="button"
      className={`bubble-toolbar__btn${isActive ? ' bubble-toolbar__btn--active' : ''}`}
      onClick={onClick}
      title={title}
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
 * "Turn Into" block conversion dropdown.
 */
function TurnIntoMenu({ editor, isOpen, onToggle }) {
  const menuRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        onToggle(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onToggle]);

  const options = [
    { label: 'Paragraph', action: () => editor.chain().focus().setParagraph().run() },
    { label: 'H1', action: () => editor.chain().focus().toggleHeading({ level: 1 }).run() },
    { label: 'H2', action: () => editor.chain().focus().toggleHeading({ level: 2 }).run() },
    { label: 'H3', action: () => editor.chain().focus().toggleHeading({ level: 3 }).run() },
    { label: 'Bullet List', action: () => editor.chain().focus().toggleBulletList().run() },
    { label: 'Numbered List', action: () => editor.chain().focus().toggleOrderedList().run() },
    { label: 'Task List', action: () => editor.chain().focus().toggleTaskList().run() },
    { label: 'Blockquote', action: () => editor.chain().focus().toggleBlockquote().run() },
    { label: 'Code Block', action: () => editor.chain().focus().toggleCodeBlock().run() },
    { label: 'Toggle', action: () => editor.chain().focus().toggleToggle().run() },
  ];

  return (
    <div ref={menuRef} style={{ position: 'relative', display: 'inline-flex' }}>
      <ToolbarButton
        label="Turn Into"
        isActive={isOpen}
        onClick={() => onToggle(!isOpen)}
        title="Convert block type"
      />
      {isOpen && (
        <div className="bubble-toolbar__turninto-dropdown">
          {options.map((opt) => (
            <button
              key={opt.label}
              type="button"
              className="bubble-toolbar__turninto-option"
              onClick={() => {
                opt.action();
                onToggle(false);
              }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * BubbleToolbar component.
 *
 * @param {Object} props
 * @param {import('@tiptap/react').Editor} props.editor - Tiptap editor instance
 * @returns {JSX.Element|null}
 */
export default function BubbleToolbar({ editor, onAttachFile, onInsertImage, onInsertEmbed, onExtractToCard }) {
  const containerRef = useRef(null);
  // Force re-render on selection change to update active states
  const [, setTick] = useState(0);
  const [turnIntoOpen, setTurnIntoOpen] = useState(false);
  const [linkInput, setLinkInput] = useState(null); // { url: string } when open
  const linkInputRef = useRef(null);

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

  const handleInsertTable = () => {
    editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run();
  };

  const handleInsertLink = () => {
    const previousUrl = editor.getAttributes('link').href || '';
    setLinkInput({ url: previousUrl });
    // Focus the input after React renders it
    setTimeout(() => linkInputRef.current?.focus(), 0);
  };

  const handleLinkSubmit = () => {
    if (!linkInput) return;
    const url = linkInput.url.trim();
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
    } else {
      editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
    }
    setLinkInput(null);
  };

  const handleLinkCancel = () => {
    setLinkInput(null);
    editor.chain().focus().run();
  };

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

      <Divider />

      {/* Table insert */}
      <ToolbarButton
        label={'\u25A6'}
        isActive={editor.isActive('table')}
        onClick={handleInsertTable}
        title="Insert 3x3 table"
      />
      {/* Toggle block */}
      <ToolbarButton
        label={'\u25B6'}
        isActive={editor.isActive('toggleBlock')}
        onClick={() => editor.chain().focus().toggleToggle().run()}
        title="Toggle block"
      />
      {/* Link */}
      <ToolbarButton
        label={'\uD83D\uDD17'}
        isActive={editor.isActive('link')}
        onClick={handleInsertLink}
        title="Insert link"
      />

      {(onAttachFile || onInsertImage || onInsertEmbed || onExtractToCard) && (
        <>
          <Divider />
          {onAttachFile && <ToolbarButton label={'\uD83D\uDCCE'} isActive={false} onClick={onAttachFile} />}
          {onInsertImage && <ToolbarButton label={'\uD83D\uDDBC'} isActive={false} onClick={onInsertImage} />}
          {onInsertEmbed && <ToolbarButton label={'\uD83D\uDD17'} isActive={false} onClick={onInsertEmbed} />}
          {onExtractToCard && (
            <ToolbarButton
              label={'\u2702'}
              isActive={false}
              onClick={() => {
                const { from, to } = editor.state.selection;
                const text = editor.state.doc.textBetween(from, to, '\n');
                if (text.trim()) onExtractToCard(text.trim());
              }}
            />
          )}
        </>
      )}

      <Divider />

      {/* Turn Into block conversion menu */}
      <TurnIntoMenu
        editor={editor}
        isOpen={turnIntoOpen}
        onToggle={setTurnIntoOpen}
      />

      {/* Inline link URL input */}
      {linkInput !== null && (
        <div className="bubble-toolbar__link-input">
          <input
            ref={linkInputRef}
            type="url"
            className="bubble-toolbar__link-input-field"
            placeholder="https://..."
            value={linkInput.url}
            onChange={(e) => setLinkInput({ url: e.target.value })}
            onKeyDown={(e) => {
              if (e.key === 'Enter') { e.preventDefault(); handleLinkSubmit(); }
              if (e.key === 'Escape') { e.preventDefault(); handleLinkCancel(); }
            }}
          />
          <button type="button" className="bubble-toolbar__link-input-btn" onClick={handleLinkSubmit}>
            Apply
          </button>
          <button type="button" className="bubble-toolbar__link-input-btn bubble-toolbar__link-input-btn--cancel" onClick={handleLinkCancel}>
            &times;
          </button>
        </div>
      )}
    </div>
  );
}
