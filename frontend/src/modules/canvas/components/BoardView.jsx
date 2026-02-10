import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import CanvasCard from './CanvasCard';
import AnimatedEdge from './AnimatedEdge';
import SectionNode from './SectionNode';
import BoardToolbar from './BoardToolbar';
import BoardQueryInput from './BoardQueryInput';
import BoardSearch from './BoardSearch';
import CardContextMenu from './CardContextMenu';
import BoardMemoryPanel from './BoardMemoryPanel';
import JournalPanel from './JournalPanel';
import InboxPanel from './InboxPanel';
import WorkflowPanel from './WorkflowPanel';
import WorkflowRunner from './WorkflowRunner';
import AgentPanel from './AgentPanel';
import CardChatPanel from './CardChatPanel';
import BoardBreadcrumbs from './BoardBreadcrumbs';
import VersionHistoryPanel from './VersionHistoryPanel';
import ViewContainer from '../../views/ViewContainer.jsx';
import PropertyPanel from '../../properties/PropertyPanel.jsx';
import { usePropertyStore } from '../../../stores/propertyStore.js';
import { usePropertyDefinitions, useAllPropertyValues, useBulkSetCardProperties } from '../../../api/queries/propertyQueries.js';
import { useNavigate } from 'react-router-dom';
import { deleteCard, updateCard, runCouncilFromBoard, runBoardAIAction, createSection, updateSection, deleteSection, createChildBoard, getBoardBreadcrumbs, createCard, groupIntoSection, ungroupSection } from '../../../api/boards.js';
import { cardToNode, edgeToFlow, sectionToNode } from '../utils.js';
import BoardContext from '../BoardContext.js';
import useBoardState from '../hooks/useBoardState.js';
import useCardActions from '../hooks/useCardActions.js';
import useEdgeActions from '../hooks/useEdgeActions.js';
import useDebouncedPositions from '../hooks/useDebouncedPositions.js';
import useKeyboardShortcuts from '../hooks/useKeyboardShortcuts.js';
import useBoardSearch from '../hooks/useBoardSearch.js';
import useBacklinks from '../hooks/useBacklinks.js';
import useWorkflows from '../hooks/useWorkflows.js';
import useAgent from '../hooks/useAgent.js';
import { useHistoryStore } from '../../../stores/historyStore';
import '../styles/BoardView.css';

const nodeTypes = { canvasCard: CanvasCard, sectionNode: SectionNode };
const edgeTypes = { animatedEdge: AnimatedEdge };

const NOOP = () => {};

