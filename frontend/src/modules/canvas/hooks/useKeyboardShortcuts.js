import { useEffect } from 'react';

/**
 * Registers keyboard shortcuts for the board canvas.
 * Side-effect only hook -- returns nothing.
 *
 * @param {Object} params
 * @param {Array}    params.selectedNodes - Currently selected nodes
 * @param {Array}    params.selectedEdges - Currently selected edges
 * @param {Function} params.handleDeleteSelected - Delete selected elements
 * @param {Function} params.handleAddCard - Add a new card by type
 * @param {boolean}  params.showSearch - Whether search is open
 * @param {Function} params.setShowCouncilModal - Toggle council modal
 * @param {Function} params.setShowSearch - Toggle search panel
 * @param {Function} params.setHighlightedCards - Set search highlight (no-op when derived)
 * @param {Function} params.setContextMenu - Clear context menu
 * @param {Function} params.setNodes - ReactFlow setNodes dispatcher
 * @param {Function} params.setEdges - ReactFlow setEdges dispatcher
 * @param {Function} params.searchReset - Reset the board search state
 * @param {Function} [params.onAddSection] - Create a new section
 * @param {Function} [params.onAddSubBoard] - Create a new sub-board
 */
export default function useKeyboardShortcuts({
  selectedNodes,
  selectedEdges,
  handleDeleteSelected,
  handleAddCard,
  showSearch,
  setShowCouncilModal,
  setShowSearch,
  setHighlightedCards,
  setContextMenu,
  setNodes,
  setEdges,
  searchReset,
  onAddSection,
  onAddSubBoard,
}) {
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if ((e.key === 'Delete' || e.key === 'Backspace') && (selectedNodes.length > 0 || selectedEdges.length > 0)) {
        e.preventDefault();
        handleDeleteSelected();
      }
      if (e.key === 'n' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        handleAddCard('note');
      }
      if (e.key === 'k' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        handleAddCard('knowledge');
      }
      if (e.key === 'Escape') {
        setShowCouncilModal(false);
        setShowSearch(false);
        setHighlightedCards(null);
        if (searchReset) searchReset();
        setContextMenu(null);
        setNodes((nds) => nds.map((n) => ({ ...n, selected: false })));
        setEdges((eds) => eds.map((e) => ({ ...e, selected: false })));
      }
      if (e.key === 'a' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setNodes((nds) => nds.map((n) => ({ ...n, selected: true })));
      }
      if (e.key === 'f' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setShowSearch((prev) => !prev);
        if (showSearch) {
          setHighlightedCards(null);
          if (searchReset) searchReset();
        }
      }
      // Cmd+G: Create section
      if (e.key === 'g' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        onAddSection?.();
      }
      // Cmd+Shift+B: Create sub-board
      if (e.key === 'B' && (e.metaKey || e.ctrlKey) && e.shiftKey) {
        e.preventDefault();
        onAddSubBoard?.();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNodes, selectedEdges, handleDeleteSelected, handleAddCard, showSearch, searchReset, onAddSection, onAddSubBoard, setShowCouncilModal, setShowSearch, setHighlightedCards, setContextMenu, setNodes, setEdges]);
}
