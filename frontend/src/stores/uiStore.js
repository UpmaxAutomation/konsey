import { create } from 'zustand';

/**
 * UI state store.
 *
 * Holds ephemeral interface state such as the active sidebar tab,
 * open editor tabs, command palette visibility, and the right panel.
 */
const useUiStore = create((set, get) => ({
  // ---- state ----
  sidebarTab: 'boards', // 'boards' | 'chat' | 'cardLibrary' | 'journal' | 'inbox'
  showCommandPalette: false,
  openTabs: [], // Array of { type, id, title }
  activeTabId: null,
  rightPanel: null, // null | 'journal' | 'inbox' | 'cardInfo'

  // ---- actions ----

  /** Switch the sidebar to a specific tab. */
  setSidebarTab: (tab) => set({ sidebarTab: tab }),

  /**
   * Open a tab. If a tab with the same id already exists it is activated
   * instead of duplicated.
   */
  openTab: (tab) =>
    set((state) => {
      const exists = state.openTabs.some((t) => t.id === tab.id);
      if (exists) {
        return { activeTabId: tab.id };
      }
      return {
        openTabs: [...state.openTabs, tab],
        activeTabId: tab.id,
      };
    }),

  /** Close a tab by id. If the closed tab was active, activate the previous tab. */
  closeTab: (tabId) =>
    set((state) => {
      const idx = state.openTabs.findIndex((t) => t.id === tabId);
      const nextTabs = state.openTabs.filter((t) => t.id !== tabId);

      let nextActiveId = state.activeTabId;
      if (state.activeTabId === tabId) {
        const fallback = nextTabs[Math.min(idx, nextTabs.length - 1)];
        nextActiveId = fallback ? fallback.id : null;
      }

      return { openTabs: nextTabs, activeTabId: nextActiveId };
    }),

  /** Activate an existing tab by id. */
  setActiveTab: (tabId) => set({ activeTabId: tabId }),

  /** Toggle the command palette open/closed. */
  toggleCommandPalette: () =>
    set((state) => ({ showCommandPalette: !state.showCommandPalette })),

  /** Set which right-side panel is visible (or null to hide). */
  setRightPanel: (panel) => set({ rightPanel: panel }),
}));

export { useUiStore };
export default useUiStore;
