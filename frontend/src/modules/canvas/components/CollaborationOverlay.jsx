import '../styles/CollaborationOverlay.css';

export default function CollaborationOverlay({ remoteCursors, viewport }) {
  if (!viewport) return null;

  return (
    <div className="collaboration-overlay">
      {Object.entries(remoteCursors).map(([userId, cursor]) => {
        const screenX = cursor.x * viewport.zoom + viewport.x;
        const screenY = cursor.y * viewport.zoom + viewport.y;

        return (
          <div
            key={userId}
            className="collaboration-cursor"
            style={{
              transform: `translate(${screenX}px, ${screenY}px)`,
              '--cursor-color': cursor.color || '#4a90e2',
            }}
          >
            <svg width="16" height="20" viewBox="0 0 16 20" fill="none">
              <path
                d="M0 0L16 12L8 12L4 20L0 0Z"
                fill={cursor.color || '#4a90e2'}
                stroke="white"
                strokeWidth="1"
              />
            </svg>
            <span className="collaboration-cursor__label" style={{ backgroundColor: cursor.color || '#4a90e2' }}>
              {cursor.name || 'User'}
            </span>
          </div>
        );
      })}
    </div>
  );
}