function BoardViewInner({ boardId, onBack }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [showCouncilModal, setShowCouncilModal] = useState(false);
  const [councilRunning, setCouncilRunning] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [contextMenu, setContextMenu] = useState(null);
  const [boardProcessing, setBoardProcessing] = useState(false);
  const [showMemoryPanel, setShowMemoryPanel] = useState(false);
  const [showJournalPanel, setShowJournalPanel] = useState(false);
  const [showInboxPanel, setShowInboxPanel] = useState(false);
  const [showWorkflowPanel, setShowWorkflowPanel] = useState(false);
  const [showAgentPanel, setShowAgentPanel] = useState(false);
  const [chatPanelCard, setChatPanelCard] = useState(null);
  const [editingCardId, setEditingCardId] = useState(null);
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const reactFlow = useReactFlow();
  const navigate = useNavigate();

  // Undo/redo from history store
  const undo = useHistoryStore((s) => s.undo);
  const redo = useHistoryStore((s) => s.redo);
  const canUndo = useHistoryStore((s) => s.canUndo());
  const canRedo = useHistoryStore((s) => s.canRedo());
  const clearHistory = useHistoryStore((s) => s.clearHistory);

  // -- Extracted hooks --
  const {
    board, loading, boardMemory,
    handleRenameBoard, handleAddFact, handleDeleteFact, handleClearMemory, memoryCount,
  } = useBoardState(boardId, setNodes, setEdges);

  const {
    handleAddCard, stableUpdateCard, handleToggleKnowledge,
    handleCardAIAction: rawCardAIAction, processingCards,
    actionError, clearActionError,
  } = useCardActions(boardId, nodes, setNodes, setEdges);

  const {
    handleConnect, handleDeleteSelected, selectedNodes, selectedEdges,
  } = useEdgeActions(boardId, nodes, edges, setNodes, setEdges);

  const { handleNodesChange, handleMoveEnd } = useDebouncedPositions(boardId, onNodesChange, setNodes);

  // Workflow & Agent hooks
  const wf = useWorkflows(boardId);
  const agent = useAgent(boardId);

  // View switching + property data
  const { activeView, setActiveView, selectedCardId, setSelectedCardId } = usePropertyStore();
  const { data: propDefsData } = usePropertyDefinitions(boardId);
  const { data: allValsData } = useAllPropertyValues(boardId);
  const bulkSetMutation = useBulkSetCardProperties(boardId);
  const propertyDefinitions = propDefsData?.properties || [];
  const allPropertyValues = allValsData?.values || [];

  // Build lookup: { cardId: { propId: value, ... } }
  const propertyValuesByCard = useMemo(() => {
    const map = {};
    for (const pv of allPropertyValues) {
      if (!map[pv.card_id]) map[pv.card_id] = {};
      map[pv.card_id][pv.property_id] = pv.value;
    }
    return map;
  }, [allPropertyValues]);

  // Handle property value changes (for kanban drag-drop, table inline edit)
  const handlePropertyChange = useCallback((cardId, propId, newValue) => {
    const existing = propertyValuesByCard[cardId] || {};
    bulkSetMutation.mutate({ cardId, values: { ...existing, [propId]: newValue } });
  }, [propertyValuesByCard, bulkSetMutation]);

  // Cards list for table/kanban views
  const cardsList = useMemo(() => {
    return nodes
      .filter((n) => n.type !== 'sectionNode')
      .map((n) => ({
        id: n.id,
        title: n.data.title,
        card_type: n.data.card_type,
        content: n.data.content,
        created_at: n.data.extra?.created_at,
      }));
  }, [nodes]);

  const handleViewCardSelect = useCallback((cardId) => {
    setSelectedCardId(cardId);
  }, [setSelectedCardId]);

  // SSE card/edge creation callback for workflows and agent
  const handleSSECardCreated = useCallback((card, edge) => {
    setNodes((nds) => [...nds, cardToNode(card)]);
    if (edge) {
      setEdges((eds) => [...eds, edgeToFlow(edge)]);
    }
  }, [setNodes, setEdges]);

  // Wrap card AI action to also close context menu
  const handleCardAIAction = useCallback((cardId, action, customPrompt) => {
    setContextMenu(null);
    rawCardAIAction(cardId, action, customPrompt);
  }, [rawCardAIAction]);

  // Discuss card in side chat panel
  const handleDiscussCard = useCallback((nodeId) => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    // Close other panels (one-at-a-time UX)
    setShowMemoryPanel(false);
    setShowJournalPanel(false);
    setShowInboxPanel(false);
    setShowWorkflowPanel(false);
    setShowAgentPanel(false);
    setContextMenu(null);
    setChatPanelCard({
      id: node.id,
      title: node.data.title,
      content: node.data.content,
      card_type: node.data.card_type,
    });
  }, [nodes]);

  const handleChatCardCreated = useCallback((card) => {
    setNodes((nds) => [...nds, cardToNode(card)]);
  }, [setNodes]);

  // Section handlers
  const handleAddSection = useCallback(async () => {
    // If 2+ non-section cards are selected, group them into a section
    const cardNodes = selectedNodes.filter((n) => n.type !== 'sectionNode');
    if (cardNodes.length >= 2) {
      try {
        const cardIds = cardNodes.map((n) => n.id);
        const result = await groupIntoSection(boardId, { card_ids: cardIds });
        const sectionNode = sectionToNode(result.section);
        // Rebuild nodes: remove old card nodes, add section + updated children
        setNodes((nds) => {
          const idSet = new Set(cardIds);
          const remaining = nds.filter((n) => !idSet.has(n.id));
          const childNodes = result.cards.map(cardToNode);
          return [...remaining, sectionNode, ...childNodes];
        });
      } catch (err) {
        console.error('Failed to group cards into section:', err);
      }
      return;
    }
    // Default: create empty section at viewport center
    const vp = reactFlow.getViewport();
    const centerX = (-vp.x + window.innerWidth / 2) / vp.zoom;
    const centerY = (-vp.y + window.innerHeight / 2) / vp.zoom;
    try {
      const section = await createSection(boardId, {
        title: 'New Section',
        color: 'gray',
        x: centerX - 200,
        y: centerY - 150,
        width: 400,
        height: 300,
      });
      setNodes((nds) => [...nds, sectionToNode(section)]);
    } catch (err) {
      console.error('Failed to create section:', err);
    }
  }, [boardId, reactFlow, setNodes, selectedNodes]);

  const handleUpdateSection = useCallback(async (sectionId, updates) => {
    try {
      await updateSection(boardId, sectionId, updates);
      setNodes((nds) => nds.map((n) => {
        if (n.id === `section-${sectionId}`) {
          return {
            ...n,
            data: { ...n.data, ...updates },
            ...(updates.width || updates.height ? {
              style: {
                ...n.style,
                ...(updates.width ? { width: updates.width } : {}),
                ...(updates.height ? { height: updates.height } : {}),
              },
            } : {}),
          };
        }
        return n;
      }));
    } catch (err) {
      console.error('Failed to update section:', err);
    }
  }, [boardId, setNodes]);

  const handleDeleteSection = useCallback(async (sectionId) => {
    try {
      // Backend converts child positions to absolute and clears section_id
      await deleteSection(boardId, sectionId);
      const sectionNodeId = `section-${sectionId}`;
      setNodes((nds) => {
        // Convert child nodes back to absolute positioning (remove parentId)
        return nds
          .filter((n) => n.id !== sectionNodeId)
          .map((n) => {
            if (n.parentId === sectionNodeId) {
              const { parentId, extent, ...rest } = n;
              // Find the section node to compute absolute position
              const sectionNode = nds.find((s) => s.id === sectionNodeId);
              if (sectionNode) {
                const headerOffset = 36;
                return {
                  ...rest,
                  position: {
                    x: n.position.x + sectionNode.position.x,
                    y: n.position.y + sectionNode.position.y + headerOffset,
                  },
                };
              }
              return rest;
            }
            return n;
          });
      });
    } catch (err) {
      console.error('Failed to delete section:', err);
    }
  }, [boardId, setNodes]);

  const handleUngroupSection = useCallback(async (sectionId) => {
    try {
      const result = await ungroupSection(boardId, sectionId);
      const sectionNodeId = `section-${sectionId}`;
      setNodes((nds) => {
        // Remove section node, replace child nodes with absolute-positioned ones
        const updatedCardIds = new Set(result.cards.map((c) => c.id));
        const remaining = nds.filter(
          (n) => n.id !== sectionNodeId && !updatedCardIds.has(n.id)
        );
        const updatedNodes = result.cards.map(cardToNode);
        return [...remaining, ...updatedNodes];
      });
    } catch (err) {
      console.error('Failed to ungroup section:', err);
    }
  }, [boardId, setNodes]);

  // Load breadcrumbs when board loads
  useEffect(() => {
    if (!boardId) return;
    getBoardBreadcrumbs(boardId)
      .then((data) => setBreadcrumbs(data.breadcrumbs || []))
      .catch(() => setBreadcrumbs([]));
  }, [boardId]);

  // Clear undo/redo history when switching boards
  useEffect(() => {
    clearHistory();
  }, [boardId, clearHistory]);

  // Create sub-board with a board_ref card on the current board
  const handleCreateSubBoard = useCallback(async () => {
    try {
      const child = await createChildBoard(boardId, { name: 'New Sub-board' });
      const vp = reactFlow.getViewport();
      const centerX = (-vp.x + window.innerWidth / 2) / vp.zoom;
      const centerY = (-vp.y + window.innerHeight / 2) / vp.zoom;
      const card = await createCard(boardId, {
        card_type: 'board_ref',
        title: child.name,
        position_x: centerX,
        position_y: centerY,
        extra: { target_board_id: child.id },
      });
      setNodes((nds) => [...nds, cardToNode(card)]);
    } catch (err) {
      console.error('Failed to create sub-board:', err);
    }
  }, [boardId, reactFlow, setNodes]);

  // Card color change handler
  const handleCardColorChange = useCallback(async (cardId, color) => {
    try {
      await updateCard(boardId, cardId, { color });
      setNodes((nds) => nds.map((n) =>
        n.id === cardId ? { ...n, data: { ...n.data, color } } : n
      ));
    } catch (err) {
      console.error('Failed to update card color:', err);
    }
  }, [boardId, setNodes]);

  // Stable refs for callbacks passed into node data
  const nodesRef = useRef(nodes);
  nodesRef.current = nodes;

  const handleFocusCardRef = useRef(null);
  handleFocusCardRef.current = useCallback((cardId) => {
    const node = nodesRef.current.find((n) => n.id === cardId);
    if (node) {
      reactFlow.setCenter(node.position.x + 140, node.position.y + 100, { zoom: 1.2, duration: 400 });
      setNodes((nds) => nds.map((n) => ({ ...n, selected: n.id === cardId })));
    }
  }, [reactFlow, setNodes]);

  const stableFocusCard = useCallback((cardId) => handleFocusCardRef.current(cardId), []);

  // Compute backlinks from edges (extracted hook)
  const backlinksMap = useBacklinks(edges, nodes);

  // Board search (extracted hook)
  const {
    query: searchQuery, setQuery: setSearchQuery,
    filterType: searchFilterType, setFilterType: setSearchFilterType,
    matches: searchMatches, matchIds: searchMatchIds,
    activeIndex: searchActiveIndex, activeMatchId: searchActiveMatchId,
    goNext: searchGoNext, goPrev: searchGoPrev, reset: searchReset,
  } = useBoardSearch(nodes);

  // Derive highlightedCards from search match IDs
  const highlightedCards = useMemo(() => {
    if (!searchQuery.trim() || searchMatchIds.length === 0) return null;
    return new Set(searchMatchIds);
  }, [searchQuery, searchMatchIds]);

  // Focus callback for search navigation
  const handleSearchFocusActive = useCallback(() => {
    if (searchActiveMatchId) {
      stableFocusCard(searchActiveMatchId);
    }
  }, [searchActiveMatchId, stableFocusCard]);

  // Stable callback to clear editing state (identity never changes)
  const stableClearEditing = useCallback(() => setEditingCardId(null), []);
  // Stable callback to start editing a card (single-click on content)
  const stableStartEditing = useCallback((cardId) => setEditingCardId(cardId), []);

  // Board context value — provides editing callbacks directly to CanvasCard via React context
  // This bypasses node data injection timing issues and works for newly created cards immediately
  const boardContextValue = useMemo(() => ({
    editingCardId,
    startEditing: stableStartEditing,
    clearEditing: stableClearEditing,
    updateCard: stableUpdateCard,
    focusCard: stableFocusCard,
  }), [editingCardId, stableStartEditing, stableClearEditing, stableUpdateCard, stableFocusCard]);

  // Build property badges for canvas cards
  const propertyBadgesByCard = useMemo(() => {
    const map = {};
    const BADGE_TYPES = new Set(['select', 'multi_select', 'date', 'checkbox']);
    for (const [cardId, vals] of Object.entries(propertyValuesByCard)) {
      const badges = [];
      for (const def of propertyDefinitions) {
        if (!BADGE_TYPES.has(def.property_type)) continue;
        const val = vals[def.id];
        if (val == null || val === '') continue;
        let display;
        if (def.property_type === 'checkbox') display = val ? '\u2713' : null;
        else if (def.property_type === 'date') display = new Date(val).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
        else if (def.property_type === 'multi_select' && Array.isArray(val)) display = val.join(', ');
        else display = String(val);
        if (display) badges.push({ id: def.id, name: def.name, display });
      }
      if (badges.length > 0) map[cardId] = badges;
    }
    return map;
  }, [propertyValuesByCard, propertyDefinitions]);

  // Inject dynamic data into nodes when dependencies change
  useEffect(() => {
    setNodes((nds) => {
      const boardCards = nds.map((n) => ({ id: n.id, card_type: n.data.card_type, title: n.data.title, extra: n.data.extra }));
      return nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          backlinks: backlinksMap[n.id] || [],
          onFocusCard: stableFocusCard,
          onUpdateCard: stableUpdateCard,
          isDimmed: highlightedCards != null && !highlightedCards.has(n.id),
          isProcessing: processingCards.has(n.id),
          editingCardId,
          onClearEditing: stableClearEditing,
          onStartEditing: stableStartEditing,
          boardCards,
          propertyBadges: propertyBadgesByCard[n.id] || [],
        },
      }));
    });
  }, [backlinksMap, stableFocusCard, stableUpdateCard, highlightedCards, processingCards, editingCardId, stableClearEditing, stableStartEditing, propertyBadgesByCard]);

  // Inject section callbacks
  useEffect(() => {
    setNodes((nds) => nds.map((n) => {
      if (n.type === 'sectionNode') {
        return {
          ...n,
          data: {
            ...n.data,
            onUpdateSection: handleUpdateSection,
            onDeleteSection: handleDeleteSection,
            onUngroupSection: handleUngroupSection,
          },
        };
      }
      return n;
    }));
  }, [handleUpdateSection, handleDeleteSection, handleUngroupSection]);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    selectedNodes, selectedEdges, handleDeleteSelected, handleAddCard,
    showSearch, setShowCouncilModal, setShowSearch,
    setHighlightedCards: NOOP, // stable no-op, derived from search state now
    setContextMenu, setNodes, setEdges,
    searchReset,
    onAddSection: handleAddSection,
    onAddSubBoard: handleCreateSubBoard,
    onUndo: undo,
    onRedo: redo,
  });

  // Double-click node to edit or navigate to sub-board
  const handleNodeDoubleClick = useCallback((_event, node) => {
    // Navigate to sub-board
    if (node.data?.card_type === 'board_ref' && node.data?.extra?.target_board_id) {
      const targetId = node.data.extra.target_board_id;
      navigate(`/boards/${targetId}`);
      return;
    }
    const cardType = node.data?.card_type;
    const isKnowledge = node.data?.extra?.is_knowledge;
    const editable = cardType === 'note' || cardType === 'link' || isKnowledge;
    if (editable) {
      setEditingCardId(node.id);
    }
  }, []);

  // Context menu
  const handleNodeContextMenu = useCallback((event, node) => {
    event.preventDefault();
    setContextMenu({ nodeId: node.id, x: event.clientX, y: event.clientY });
  }, []);
  const handleCloseContextMenu = useCallback(() => setContextMenu(null), []);

  // Auto-dismiss action errors after 5 seconds
  useEffect(() => {
    if (!actionError) return;
    const timer = setTimeout(clearActionError, 5000);
    return () => clearTimeout(timer);
  }, [actionError, clearActionError]);

  // Board-level AI action
  const handleBoardAIAction = useCallback(async (action) => {
    setBoardProcessing(true);
    try {
      const cardIds = selectedNodes.length > 0 ? selectedNodes.map((n) => n.id) : [];
      const result = await runBoardAIAction(boardId, { action, cardIds });
      const newNodes = (result.cards || []).map(cardToNode);
      const newEdges = (result.edges || []).map(edgeToFlow);
      setNodes((nds) => [...nds, ...newNodes]);
      setEdges((eds) => [...eds, ...newEdges]);
      if (result.color_updates) {
        setNodes((nds) => nds.map((n) => {
          const newColor = result.color_updates[n.id];
          return newColor ? { ...n, data: { ...n.data, color: newColor } } : n;
        }));
      }
    } catch (err) {
      console.error('Board AI action failed:', err);
    } finally {
      setBoardProcessing(false);
    }
  }, [boardId, selectedNodes, setNodes, setEdges]);

  // Council from board
  const handleRunCouncil = useCallback(async ({ query, webSearch, fastMode }) => {
    setCouncilRunning(true);
    try {
      await runCouncilFromBoard(
        boardId,
        { query, cardIds: selectedNodes.map((n) => n.id), webSearch, fastMode },
        (event) => {
          if (event.type === 'board_update') {
            const newNodes = (event.cards || []).map(cardToNode);
            const newEdges = (event.edges || []).map(edgeToFlow);
            setNodes((nds) => [...nds, ...newNodes]);
            setEdges((eds) => [...eds, ...newEdges]);
          }
        }
      );
    } catch (err) {
      console.error('Council from board failed:', err);
    } finally {
      setCouncilRunning(false);
      setShowCouncilModal(false);
    }
  }, [boardId, selectedNodes, setNodes, setEdges]);

  // Default viewport from saved state
  const defaultViewport = useMemo(() => {
    if (board?.viewport) {
      return { x: board.viewport.x || 0, y: board.viewport.y || 0, zoom: board.viewport.zoom || 1 };
    }
    return { x: 0, y: 0, zoom: 1 };
  }, [board?.viewport]);

  // MiniMap node color by card type
  const minimapNodeColor = useCallback((node) => {
    switch (node.data?.card_type) {
      case 'query': return '#6366f1';
      case 'council_response': return '#f59e0b';
      case 'council_synthesis': return '#10b981';
      case 'file_ref': return '#94a3b8';
      case 'link': return '#3b82f6';
      default: return '#e2e8f0';
    }
  }, []);

  if (loading) {
    return (
      <div className="board-view board-view--loading">
        <div className="loading-spinner" />
        <p>Loading board...</p>
      </div>
    );
  }

  return (
    <div className="board-view">
      <BoardToolbar
        board={board}
        onAddCard={handleAddCard}
        onAddSection={handleAddSection}
        onAddSubBoard={handleCreateSubBoard}
        onBack={onBack}
        onRenameBoard={handleRenameBoard}
        selectedCount={selectedNodes.length}
        onRunCouncil={() => setShowCouncilModal(true)}
        onDeleteSelected={selectedNodes.length > 0 || selectedEdges.length > 0 ? handleDeleteSelected : undefined}
        onToggleSearch={() => { setShowSearch((p) => !p); if (showSearch) searchReset(); }}
        onBoardAIAction={handleBoardAIAction}
        boardProcessing={boardProcessing}
        onToggleMemory={() => setShowMemoryPanel((p) => !p)}
        memoryCount={memoryCount}
        onToggleJournal={() => setShowJournalPanel((p) => !p)}
        onToggleInbox={() => setShowInboxPanel((p) => !p)}
        onToggleWorkflows={() => setShowWorkflowPanel((p) => !p)}
        onToggleAgent={() => setShowAgentPanel((p) => !p)}
        agentRunning={agent.running}
        activeView={activeView}
        onViewChange={setActiveView}
        canUndo={canUndo}
        canRedo={canRedo}
        onUndo={undo}
        onRedo={redo}
        onToggleHistory={() => setShowVersionHistory((p) => !p)}
      />

      {breadcrumbs.length > 0 && (
        <BoardBreadcrumbs
          breadcrumbs={breadcrumbs}
          currentBoard={board}
          onNavigate={(id) => navigate(`/boards/${id}`)}
        />
      )}

      {showSearch && (
        <BoardSearch
          query={searchQuery}
          setQuery={setSearchQuery}
          filterType={searchFilterType}
          setFilterType={setSearchFilterType}
          matchCount={searchMatches.length}
          activeIndex={searchActiveIndex}
          onNext={searchGoNext}
          onPrev={searchGoPrev}
          onFocusActive={handleSearchFocusActive}
          onClose={() => { setShowSearch(false); searchReset(); }}
        />
      )}

      {activeView === 'canvas' ? (
        <div className="board-view__canvas">
          <BoardContext.Provider value={boardContextValue}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={handleConnect}
            onMoveEnd={handleMoveEnd}
            onNodeDoubleClick={handleNodeDoubleClick}
            onNodeContextMenu={handleNodeContextMenu}
            onPaneClick={handleCloseContextMenu}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            defaultViewport={defaultViewport}
            connectionMode="loose"
            snapToGrid
            snapGrid={[16, 16]}
            fitView={!board?.viewport}
            deleteKeyCode={null}
            multiSelectionKeyCode="Shift"
          >
            <Background gap={16} size={1} color="var(--border-primary)" />
            <Controls />
            <MiniMap nodeColor={minimapNodeColor} maskColor="var(--bg-overlay)" />
          </ReactFlow>
          </BoardContext.Provider>
        </div>
      ) : (
        <ViewContainer
          activeView={activeView}
          cards={cardsList}
          propertyDefinitions={propertyDefinitions}
          propertyValuesByCard={propertyValuesByCard}
          onCardSelect={handleViewCardSelect}
          onPropertyChange={handlePropertyChange}
          boardId={boardId}
        />
      )}

      {contextMenu && (
        <CardContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          nodeId={contextMenu.nodeId}
          cardType={nodes.find((n) => n.id === contextMenu.nodeId)?.data?.card_type}
          isKnowledge={nodes.find((n) => n.id === contextMenu.nodeId)?.data?.extra?.is_knowledge}
          onAction={handleCardAIAction}
          onToggleKnowledge={handleToggleKnowledge}
          onColorChange={handleCardColorChange}
          onEdit={(cardId) => {
            setContextMenu(null);
            setEditingCardId(cardId);
          }}
          onDelete={(cardId) => {
            setContextMenu(null);
            deleteCard(boardId, cardId).then(() => {
              setNodes((nds) => nds.filter((n) => n.id !== cardId));
              setEdges((eds) => eds.filter((e) => e.source !== cardId && e.target !== cardId));
            }).catch(console.error);
          }}
          onDiscuss={handleDiscussCard}
          onClose={handleCloseContextMenu}
        />
      )}

      {showCouncilModal && (
        <BoardQueryInput
          selectedCards={selectedNodes.map((n) => ({
            id: n.id, title: n.data?.title, card_type: n.data?.card_type,
          }))}
          onRun={handleRunCouncil}
          onClose={() => setShowCouncilModal(false)}
          isRunning={councilRunning}
        />
      )}

      {showMemoryPanel && (
        <BoardMemoryPanel
          memory={boardMemory}
          onAddFact={handleAddFact}
          onDeleteFact={handleDeleteFact}
          onClear={handleClearMemory}
          onClose={() => setShowMemoryPanel(false)}
        />
      )}

      {showJournalPanel && (
        <JournalPanel
          boardId={boardId}
          onClose={() => setShowJournalPanel(false)}
          onFocusCard={stableFocusCard}
        />
      )}

      {showInboxPanel && (
        <InboxPanel
          boardId={boardId}
          onClose={() => setShowInboxPanel(false)}
          onFocusCard={stableFocusCard}
        />
      )}

      {showWorkflowPanel && (
        <WorkflowPanel
          boardId={boardId}
          workflows={wf.workflows}
          activeWorkflow={wf.activeWorkflow}
          onSelectWorkflow={wf.setActiveWorkflow}
          onCreateWorkflow={wf.createWorkflow}
          onDeleteWorkflow={wf.deleteWorkflow}
          onRunWorkflow={(wfId, opts) => wf.runWorkflow(wfId, opts, handleSSECardCreated)}
          onApproveStep={wf.approveStep}
          onCancelWorkflow={wf.cancelWorkflow}
          running={wf.running}
          currentStep={wf.currentStep}
          waitingReview={wf.waitingReview}
          error={wf.error}
          onClearError={wf.clearError}
          onClose={() => setShowWorkflowPanel(false)}
          onRefresh={wf.fetchWorkflows}
        />
      )}

      {wf.running && (
        <WorkflowRunner
          currentStep={wf.currentStep}
          waitingReview={wf.waitingReview}
          onApprove={() => wf.approveStep(wf.activeWorkflow?.id)}
          onCancel={() => wf.cancelWorkflow(wf.activeWorkflow?.id)}
        />
      )}

      {showAgentPanel && (
        <AgentPanel
          boardId={boardId}
          running={agent.running}
          paused={agent.paused}
          thoughts={agent.thoughts}
          iteration={agent.iteration}
          error={agent.error}
          onClearError={agent.clearError}
          onStart={(opts) => agent.startAgent(opts, handleSSECardCreated)}
          onPause={agent.pause}
          onResume={() => agent.resume(handleSSECardCreated)}
          onCancel={agent.cancel}
          runs={agent.runs}
          onRefreshRuns={agent.fetchRuns}
          onClose={() => setShowAgentPanel(false)}
        />
      )}

      {chatPanelCard && (
        <CardChatPanel
          card={chatPanelCard}
          boardId={boardId}
          onClose={() => setChatPanelCard(null)}
          onCardCreated={handleChatCardCreated}
        />
      )}

      {selectedCardId && (
        <PropertyPanel
          boardId={boardId}
          cardId={selectedCardId}
          card={cardsList.find((c) => c.id === selectedCardId)}
          propertyDefinitions={propertyDefinitions}
          onClose={() => setSelectedCardId(null)}
        />
      )}

      {showVersionHistory && (
        <VersionHistoryPanel
          boardId={boardId}
          onClose={() => setShowVersionHistory(false)}
          onRestore={(data) => {
            // Reload board state from snapshot data
            if (data?.cards && data?.edges) {
              setNodes(data.cards.map(cardToNode));
              setEdges(data.edges.map(edgeToFlow));
            }
            clearHistory();
          }}
        />
      )}

      {actionError && (
        <div className="board-view__error-toast" role="alert">
          <span>{actionError.message}</span>
          <button onClick={clearActionError} aria-label="Dismiss error">&times;</button>
        </div>
      )}
    </div>
  );
}

export default function BoardView(props) {
  return (
    <ReactFlowProvider>
      <BoardViewInner {...props} />
    </ReactFlowProvider>
  );
}
