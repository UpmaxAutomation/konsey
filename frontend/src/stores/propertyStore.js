import { create } from 'zustand';

/**
 * Property/view state store.
 *
 * Manages the active board view (canvas/table/kanban),
 * selected card for property editing, and view-specific settings.
 */
const usePropertyStore = create((set) => ({
  // ---- state ----
  activeView: 'canvas', // 'canvas' | 'table' | 'kanban'
  selectedCardId: null,
  kanbanGroupByPropertyId: null,
  tableSortColumn: null,
  tableSortDirection: 'asc', // 'asc' | 'desc'
  tableFilters: {}, // { propertyId: filterValue }

  // ---- actions ----
  setActiveView: (view) => set({ activeView: view }),
  setSelectedCardId: (cardId) => set({ selectedCardId: cardId }),
  setKanbanGroupByPropertyId: (propId) => set({ kanbanGroupByPropertyId: propId }),
  setTableSort: (column, direction) => set({ tableSortColumn: column, tableSortDirection: direction }),
  setTableFilter: (propertyId, value) =>
    set((state) => ({
      tableFilters: { ...state.tableFilters, [propertyId]: value },
    })),
  clearTableFilters: () => set({ tableFilters: {} }),
  resetViewState: () =>
    set({
      activeView: 'canvas',
      selectedCardId: null,
      kanbanGroupByPropertyId: null,
      tableSortColumn: null,
      tableSortDirection: 'asc',
      tableFilters: {},
    }),
}));

export { usePropertyStore };
export default usePropertyStore;
