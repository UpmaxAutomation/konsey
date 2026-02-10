import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useCollaborationStore } from '../../../stores/collaborationStore';

export default function useCollaboration(boardId) {
  const queryClient = useQueryClient();
  const { connect, disconnect, sendCursorMove, sendPing, setOnRemoteEvent, connected, boardUsers, remoteCursors } = useCollaborationStore();
  const cursorThrottleRef = useRef(null);
  const pingIntervalRef = useRef(null);

  useEffect(() => {
    if (!boardId) return;
    const token = localStorage.getItem('auth_token');
    if (!token) return;

    connect(boardId, token);

    // Ping heartbeat every 5s
    pingIntervalRef.current = setInterval(() => {
      sendPing();
    }, 5000);

    return () => {
      disconnect();
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
    };
  }, [boardId]);

  // Handle remote mutation events -> invalidate React Query cache
  useEffect(() => {
    setOnRemoteEvent((event) => {
      const eventType = event.type;
      if (['card_created', 'card_updated', 'card_deleted',
           'edge_created', 'edge_deleted', 'section_updated',
           'board_changed'].includes(eventType)) {
        queryClient.invalidateQueries({ queryKey: ['board', boardId] });
      }
    });
    return () => setOnRemoteEvent(null);
  }, [boardId, queryClient, setOnRemoteEvent]);

  // Throttled cursor broadcast (50ms)
  const handleMouseMove = useCallback((e, viewport) => {
    if (cursorThrottleRef.current) return;
    cursorThrottleRef.current = requestAnimationFrame(() => {
      cursorThrottleRef.current = null;
      if (viewport) {
        const x = (e.clientX - viewport.x) / viewport.zoom;
        const y = (e.clientY - viewport.y) / viewport.zoom;
        sendCursorMove(x, y);
      }
    });
  }, [sendCursorMove]);

  return { connected, boardUsers, remoteCursors, handleMouseMove };
}
