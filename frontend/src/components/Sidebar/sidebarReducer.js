/**
 * Sidebar state reducer for Claude-like UX
 * Consolidates 25+ useState hooks into a single manageable state
 */

export const ACTIONS = {
  // UI State
  SET_THEME: 'SET_THEME',
  TOGGLE_SECTION: 'TOGGLE_SECTION',
  SET_MOBILE_OPEN: 'SET_MOBILE_OPEN',

  // Modals
  OPEN_MODAL: 'OPEN_MODAL',
  CLOSE_MODAL: 'CLOSE_MODAL',
  CLOSE_ALL_MODALS: 'CLOSE_ALL_MODALS',

  // Data
  SET_FOLDERS: 'SET_FOLDERS',
  SET_TAGS: 'SET_TAGS',
  SET_SELECTED_TAGS: 'SET_SELECTED_TAGS',
  TOGGLE_TAG_FILTER: 'TOGGLE_TAG_FILTER',

  // Drag & Drop
  SET_DRAGGED_CONVERSATION: 'SET_DRAGGED_CONVERSATION',
  CLEAR_DRAGGED: 'CLEAR_DRAGGED',

  // Editing
  SET_EDITING_TAGS: 'SET_EDITING_TAGS',
  SET_TAG_INPUT: 'SET_TAG_INPUT',

  // Folders
  TOGGLE_FOLDER: 'TOGGLE_FOLDER',
  SET_NEW_FOLDER_NAME: 'SET_NEW_FOLDER_NAME',
  TOGGLE_NEW_FOLDER: 'TOGGLE_NEW_FOLDER',

  // Loading states
  SET_IMPORTING: 'SET_IMPORTING',

  // More menu
  TOGGLE_MORE_MENU: 'TOGGLE_MORE_MENU',

  // Starred conversations
  SET_STARRED: 'SET_STARRED',
  TOGGLE_STARRED_ITEM: 'TOGGLE_STARRED_ITEM',
};

export const initialState = {
  // UI State
  theme: localStorage.getItem('theme') || 'light',
  isMobileOpen: false,

  // Section visibility (collapsible)
  sections: {
    starred: false,   // collapsed by default
    recents: false,   // collapsed by default
    all: true,        // expanded by default
  },

  // Modals
  modals: {
    settings: false,
    analytics: false,
    projects: false,
    batch: false,
    search: false,
    admin: false,
  },

  // More menu
  showMoreMenu: false,

  // Data
  folders: [],
  allTags: [],
  selectedTags: [],
  starredIds: JSON.parse(localStorage.getItem('starredConversations') || '[]'),

  // Folder state
  collapsedFolders: {},
  showNewFolder: false,
  newFolderName: '',

  // Drag & Drop
  draggedConversation: null,

  // Tag editing
  editingTags: null,
  tagInput: '',

  // Loading
  isImporting: false,

  // Current project
  currentProjectId: null,
};

export function sidebarReducer(state, action) {
  switch (action.type) {
    // UI State
    case ACTIONS.SET_THEME:
      return { ...state, theme: action.payload };

    case ACTIONS.TOGGLE_SECTION:
      return {
        ...state,
        sections: {
          ...state.sections,
          [action.payload]: !state.sections[action.payload],
        },
      };

    case ACTIONS.SET_MOBILE_OPEN:
      return { ...state, isMobileOpen: action.payload };

    // Modals
    case ACTIONS.OPEN_MODAL:
      return {
        ...state,
        modals: { ...state.modals, [action.payload]: true },
        showMoreMenu: false,
      };

    case ACTIONS.CLOSE_MODAL:
      return {
        ...state,
        modals: { ...state.modals, [action.payload]: false },
      };

    case ACTIONS.CLOSE_ALL_MODALS:
      return {
        ...state,
        modals: Object.keys(state.modals).reduce((acc, key) => {
          acc[key] = false;
          return acc;
        }, {}),
      };

    // Data
    case ACTIONS.SET_FOLDERS:
      return { ...state, folders: action.payload };

    case ACTIONS.SET_TAGS:
      return { ...state, allTags: action.payload };

    case ACTIONS.SET_SELECTED_TAGS:
      return { ...state, selectedTags: action.payload };

    case ACTIONS.TOGGLE_TAG_FILTER:
      const tag = action.payload;
      const newSelectedTags = state.selectedTags.includes(tag)
        ? state.selectedTags.filter(t => t !== tag)
        : [...state.selectedTags, tag];
      return { ...state, selectedTags: newSelectedTags };

    // Drag & Drop
    case ACTIONS.SET_DRAGGED_CONVERSATION:
      return { ...state, draggedConversation: action.payload };

    case ACTIONS.CLEAR_DRAGGED:
      return { ...state, draggedConversation: null };

    // Tag editing
    case ACTIONS.SET_EDITING_TAGS:
      return { ...state, editingTags: action.payload, tagInput: '' };

    case ACTIONS.SET_TAG_INPUT:
      return { ...state, tagInput: action.payload };

    // Folders
    case ACTIONS.TOGGLE_FOLDER:
      return {
        ...state,
        collapsedFolders: {
          ...state.collapsedFolders,
          [action.payload]: !state.collapsedFolders[action.payload],
        },
      };

    case ACTIONS.SET_NEW_FOLDER_NAME:
      return { ...state, newFolderName: action.payload };

    case ACTIONS.TOGGLE_NEW_FOLDER:
      return {
        ...state,
        showNewFolder: !state.showNewFolder,
        newFolderName: '',
      };

    // Loading
    case ACTIONS.SET_IMPORTING:
      return { ...state, isImporting: action.payload };

    // More menu
    case ACTIONS.TOGGLE_MORE_MENU:
      return { ...state, showMoreMenu: !state.showMoreMenu };

    // Starred
    case ACTIONS.SET_STARRED:
      localStorage.setItem('starredConversations', JSON.stringify(action.payload));
      return { ...state, starredIds: action.payload };

    case ACTIONS.TOGGLE_STARRED_ITEM:
      const id = action.payload;
      const newStarred = state.starredIds.includes(id)
        ? state.starredIds.filter(i => i !== id)
        : [...state.starredIds, id];
      localStorage.setItem('starredConversations', JSON.stringify(newStarred));
      return { ...state, starredIds: newStarred };

    default:
      return state;
  }
}
