import { memo } from 'react';
import { getBezierPath, EdgeLabelRenderer } from '@xyflow/react';

function AnimatedEdge({
  id, sourceX, sourceY, targetX, targetY,
  sourcePosition, targetPosition, data, markerEnd, label,
}) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition,
  });

  const cfg = data?.style || {};
  const classNames = [
    'animated-edge',
    cfg.animated ? 'animated-edge--flowing' : '',
    cfg.dashed ? 'animated-edge--dashed' : '',
  ].filter(Boolean).join(' ');

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
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            className="animated-edge__label"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export default memo(AnimatedEdge);
