import { create } from 'zustand';

/**
 * Board state store.
 *
 * Manages the list of boards (which may form a tree via parent_board_id),
 * the currently-active board, and the sections that belong to it.
 */
const useBoardStore = create((set, get) => ({
  // ---- state ----
  boards: [],
  currentBoardId: null,
  sections: [],

  // ---- board actions ----

  /** Replace the entire boards array. */
  setBoards: (boards) => set({ boards }),

  /** Append a single board. */
  addBoard: (board) =>
    set((state) => ({ boards: [...state.boards, board] })),

  /** Remove a board by id. If the removed board was active, clear selection. */
  removeBoard: (boardId) =>
    set((state) => ({
      boards: state.boards.filter((b) => b.id !== boardId),
      currentBoardId:
        state.currentBoardId === boardId ? null : state.currentBoardId,
      sections: state.currentBoardId === boardId ? [] : state.sections,
    })),

  /** Shallow-merge updated fields into an existing board. */
  updateBoard: (boardId, updates) =>
    set((state) => ({
      boards: state.boards.map((b) =>
        b.id === boardId ? { ...b, ...updates } : b
      ),
    })),

  /** Set the active board id. */
  setCurrentBoard: (boardId) => set({ currentBoardId: boardId }),

  // ---- section actions ----

  /** Replace all sections for the current board. */
  setSections: (sections) => set({ sections }),

  /** Append a section to the current board. */
  addSection: (section) =>
    set((state) => ({ sections: [...state.sections, section] })),

  /** Shallow-merge updated fields into an existing section. */
  updateSection: (sectionId, updates) =>
    set((state) => ({
      sections: state.sections.map((s) =>
        s.id === sectionId ? { ...s, ...updates } : s
      ),
    })),

  /** Remove a section by id. */
  removeSection: (sectionId) =>
    set((state) => ({
      sections: state.sections.filter((s) => s.id !== sectionId),
    })),

  // ---- derived helpers ----

  /** Return the currently-active board object (or null). */
  getCurrentBoard: () => {
    const { boards, currentBoardId } = get();
    return boards.find((b) => b.id === currentBoardId) ?? null;
  },

  /** Return direct children of a given parent board. */
  getChildBoards: (parentId) => {
    const { boards } = get();
    return boards.filter((b) => b.parent_board_id === parentId);
  },

  /** Return top-level boards (no parent). */
  getRootBoards: () => {
    const { boards } = get();
    return boards.filter((b) => !b.parent_board_id);
  },
}));

export { useBoardStore };
export default useBoardStore;
