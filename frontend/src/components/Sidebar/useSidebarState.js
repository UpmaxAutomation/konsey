/**
 * Custom hook for sidebar state management
 * Provides actions and derived state for Claude-like sidebar
 */

import { useReducer, useCallback, useEffect, useMemo } from 'react';
import { sidebarReducer, initialState, ACTIONS } from './sidebarReducer';

export function useSidebarState(conversations = []) {
  const [state, dispatch] = useReducer(sidebarReducer, initialState);

  // Theme effect
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', state.theme);
    localStorage.setItem('theme', state.theme);
  }, [state.theme]);

  // Action creators
  const actions = useMemo(() => ({
    // Theme
    toggleTheme: () => {
      dispatch({
        type: ACTIONS.SET_THEME,
        payload: state.theme === 'light' ? 'dark' : 'light',
      });
    },

    // Sections
    toggleSection: (section) => dispatch({ type: ACTIONS.TOGGLE_SECTION, payload: section }),

    // Mobile
    setMobileOpen: (isOpen) => dispatch({ type: ACTIONS.SET_MOBILE_OPEN, payload: isOpen }),

    // Modals
    openModal: (modal) => dispatch({ type: ACTIONS.OPEN_MODAL, payload: modal }),
    closeModal: (modal) => dispatch({ type: ACTIONS.CLOSE_MODAL, payload: modal }),
    closeAllModals: () => dispatch({ type: ACTIONS.CLOSE_ALL_MODALS }),

    // Data
    setFolders: (folders) => dispatch({ type: ACTIONS.SET_FOLDERS, payload: folders }),
    setTags: (tags) => dispatch({ type: ACTIONS.SET_TAGS, payload: tags }),
    toggleTagFilter: (tag) => dispatch({ type: ACTIONS.TOGGLE_TAG_FILTER, payload: tag }),

    // Drag & Drop
    setDraggedConversation: (conv) => dispatch({ type: ACTIONS.SET_DRAGGED_CONVERSATION, payload: conv }),
    clearDragged: () => dispatch({ type: ACTIONS.CLEAR_DRAGGED }),

    // Tag editing
    setEditingTags: (id) => dispatch({ type: ACTIONS.SET_EDITING_TAGS, payload: id }),
    setTagInput: (input) => dispatch({ type: ACTIONS.SET_TAG_INPUT, payload: input }),

    // Folders
    toggleFolder: (id) => dispatch({ type: ACTIONS.TOGGLE_FOLDER, payload: id }),
    setNewFolderName: (name) => dispatch({ type: ACTIONS.SET_NEW_FOLDER_NAME, payload: name }),
    toggleNewFolder: () => dispatch({ type: ACTIONS.TOGGLE_NEW_FOLDER }),

    // Loading
    setImporting: (isImporting) => dispatch({ type: ACTIONS.SET_IMPORTING, payload: isImporting }),

    // More menu
    toggleMoreMenu: () => dispatch({ type: ACTIONS.TOGGLE_MORE_MENU }),
    closeMoreMenu: () => dispatch({ type: ACTIONS.TOGGLE_MORE_MENU }),

    // Starred
    toggleStarred: (id) => dispatch({ type: ACTIONS.TOGGLE_STARRED_ITEM, payload: id }),
    setStarred: (ids) => dispatch({ type: ACTIONS.SET_STARRED, payload: ids }),
  }), [state.theme]);

  // Derived state: Filter conversations by tags
  const filteredConversations = useMemo(() => {
    if (state.selectedTags.length === 0) return conversations;
    return conversations.filter(conv =>
      state.selectedTags.some(tag => conv.tags?.includes(tag))
    );
  }, [conversations, state.selectedTags]);

  // Derived state: Starred conversations
  const starredConversations = useMemo(() => {
    return conversations.filter(conv => state.starredIds.includes(conv.id));
  }, [conversations, state.starredIds]);

  // Derived state: Recent conversations (last 15, sorted by updated_at or created_at)
  const recentConversations = useMemo(() => {
    return [...conversations]
      .sort((a, b) => {
        const dateA = new Date(a.updated_at || a.created_at);
        const dateB = new Date(b.updated_at || b.created_at);
        return dateB - dateA;
      })
      .slice(0, 15);
  }, [conversations]);

  // Derived state: Conversations grouped by folder
  const conversationsByFolder = useMemo(() => {
    const byFolder = {};
    const uncategorized = [];

    filteredConversations.forEach(conv => {
      if (conv.folder_id) {
        if (!byFolder[conv.folder_id]) {
          byFolder[conv.folder_id] = [];
        }
        byFolder[conv.folder_id].push(conv);
      } else {
        uncategorized.push(conv);
      }
    });

    return { byFolder, uncategorized };
  }, [filteredConversations]);

  // Check if item is starred
  const isStarred = useCallback((id) => {
    return state.starredIds.includes(id);
  }, [state.starredIds]);

  return {
    state,
    actions,
    // Derived state
    filteredConversations,
    starredConversations,
    recentConversations,
    conversationsByFolder,
    isStarred,
  };
}
