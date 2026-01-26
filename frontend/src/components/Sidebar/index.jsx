/**
 * Claude-like Sidebar - Main orchestrator component
 * Re-exports the modular Sidebar for use when migrating from monolithic Sidebar.jsx
 */

export { default as StarredSection } from './StarredSection';
export { default as RecentsSection } from './RecentsSection';
export { default as ProjectsSection } from './ProjectsSection';
export { default as UserProfile } from './UserProfile';
export { useSidebarState } from './useSidebarState';
export { sidebarReducer, ACTIONS, initialState } from './sidebarReducer';
