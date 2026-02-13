import { memo, useState, useCallback, useRef, useEffect } from 'react';
import { getBezierPath, getStraightPath, getSmoothStepPath, EdgeLabelRenderer } from '@xyflow/react';

function AnimatedEdge({
  id, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, data, markerEnd, markerStart, label, selected,
}) {
  const [editing, setEditing] = useState(false);
  const [labelValue, setLabelValue] = useState(label || '');
  const inputRef = useRef(null);

  // Sync external label prop changes
  useEffect(() => {
    if (!editing) setLabelValue(label || '');
  }, [label, editing]);

  const cfg = data?.style || {};
  const pathType = cfg.pathType || 'bezier';

  // Compute path based on pathType
  let edgePath, labelX, labelY;
  const pathParams = { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition };
  if (pathType === 'straight') {
    [edgePath, labelX, labelY] = getStraightPath(pathParams);
  } else if (pathType === 'step') {
    [edgePath, labelX, labelY] = getSmoothStepPath(pathParams);
  } else {
    [edgePath, labelX, labelY] = getBezierPath(pathParams);
  }

  const classNames = [
    'animated-edge',
    cfg.animated ? 'animated-edge--flowing' : '',
    cfg.dashed ? 'animated-edge--dashed' : '',
    selected ? 'animated-edge--selected' : '',
  ].filter(Boolean).join(' ');

  const handleDoubleClick = useCallback((e) => {
    e.stopPropagation();
    setEditing(true);
  }, []);

  const commitLabel = useCallback(() => {
    setEditing(false);
    const newLabel = labelValue.trim();
    if (data?.onUpdateEdge) {
      // Clear the editingLabel flag
      if (data.editingLabel) {
        data.onUpdateEdge(data.edgeId, { label: newLabel || null });
      } else if (newLabel !== (label || '')) {
        data.onUpdateEdge(data.edgeId, { label: newLabel || null });
      }
    }
  }, [labelValue, label, data]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      commitLabel();
    } else if (e.key === 'Escape') {
      setEditing(false);
      setLabelValue(label || '');
    }
  }, [commitLabel, label]);

  // Auto-enter editing when triggered from context menu
  useEffect(() => {
    if (data?.editingLabel && !editing) {
      setEditing(true);
    }
  }, [data?.editingLabel, editing]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  return (
    <>
      {/* Invisible wider hit area for easier hover/selection */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        className="react-flow__edge-interaction"
      />
      <path
        id={id}
        className={classNames}
        d={edgePath}
        fill="none"
        stroke={cfg.stroke || '#cbd5e1'}
        strokeWidth={cfg.strokeWidth || 1}
        markerEnd={markerEnd}
        markerStart={markerStart}
      />
      <EdgeLabelRenderer>
        <div
          className="animated-edge__label-wrapper"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
          }}
          onDoubleClick={handleDoubleClick}
        >
          {editing ? (
            <input
              ref={inputRef}
              className="animated-edge__label-input"
              value={labelValue}
              onChange={(e) => setLabelValue(e.target.value)}
              onBlur={commitLabel}
              onKeyDown={handleKeyDown}
              placeholder="Label..."
            />
          ) : (
            (label || labelValue) && (
              <div className="animated-edge__label">
                {label || labelValue}
              </div>
            )
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

export default memo(AnimatedEdge);
