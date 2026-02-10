import { create } from 'zustand';

const MAX_HISTORY = 50;

export const useHistoryStore = create((set, get) => ({
  past: [],
  future: [],
  isUndoing: false,
  isRedoing: false,

  pushEntry: (entry) => {
    if (get().isUndoing || get().isRedoing) return;
    set((state) => ({
      past: [...state.past.slice(-(MAX_HISTORY - 1)), {
        ...entry,
        id: entry.id || crypto.randomUUID(),
        timestamp: entry.timestamp || Date.now(),
      }],
      future: [],
    }));
  },

  undo: () => {
    const { past, isUndoing, isRedoing } = get();
    if (isUndoing || isRedoing || past.length === 0) return;
    const entry = past[past.length - 1];
    set({ isUndoing: true });
    try {
      entry.undo?.();
      entry.apiUndo?.().catch(console.error);
    } catch (e) {
      console.error('Undo failed:', e);
    }
    set((state) => ({
      past: state.past.slice(0, -1),
      future: [...state.future, entry],
      isUndoing: false,
    }));
  },

  redo: () => {
    const { future, isUndoing, isRedoing } = get();
    if (isUndoing || isRedoing || future.length === 0) return;
    const entry = future[future.length - 1];
    set({ isRedoing: true });
    try {
      entry.redo?.();
      entry.apiRedo?.().catch(console.error);
    } catch (e) {
      console.error('Redo failed:', e);
    }
    set((state) => ({
      future: state.future.slice(0, -1),
      past: [...state.past, entry],
      isRedoing: false,
    }));
  },

  clearHistory: () => set({ past: [], future: [] }),
  canUndo: () => get().past.length > 0,
  canRedo: () => get().future.length > 0,
}));
