import { useState, useCallback, useRef, memo } from 'react';
import { NodeResizer, Handle, Position, useStore } from '@xyflow/react';
import ColorPicker from './ColorPicker';
import '../styles/SectionNode.css';

const SECTION_COLORS = {
  gray: { bg: 'var(--section-gray-bg)', border: 'var(--card-gray)' },
  red: { bg: 'var(--section-red-bg)', border: 'var(--card-red)' },
  orange: { bg: 'var(--section-orange-bg)', border: 'var(--card-orange)' },
  yellow: { bg: 'var(--section-yellow-bg)', border: 'var(--card-yellow)' },
  green: { bg: 'var(--section-green-bg)', border: 'var(--card-green)' },
  blue: { bg: 'var(--section-blue-bg)', border: 'var(--card-blue)' },
  purple: { bg: 'var(--section-purple-bg)', border: 'var(--card-purple)' },
  pink: { bg: 'var(--section-pink-bg)', border: 'var(--card-pink)' },
};

/**
 * SectionNode - A ReactFlow group node that renders as a colored section rectangle.
 * Supports inline title editing, color picking, resizing, and deletion.
 * @param {{ data: object, selected: boolean }} props
 */
function SectionNode({ data, selected }) {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitle, setEditTitle] = useState(data.title || '');
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const inputRef = useRef(null);

  // Zoom-aware title scaling
  const zoom = useStore((s) => s.transform[2]);
  const titleFontSize = Math.min(48, Math.max(12, 14 / zoom));

  const colors = SECTION_COLORS[data.color] || SECTION_COLORS.gray;

  const handleToggleCollapse = useCallback(() => {
    const next = !collapsed;
    setCollapsed(next);
    data.onToggleCollapse?.(data.sectionId, next);
  }, [collapsed, data]);

  const handleTitleSave = useCallback(() => {
    setIsEditingTitle(false);
    if (editTitle.trim() !== data.title) {
      data.onUpdateSection?.(data.sectionId, { title: editTitle.trim() });
    }
  }, [editTitle, data]);

  const handleColorChange = useCallback((color) => {
    setShowColorPicker(false);
    data.onUpdateSection?.(data.sectionId, { color });
  }, [data]);

  const handleDelete = useCallback(() => {
    data.onDeleteSection?.(data.sectionId);
  }, [data]);

  const handleUngroup = useCallback(() => {
    data.onUngroupSection?.(data.sectionId);
  }, [data]);

  const childCount = data.childCount || 0;

  return (
    <div
      className={`section-node ${selected ? 'section-node--selected' : ''} ${collapsed ? 'section-node--collapsed' : ''}`}
      style={{
        background: colors.bg,
        borderColor: colors.border,
        width: '100%',
        height: '100%',
      }}
    >
      <Handle type="source" position={Position.Top} id="top" className="section-node__handle" />
      <Handle type="target" position={Position.Top} id="top" className="section-node__handle" />
      <Handle type="source" position={Position.Left} id="left" className="section-node__handle" />
      <Handle type="target" position={Position.Left} id="left" className="section-node__handle" />
      <Handle type="source" position={Position.Right} id="right" className="section-node__handle" />
      <Handle type="target" position={Position.Right} id="right" className="section-node__handle" />

      <NodeResizer
        minWidth={300}
        minHeight={collapsed ? 44 : 200}
        isVisible={selected && !collapsed}
        lineClassName="section-node__resize-line"
        handleClassName="section-node__resize-handle"
        onResize={(_, params) => {
          data.onUpdateSection?.(data.sectionId, {
            width: params.width,
            height: params.height,
          });
        }}
      />
      <div className="section-node__header">
        <button
          className="section-node__collapse-toggle"
          onClick={(e) => {
            e.stopPropagation();
            handleToggleCollapse();
          }}
          title={collapsed ? 'Expand section' : 'Collapse section'}
          aria-label={collapsed ? 'Expand section' : 'Collapse section'}
        >
          {collapsed ? '\u25B6' : '\u25BC'}
        </button>
        <div
          className="section-node__color-dot"
          style={{ background: colors.border }}
          onClick={(e) => {
            e.stopPropagation();
            setShowColorPicker(!showColorPicker);
          }}
          role="button"
          tabIndex={0}
          aria-label="Change section color"
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              e.stopPropagation();
              setShowColorPicker(!showColorPicker);
            }
          }}
        />
        {isEditingTitle ? (
          <input
            ref={inputRef}
            className="section-node__title-input"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onBlur={handleTitleSave}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleTitleSave();
              if (e.key === 'Escape') {
                setIsEditingTitle(false);
                setEditTitle(data.title || '');
              }
            }}
            autoFocus
            onClick={(e) => e.stopPropagation()}
            aria-label="Section title"
          />
        ) : (
          <span
            className="section-node__title"
            style={{ fontSize: `${titleFontSize}px` }}
            onDoubleClick={(e) => {
              e.stopPropagation();
              setIsEditingTitle(true);
              setEditTitle(data.title || '');
            }}
          >
            {data.title || 'Untitled Section'}
          </span>
        )}
        {childCount > 0 && (
          <span className="section-node__card-count">
            {childCount} {childCount === 1 ? 'card' : 'cards'}
          </span>
        )}
        <button
          className="section-node__ungroup"
          onClick={(e) => {
            e.stopPropagation();
            handleUngroup();
          }}
          title="Ungroup cards"
          aria-label="Ungroup cards from section"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 13h-5" /><path d="M10 13H5" /><path d="M21 8a5 5 0 0 0-5-5h-1a5 5 0 0 0-5 5" /><path d="M3 16a5 5 0 0 0 5 5h1a5 5 0 0 0 5-5" />
          </svg>
        </button>
        <button
          className="section-node__delete"
          onClick={(e) => {
            e.stopPropagation();
            handleDelete();
          }}
          title="Delete section"
          aria-label="Delete section"
        >
          &times;
        </button>
      </div>
      {showColorPicker && (
        <div
          className="section-node__color-picker"
          onClick={(e) => e.stopPropagation()}
        >
          <ColorPicker selected={data.color} onSelect={handleColorChange} />
        </div>
      )}

      <Handle type="source" position={Position.Bottom} id="bottom" className="section-node__handle" />
      <Handle type="target" position={Position.Bottom} id="bottom" className="section-node__handle" />
    </div>
  );
}

export default memo(SectionNode, (prev, next) =>
  prev.data === next.data && prev.selected === next.selected
);
export { SECTION_COLORS };
