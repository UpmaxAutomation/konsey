import { create } from 'zustand';

const useCollaborationStore = create((set, get) => ({
  ws: null,
  connected: false,
  boardId: null,
  boardUsers: [],
  remoteCursors: {},
  reconnectAttempts: 0,
  maxReconnectAttempts: 10,

  connect: (boardId, token) => {
    const state = get();
    if (state.ws && state.connected && state.boardId === boardId) return;

    // Close existing
    if (state.ws) {
      try { state.ws.close(); } catch (e) {}
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.VITE_API_URL
      ? new URL(import.meta.env.VITE_API_URL).host
      : 'localhost:8001';
    const url = `${protocol}//${host}/ws/boards/${boardId}?token=${token}`;

    const ws = new WebSocket(url);

    ws.onopen = () => {
      set({ connected: true, reconnectAttempts: 0 });
    };

    ws.onclose = () => {
      set({ connected: false, ws: null });
      // Auto-reconnect with exponential backoff
      const attempts = get().reconnectAttempts;
      if (attempts < get().maxReconnectAttempts && get().boardId) {
        const delay = Math.min(1000 * Math.pow(2, attempts), 30000);
        setTimeout(() => {
          set({ reconnectAttempts: attempts + 1 });
          const currentToken = localStorage.getItem('auth_token');
          if (currentToken && get().boardId) {
            get().connect(get().boardId, currentToken);
          }
        }, delay);
      }
    };

    ws.onerror = () => {};

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        get()._handleMessage(message);
      } catch (e) {}
    };

    set({ ws, boardId });
  },

  disconnect: () => {
    const { ws } = get();
    if (ws) {
      try { ws.close(); } catch (e) {}
    }
    set({
      ws: null,
      connected: false,
      boardId: null,
      boardUsers: [],
      remoteCursors: {},
      reconnectAttempts: get().maxReconnectAttempts, // prevent reconnect
    });
  },

  sendCursorMove: (x, y) => {
    const { ws, connected } = get();
    if (ws && connected) {
      try {
        ws.send(JSON.stringify({ type: 'cursor_move', x, y }));
      } catch (e) {}
    }
  },

  sendPing: () => {
    const { ws, connected } = get();
    if (ws && connected) {
      try { ws.send(JSON.stringify({ type: 'ping' })); } catch (e) {}
    }
  },

  // Internal message handler
  _handleMessage: (message) => {
    switch (message.type) {
      case 'presence_sync':
        set({ boardUsers: message.users || [] });
        break;
      case 'user_joined':
        set({ boardUsers: message.users || get().boardUsers });
        break;
      case 'user_left':
        set((state) => ({
          boardUsers: message.users || state.boardUsers,
          remoteCursors: (() => {
            const c = { ...state.remoteCursors };
            delete c[message.user_id];
            return c;
          })(),
        }));
        break;
      case 'cursor_move':
        set((state) => ({
          remoteCursors: {
            ...state.remoteCursors,
            [message.user_id]: {
              x: message.x,
              y: message.y,
              name: message.name,
              color: message.color,
            },
          },
        }));
        break;
      case 'pong':
        break;
      default:
        // Relay to any registered event listeners
        if (get()._onRemoteEvent) {
          get()._onRemoteEvent(message);
        }
        break;
    }
  },

  _onRemoteEvent: null,
  setOnRemoteEvent: (handler) => set({ _onRemoteEvent: handler }),
}));

export { useCollaborationStore };
