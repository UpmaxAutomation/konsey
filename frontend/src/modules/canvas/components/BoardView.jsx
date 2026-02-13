import { useState, useEffect, useCallback, useMemo, useRef, lazy, Suspense } from 'react';
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

// Stable empty array to avoid creating new references on every render
const EMPTY_ARRAY = [];

import CanvasCard from './CanvasCard';
import PipelineNode from './PipelineNode';
import AnimatedEdge from './AnimatedEdge';
import SectionNode from './SectionNode';
import BoardToolbar from './BoardToolbar';
import TabBar from './TabBar';
import BoardQueryInput from './BoardQueryInput';
import BoardSearch from './BoardSearch';
import CardContextMenu from './CardContextMenu';
import EdgeContextMenu from './EdgeContextMenu';
import BoardMemoryPanel from './BoardMemoryPanel';
import JournalPanel from './JournalPanel';
import InboxPanel from './InboxPanel';
import CardChatPanel from './CardChatPanel';
import CardSidePanel from './CardSidePanel';
import BoardBreadcrumbs from './BoardBreadcrumbs';
import SelectionToolbar from './SelectionToolbar';
import VersionHistoryPanel from './VersionHistoryPanel';
import useCollaboration from '../hooks/useCollaboration.js';
import CollaborationOverlay from './CollaborationOverlay.jsx';
import ViewContainer from '../../views/ViewContainer.jsx';
import PropertyPanel from '../../properties/PropertyPanel.jsx';
import { usePropertyStore } from '../../../stores/propertyStore.js';
import { usePropertyDefinitions, useAllPropertyValues, useBulkSetCardProperties } from '../../../api/queries/propertyQueries.js';
import { useNavigate } from 'react-router-dom';
import { deleteCard, updateCard, runCouncilFromBoard, runBoardAIAction, createSection, updateSection, deleteSection, createChildBoard, getBoardBreadcrumbs, createCard, createEdge as apiCreateEdge, groupIntoSection, ungroupSection, mergeCards, splitCard, listEdges } from '../../../api/boards.js';
import { linkCard, cloneCard, unlinkCard } from '../../../api/cardSearch.js';
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
import usePipeline from '../hooks/usePipeline.js';
import { useAutoLayout } from '../hooks/useAutoLayout.js';
import useAlignmentGuides from '../hooks/useAlignmentGuides.js';
import { useHistoryStore } from '../../../stores/historyStore';
import '../styles/BoardView.css';

// v15: Lazy-load heavy panels
const WorkflowPanel = lazy(() => import('./WorkflowPanel'));
const WorkflowRunner = lazy(() => import('./WorkflowRunner'));
const AgentPanel = lazy(() => import('./AgentPanel'));
const AssetBrowser = lazy(() => import('./AssetBrowser'));
const ExportDialog = lazy(() => import('./ExportDialog'));
const TemplateMarketplace = lazy(() => import('./TemplateMarketplace'));
const IntegrationPanel = lazy(() => import('./IntegrationPanel'));

// v15: Memoize nodeTypes/edgeTypes to prevent ReactFlow re-registration
const nodeTypes = { canvasCard: CanvasCard, sectionNode: SectionNode, pipelineNode: PipelineNode };
const edgeTypes = { animatedEdge: AnimatedEdge };

const NOOP = () => {};

function BoardViewInner({ boardId, onBack }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [showCouncilModal, setShowCouncilModal] = useState(false);
  const [councilRunning, setCouncilRunning] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [contextMenu, setContextMenu] = useState(null);
  const [edgeMenu, setEdgeMenu] = useState(null);
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
  const [showAssetBrowser, setShowAssetBrowser] = useState(false);
  const [showMarketplace, setShowMarketplace] = useState(false);
  const [showExportDialog, setShowExportDialog] = useState(false);
  const [showIntegrations, setShowIntegrations] = useState(false);
  const [sidePanelCardId, setSidePanelCardId] = useState(null);
  const [collapsedSections, setCollapsedSections] = useState(new Set());
  const [openTabs, setOpenTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [recentCards, setRecentCards] = useState([]);
  const [cardDragOver, setCardDragOver] = useState(false);
  const reactFlow = useReactFlow();
  const navigate = useNavigate();

  // Real-time collaboration
  const { connected: collabConnected, boardUsers, remoteCursors, handleMouseMove: handleCollabMouseMove } = useCollaboration(boardId);

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
    handleUpdateEdge, handleReverseEdge, handleDeleteEdge,
  } = useEdgeActions(boardId, nodes, edges, setNodes, setEdges);

  const { handleNodesChange, handleMoveEnd } = useDebouncedPositions(boardId, onNodesChange, setNodes);

  // Workflow, Agent & Pipeline hooks
  const wf = useWorkflows(boardId);
  const agent = useAgent(boardId);
  const pipeline = usePipeline(boardId);

  // Auto-layout (dagre)
  const { applyAutoLayout, tidyUp } = useAutoLayout({ nodes, edges, setNodes, boardId });

  // Alignment guides (snap lines when dragging)
  const { guides: alignmentGuides, onNodeDrag: handleAlignDrag, onNodeDragStop: handleAlignDragStop, alignSelected } = useAlignmentGuides(nodes, setNodes);

  // View switching + property data
  const { activeView, setActiveView, selectedCardId, setSelectedCardId } = usePropertyStore();
  const { data: propDefsData } = usePropertyDefinitions(boardId);
  const { data: allValsData } = useAllPropertyValues(boardId);
  const bulkSetMutation = useBulkSetCardProperties(boardId);
  const propertyDefinitions = propDefsData?.properties || EMPTY_ARRAY;
  const allPropertyValues = allValsData?.values || EMPTY_ARRAY;

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
      .filter((n) => n.type !== 'sectionNode' && n.type !== 'pipelineNode')
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

  const handleExtractToCard = useCallback(async (text, sourceCardId) => {
    try {
      // Position new card to the right of the source card, or at viewport center
      let posX, posY;
      if (sourceCardId) {
        const sourceNode = nodes.find(n => n.id === sourceCardId);
        if (sourceNode) {
          const srcW = sourceNode.measured?.width || sourceNode.style?.width || 280;
          posX = sourceNode.position.x + srcW + 60;
          posY = sourceNode.position.y;
        }
      }
      if (posX == null) {
        const vp = reactFlow.getViewport();
        posX = (-vp.x + window.innerWidth / 2) / vp.zoom + 160;
        posY = (-vp.y + window.innerHeight / 2) / vp.zoom;
      }
      const card = await createCard(boardId, {
        card_type: 'note',
        title: text.slice(0, 60),
        content: text,
        position_x: posX,
        position_y: posY,
      });
      setNodes((nds) => [...nds, cardToNode(card)]);
      // Create edge linking source → new card
      if (sourceCardId) {
        try {
          const edge = await apiCreateEdge(boardId, {
            from_card_id: sourceCardId,
            to_card_id: card.id,
            edge_type: 'derived_from',
            source_handle: 'right',
            target_handle: 'left',
          });
          setEdges((eds) => [...eds, edgeToFlow(edge)]);
        } catch (edgeErr) {
          console.error('Failed to create extract edge:', edgeErr);
        }
      }
    } catch (err) {
      console.error('Failed to extract to card:', err);
    }
  }, [boardId, reactFlow, nodes, setNodes, setEdges]);

  // Pipeline helpers
  const hasPipelineNodes = useMemo(() => nodes.some(n => n.data?.card_type?.startsWith('pl_')), [nodes]);

  const handleAddPipelineNode = useCallback(async (plType) => {
    const vp = reactFlow.getViewport();
    const centerX = (-vp.x + window.innerWidth / 2) / vp.zoom;
    const centerY = (-vp.y + window.innerHeight / 2) / vp.zoom;
    const labels = { pl_input: 'Input', pl_llm: 'LLM', pl_council: 'Council', pl_transform: 'Transform', pl_output: 'Output', pl_conditional: 'Conditional' };
    try {
      const card = await createCard(boardId, {
        card_type: plType,
        title: labels[plType] || plType,
        position_x: centerX,
        position_y: centerY,
        width: 220,
        extra: { model: 'openai/gpt-4o' },
      });
      setNodes(nds => [...nds, cardToNode(card)]);
    } catch (err) {
      console.error('Failed to create pipeline node:', err);
    }
  }, [boardId, reactFlow, setNodes]);

  // Section handlers
  const handleAddSection = useCallback(async () => {
    // If 2+ non-section cards are selected, group them into a section
    const cardNodes = selectedNodes.filter((n) => n.type !== 'sectionNode');
    if (cardNodes.length >= 2) {
      try {
        const cardIds = cardNodes.map((n) => n.id);

        // Compute bounding box from actual rendered node dimensions
        const padding = 60;
        const headerOffset = 44;
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (const node of cardNodes) {
          const rfNode = reactFlow.getNode(node.id);
          const w = rfNode?.measured?.width ?? rfNode?.width ?? node.style?.width ?? 280;
          const h = rfNode?.measured?.height ?? rfNode?.height ?? 200;
          const x = node.position.x;
          const y = node.position.y;
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x + w);
          maxY = Math.max(maxY, y + h);
        }

        const result = await groupIntoSection(boardId, {
          card_ids: cardIds,
          bounds_x: minX - padding,
          bounds_y: minY - padding - headerOffset,
          bounds_width: (maxX - minX) + padding * 2,
          bounds_height: (maxY - minY) + padding * 2 + headerOffset,
        });
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
        x: centerX - 300,
        y: centerY - 200,
        width: 600,
        height: 400,
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
                const headerOffset = 44;
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

  // ── Explicit merge of selected cards ──────────────────────────────
  const handleMergeSelected = useCallback(async () => {
    const cardNodes = selectedNodes.filter(n => n.type === 'canvasCard');
    if (cardNodes.length < 2) return;
    // Merge into the first selected card, absorbing the rest
    const targetId = cardNodes[0].id;
    try {
      let currentTarget = targetId;
      for (let i = 1; i < cardNodes.length; i++) {
        const merged = await mergeCards(boardId, currentTarget, cardNodes[i].id);
        currentTarget = merged.id;
      }
      // Reload all cards by removing merged sources and updating target
      const sourceIds = new Set(cardNodes.slice(1).map(n => n.id));
      setNodes(nds => nds.filter(n => !sourceIds.has(n.id)));
      // Reload edges
      const edgesData = await listEdges(boardId);
      setEdges((edgesData.edges || edgesData).map(edgeToFlow));
      // Refresh target card data
      stableUpdateCard(currentTarget, {});
    } catch (err) {
      console.error('Failed to merge cards:', err);
    }
  }, [selectedNodes, boardId, setNodes, setEdges, stableUpdateCard]);

  // ── Split / unmerge a previously merged card ─────────────────────────
  const handleSplitCard = useCallback(async (cardId) => {
    try {
      const result = await splitCard(boardId, cardId);
      // Update the target card in-place (content restored, provenance cleared)
      setNodes((nds) => {
        const updated = nds.map((n) =>
          n.id === cardId ? cardToNode(result.target) : n
        );
        // Add restored cards
        const restoredNodes = result.restored.map(cardToNode);
        return [...updated, ...restoredNodes];
      });
    } catch (err) {
      console.error('Failed to split card:', err);
    }
  }, [boardId, setNodes]);

  // ── Duplicate a single card ────────────────────────────────────────
  const handleDuplicateCard = useCallback(async (cardId, offsetX = 40, offsetY = 40) => {
    const node = nodes.find((n) => n.id === cardId);
    if (!node || node.type !== 'canvasCard') return;
    try {
      const card = await createCard(boardId, {
        card_type: node.data.card_type || 'note',
        title: node.data.title || '',
        content: node.data.content || '',
        position_x: node.position.x + offsetX,
        position_y: node.position.y + offsetY,
        width: node.measured?.width || node.data.width || 280,
      });
      setNodes((nds) => [...nds, cardToNode(card)]);
    } catch (err) {
      console.error('Failed to duplicate card:', err);
    }
  }, [boardId, nodes, setNodes]);

  // Alt+drag: duplicate the card and leave original in place
  const altDragRef = useRef(null);
  const handleNodeDragStart = useCallback((event, node) => {
    if (event.sourceEvent?.altKey && node.type === 'canvasCard') {
      // Clone the card at the original position
      altDragRef.current = { nodeId: node.id, origPos: { ...node.position } };
      createCard(boardId, {
        card_type: node.data.card_type || 'note',
        title: node.data.title || '',
        content: node.data.content || '',
        position_x: node.position.x,
        position_y: node.position.y,
        width: node.measured?.width || node.data.width || 280,
      }).then((card) => {
        setNodes((nds) => [...nds, cardToNode(card)]);
      }).catch((err) => console.error('Alt+drag duplicate failed:', err));
    } else {
      altDragRef.current = null;
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

  // Tab management
  const MAX_TABS = 8;
  const openTab = useCallback((cardId) => {
    const node = nodes.find(n => n.id === cardId);
    if (!node) return;
    setOpenTabs(prev => {
      if (prev.find(t => t.cardId === cardId)) return prev;
      const newTab = { id: `tab-${cardId}`, cardId, title: node.data.title || 'Untitled', cardType: node.data.card_type };
      const updated = [...prev, newTab];
      return updated.length > MAX_TABS ? updated.slice(updated.length - MAX_TABS) : updated;
    });
    setActiveTabId(`tab-${cardId}`);
  }, [nodes]);

  const closeTab = useCallback((tabId) => {
    setOpenTabs(prev => {
      const updated = prev.filter(t => t.id !== tabId);
      if (activeTabId === tabId && updated.length > 0) {
        setActiveTabId(updated[updated.length - 1].id);
        setSidePanelCardId(updated[updated.length - 1].cardId);
      } else if (updated.length === 0) {
        setActiveTabId(null);
        setSidePanelCardId(null);
      }
      return updated;
    });
  }, [activeTabId]);

  const handleTabSelect = useCallback((cardId) => {
    setActiveTabId(`tab-${cardId}`);
    setSidePanelCardId(cardId);
  }, []);

  // Track recent cards (last 20)
  const trackRecent = useCallback((cardId) => {
    const node = nodes.find(n => n.id === cardId);
    if (!node) return;
    setRecentCards(prev => {
      const filtered = prev.filter(r => r.id !== cardId);
      return [{ id: cardId, title: node.data.title, card_type: node.data.card_type }, ...filtered].slice(0, 20);
    });
  }, [nodes]);

  // Side panel open/close (also opens a tab + tracks recent)
  const openSidePanel = useCallback((cardId) => {
    setSidePanelCardId(cardId);
    openTab(cardId);
    trackRecent(cardId);
  }, [openTab, trackRecent]);
  const closeSidePanel = useCallback(() => {
    setSidePanelCardId(null);
  }, []);

  // Side panel card data (derived from nodes)
  const sidePanelCard = useMemo(() => {
    if (!sidePanelCardId) return null;
    const node = nodes.find(n => n.id === sidePanelCardId);
    if (!node) return null;
    return {
      id: node.id,
      board_id: boardId,
      card_type: node.data.card_type,
      title: node.data.title,
      content: node.data.content,
      color: node.data.color,
      section_id: node.data.section_id,
      created_at: node.data.extra?.created_at || node.data.created_at,
      updated_at: node.data.extra?.updated_at || node.data.updated_at,
      extra: node.data.extra,
    };
  }, [sidePanelCardId, nodes, boardId]);

  // When side panel saves changes, sync into node state
  const handleSidePanelCardUpdated = useCallback((cardId, updates) => {
    setNodes(nds => nds.map(n =>
      n.id === cardId ? { ...n, data: { ...n.data, ...updates } } : n
    ));
  }, [setNodes]);

  // Board context value — provides editing callbacks directly to CanvasCard via React context
  // This bypasses node data injection timing issues and works for newly created cards immediately
  const boardContextValue = useMemo(() => ({
    editingCardId,
    startEditing: stableStartEditing,
    clearEditing: stableClearEditing,
    updateCard: stableUpdateCard,
    focusCard: stableFocusCard,
    extractToCard: handleExtractToCard,
    openSidePanel,
    closeSidePanel,
    sidePanelCardId,
  }), [editingCardId, stableStartEditing, stableClearEditing, stableUpdateCard, stableFocusCard, handleExtractToCard, openSidePanel, closeSidePanel, sidePanelCardId]);

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

  // Refs for section callbacks (populated after callbacks are defined below)
  const sectionCallbacksRef = useRef({});

  // Single combined effect for ALL node data injection (prevents cascading setNodes loops)
  useEffect(() => {
    setNodes((nds) => {
      const boardCards = nds.map((n) => ({ id: n.id, card_type: n.data.card_type, title: n.data.title, extra: n.data.extra }));
      const callbacks = sectionCallbacksRef.current;

      // Compute section child counts inline
      const childCounts = {};
      for (const n of nds) {
        if (n.parentId && n.type !== 'sectionNode') {
          childCounts[n.parentId] = (childCounts[n.parentId] || 0) + 1;
        }
      }

      return nds.map((n) => {
        // Determine hidden state for collapsed sections
        let hidden = false;
        if (n.parentId && collapsedSections.has(n.parentId)) {
          hidden = true;
        }

        const base = {
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
        };

        // Inject pipeline execution state for pipeline nodes
        if (n.type === 'pipelineNode') {
          base.pipelineStatus = pipeline.nodeStatuses[n.id] || 'idle';
          base.pipelineOutput = pipeline.nodeOutputs[n.id] || null;
        }

        // Inject section-specific callbacks
        if (n.type === 'sectionNode') {
          base.onUpdateSection = callbacks.onUpdateSection;
          base.onDeleteSection = callbacks.onDeleteSection;
          base.onUngroupSection = callbacks.onUngroupSection;
          base.onToggleCollapse = callbacks.onToggleCollapse;
          base.childCount = childCounts[n.id] || 0;
        }

        return { ...n, data: base, hidden };
      });
    });
  }, [backlinksMap, stableFocusCard, stableUpdateCard, highlightedCards, processingCards, editingCardId, stableClearEditing, stableStartEditing, propertyBadgesByCard, pipeline.nodeStatuses, pipeline.nodeOutputs, collapsedSections, setNodes]);

  // Inject onUpdateEdge callback into edge data so AnimatedEdge can trigger label edits
  const handleUpdateEdgeRef = useRef(handleUpdateEdge);
  handleUpdateEdgeRef.current = handleUpdateEdge;
  useEffect(() => {
    setEdges((eds) => eds.map((e) => ({
      ...e,
      data: { ...e.data, onUpdateEdge: handleUpdateEdgeRef.current },
    })));
  // Only re-run when edges are first loaded, not on every handleUpdateEdge change
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setEdges]);

  // Section collapse toggle handler
  const handleToggleCollapse = useCallback((sectionId, isCollapsed) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      const nodeId = `section-${sectionId}`;
      if (isCollapsed) next.add(nodeId);
      else next.delete(nodeId);
      return next;
    });
  }, []);

  // Populate section callbacks ref (must be after all callbacks are defined)
  sectionCallbacksRef.current = {
    onUpdateSection: handleUpdateSection,
    onDeleteSection: handleDeleteSection,
    onUngroupSection: handleUngroupSection,
    onToggleCollapse: handleToggleCollapse,
  };

  // Load recent cards from localStorage on mount
  useEffect(() => {
    if (!boardId) return;
    try {
      const stored = localStorage.getItem(`canvas-recent-${boardId}`);
      if (stored) setRecentCards(JSON.parse(stored));
    } catch { /* ignore */ }
  }, [boardId]);

  // Persist recent cards to localStorage whenever they change
  useEffect(() => {
    if (!boardId || recentCards.length === 0) return;
    try { localStorage.setItem(`canvas-recent-${boardId}`, JSON.stringify(recentCards)); } catch { /* ignore */ }
  }, [recentCards, boardId]);

  const handleRecentSelect = useCallback((cardId) => {
    const node = nodes.find((n) => n.id === cardId);
    if (node) {
      reactFlow.setCenter(node.position.x + 140, node.position.y + 100, { zoom: 1.2, duration: 400 });
      setNodes((nds) => nds.map((n) => ({ ...n, selected: n.id === cardId })));
    }
  }, [nodes, reactFlow, setNodes]);

  // Collapse / Expand all cards
  const handleCollapseAll = useCallback(() => {
    setNodes((nds) => nds.map((n) => {
      if (n.type !== 'canvasCard') return n;
      const extra = { ...(n.data.extra || {}), collapsed: true };
      stableUpdateCard(n.id, { extra });
      return { ...n, data: { ...n.data, extra } };
    }));
  }, [setNodes, stableUpdateCard]);

  const handleExpandAll = useCallback(() => {
    setNodes((nds) => nds.map((n) => {
      if (n.type !== 'canvasCard') return n;
      const extra = { ...(n.data.extra || {}), collapsed: false };
      stableUpdateCard(n.id, { extra });
      return { ...n, data: { ...n.data, extra } };
    }));
  }, [setNodes, stableUpdateCard]);

  // Toggle collapse on selected card(s)
  const handleToggleCardCollapse = useCallback(() => {
    if (selectedNodes.length === 0) return;
    setNodes((nds) => nds.map((n) => {
      if (!n.selected || n.type !== 'canvasCard') return n;
      const collapsed = !(n.data.extra?.collapsed);
      const extra = { ...(n.data.extra || {}), collapsed };
      stableUpdateCard(n.id, { extra });
      return { ...n, data: { ...n.data, extra } };
    }));
  }, [selectedNodes, setNodes, stableUpdateCard]);

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
    onToggleCollapse: handleToggleCardCollapse,
  });

  // Double-click node to open side panel or navigate to sub-board
  const handleNodeDoubleClick = useCallback((_event, node) => {
    // Navigate to sub-board
    if (node.data?.card_type === 'board_ref' && node.data?.extra?.target_board_id) {
      const targetId = node.data.extra.target_board_id;
      navigate(`/boards/${targetId}`);
      return;
    }
    // Open side panel (also opens tab + tracks recent)
    openSidePanel(node.id);
  }, [navigate, openSidePanel]);

  // Single-click node: if side panel is already open, switch to the clicked card
  const handleNodeClick = useCallback((_event, node) => {
    if (sidePanelCardId && node.id !== sidePanelCardId) {
      openSidePanel(node.id);
    }
  }, [sidePanelCardId, openSidePanel]);

  // Context menu
  const handleNodeContextMenu = useCallback((event, node) => {
    event.preventDefault();
    setContextMenu({ nodeId: node.id, x: event.clientX, y: event.clientY });
  }, []);
  const handleCloseContextMenu = useCallback(() => { setContextMenu(null); setEdgeMenu(null); }, []);

  // Edge context menu (right-click on edge)
  const handleEdgeContextMenu = useCallback((event, edge) => {
    event.preventDefault();
    setContextMenu(null);
    setEdgeMenu({ edgeId: edge.id, x: event.clientX, y: event.clientY });
  }, []);

  // Trigger inline label editing on an edge (from context menu "Edit Label")
  const handleEditEdgeLabel = useCallback((edgeId) => {
    setEdges((eds) => eds.map((e) =>
      e.id === edgeId ? { ...e, data: { ...e.data, editingLabel: true } } : e
    ));
  }, [setEdges]);

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
    // Section nodes: use section color or a muted default
    if (node.type === 'sectionNode') {
      const SECTION_COLORS = {
        gray: '#94a3b8', blue: '#3b82f6', green: '#10b981', purple: '#8b5cf6',
        yellow: '#f59e0b', red: '#ef4444', pink: '#ec4899', orange: '#f97316',
      };
      return SECTION_COLORS[node.data?.color] || '#cbd5e1';
    }
    switch (node.data?.card_type) {
      case 'query': return '#6366f1';
      case 'council_response': return '#f59e0b';
      case 'council_synthesis': return '#10b981';
      case 'file_ref': return '#94a3b8';
      case 'link': return '#3b82f6';
      case 'pl_input': return '#10b981';
      case 'pl_llm': return '#3b82f6';
      case 'pl_council': return '#8b5cf6';
      case 'pl_transform': return '#f59e0b';
      case 'pl_output': return '#64748b';
      case 'pl_conditional': return '#eab308';
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
        boardUsers={boardUsers}
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
        onToggleAssets={() => setShowAssetBrowser((p) => !p)}
        onToggleMarketplace={() => setShowMarketplace((p) => !p)}
        onToggleExport={() => setShowExportDialog((p) => !p)}
        onToggleIntegrations={() => setShowIntegrations((p) => !p)}
        onAddPipelineNode={handleAddPipelineNode}
        hasPipelineNodes={hasPipelineNodes}
        onRunPipeline={pipeline.run}
        pipelineRunning={pipeline.running}
        onAutoLayout={applyAutoLayout}
        onTidyUp={tidyUp}
        recentCards={recentCards}
        onRecentSelect={handleRecentSelect}
        onCollapseAll={handleCollapseAll}
        onExpandAll={handleExpandAll}
      />

      {openTabs.length > 0 && (
        <TabBar
          tabs={openTabs}
          activeTabId={activeTabId}
          onTabSelect={handleTabSelect}
          onTabClose={closeTab}
        />
      )}

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
        <div style={{ display: 'flex', flex: 1, position: 'relative', overflow: 'hidden' }}>
        <div
          className={`board-view__canvas${cardDragOver ? ' board-view__canvas--drag-over' : ''}`}
          style={sidePanelCard ? { flex: 1 } : undefined}
          onDragOver={(e) => {
            if (
              e.dataTransfer.types.includes('application/x-council-card') ||
              e.dataTransfer.types.includes('text/plain')
            ) {
              e.preventDefault();
              e.dataTransfer.dropEffect = 'copy';
              if (!cardDragOver) setCardDragOver(true);
            }
          }}
          onDragLeave={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget)) setCardDragOver(false);
          }}
          onDrop={async (e) => {
            setCardDragOver(false);
            const raw = e.dataTransfer.getData('application/x-council-card');
            const plainText = e.dataTransfer.getData('text/plain');
            if (!raw && !plainText) return;
            e.preventDefault();
            try {
              const position = reactFlow.screenToFlowPosition({ x: e.clientX, y: e.clientY });

              // If we have structured card data, use it
              if (raw) {
                const { text, title, sourceCardId, action, card_type } = JSON.parse(raw);

                // Library drop: link or clone from another board
                if (sourceCardId && (action === 'link' || action === 'clone')) {
                  let newCard;
                  if (action === 'link') {
                    newCard = await linkCard(sourceCardId, {
                      target_board_id: boardId,
                      position_x: position.x,
                      position_y: position.y,
                    });
                  } else {
                    newCard = await cloneCard(sourceCardId, {
                      target_board_id: boardId,
                      position_x: position.x,
                      position_y: position.y,
                    });
                  }
                  setNodes((nds) => [...nds, cardToNode(newCard)]);
                  return;
                }

                // Regular card drop with source tracking
                const newCard = await createCard(boardId, {
                  card_type: card_type || 'note',
                  title: title || (text && text.slice(0, 60)) || '',
                  content: text || '',
                  position_x: position.x,
                  position_y: position.y,
                });
                setNodes((nds) => [...nds, cardToNode(newCard)]);
                if (sourceCardId) {
                  try {
                    const edge = await apiCreateEdge(boardId, {
                      from_card_id: sourceCardId,
                      to_card_id: newCard.id,
                      edge_type: 'derived_from',
                    });
                    setEdges((eds) => [...eds, edgeToFlow(edge)]);
                  } catch (edgeErr) {
                    console.error('Failed to create edge from drop:', edgeErr);
                  }
                }
                return;
              }

              // Fallback: plain text drop (native text drag without custom data)
              const text = plainText.trim();
              if (text.length < 3) return;
              const newCard = await createCard(boardId, {
                card_type: 'note',
                title: text.slice(0, 60),
                content: text,
                position_x: position.x,
                position_y: position.y,
              });
              setNodes((nds) => [...nds, cardToNode(newCard)]);
            } catch (err) {
              console.error('Failed to create card from drop:', err);
            }
          }}
        >
          <BoardContext.Provider value={boardContextValue}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={handleConnect}
            onMoveEnd={handleMoveEnd}
            onNodeClick={handleNodeClick}
            onNodeDoubleClick={handleNodeDoubleClick}
            onNodeContextMenu={handleNodeContextMenu}
            onEdgeContextMenu={handleEdgeContextMenu}
            onNodeDragStart={handleNodeDragStart}
            onNodeDrag={handleAlignDrag}
            onNodeDragStop={handleAlignDragStop}
            onPaneClick={handleCloseContextMenu}
            onPaneMouseMove={(e) => handleCollabMouseMove(e, reactFlow.getViewport())}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            defaultViewport={defaultViewport}
            connectionMode="loose"
            nodeDragThreshold={2}
            snapToGrid
            snapGrid={[16, 16]}
            fitView={!board?.viewport}
            deleteKeyCode={null}
            multiSelectionKeyCode="Shift"
            elevateNodesOnSelect
            minZoom={0.1}
            maxZoom={4}
          >
            <Background gap={16} size={1} color="var(--border-primary)" />
            <Controls />
            <MiniMap nodeColor={minimapNodeColor} maskColor="var(--bg-overlay)" />
            {alignmentGuides.length > 0 && (
              <svg className="react-flow__alignment-guides" style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 5 }}>
                {alignmentGuides.map((g, i) => {
                  const vp = reactFlow.getViewport();
                  const x1 = g.x1 * vp.zoom + vp.x;
                  const y1 = g.y1 * vp.zoom + vp.y;
                  const x2 = g.x2 * vp.zoom + vp.x;
                  const y2 = g.y2 * vp.zoom + vp.y;
                  return (
                    <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#6366f1" strokeWidth="1" strokeDasharray="4 2" />
                  );
                })}
              </svg>
            )}
          </ReactFlow>
          <SelectionToolbar
            selectedNodes={selectedNodes}
            onGroup={handleAddSection}
            onUngroup={handleUngroupSection}
            onDelete={handleDeleteSelected}
            onMerge={handleMergeSelected}
            onAlign={alignSelected}
            reactFlowInstance={reactFlow}
          />
          <CollaborationOverlay remoteCursors={remoteCursors} viewport={reactFlow.getViewport()} />
          </BoardContext.Provider>
        </div>
        {sidePanelCard && (
          <CardSidePanel
            card={sidePanelCard}
            boardId={boardId}
            edges={edges}
            nodes={nodes}
            onClose={closeSidePanel}
            onCardUpdated={handleSidePanelCardUpdated}
            onNavigateToCard={openSidePanel}
            onExtractToCard={handleExtractToCard}
          />
        )}
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
          isLibrary={nodes.find((n) => n.id === contextMenu.nodeId)?.data?.is_library}
          sourceCardId={nodes.find((n) => n.id === contextMenu.nodeId)?.data?.source_card_id}
          hasMergeProvenance={Array.isArray(nodes.find((n) => n.id === contextMenu.nodeId)?.data?.extra?.merged_from) && nodes.find((n) => n.id === contextMenu.nodeId)?.data?.extra?.merged_from.length > 0}
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
          onUnlink={async (cardId) => {
            setContextMenu(null);
            try {
              const updated = await unlinkCard(cardId);
              setNodes((nds) => nds.map((n) =>
                n.id === cardId ? cardToNode(updated) : n
              ));
            } catch (err) {
              console.error('Failed to unlink card:', err);
            }
          }}
          onGoToSource={(sourceId) => {
            setContextMenu(null);
            const sourceNode = nodes.find((n) => n.id === sourceId);
            if (sourceNode) {
              reactFlow.fitView({ nodes: [sourceNode], duration: 300 });
            }
          }}
          onToggleLibrary={async (cardId) => {
            try {
              const { toggleLibrary } = await import('../../../api/cardSearch.js');
              const updated = await toggleLibrary(cardId);
              setNodes((nds) => nds.map((n) =>
                n.id === cardId ? { ...n, data: { ...n.data, is_library: updated.is_library } } : n
              ));
            } catch (err) {
              console.error('Failed to toggle library:', err);
            }
          }}
          onDuplicate={handleDuplicateCard}
          onSplit={handleSplitCard}
        />
      )}

      {edgeMenu && (
        <EdgeContextMenu
          x={edgeMenu.x}
          y={edgeMenu.y}
          edgeId={edgeMenu.edgeId}
          edgeData={edges.find((e) => e.id === edgeMenu.edgeId)?.data}
          onEditLabel={handleEditEdgeLabel}
          onUpdateEdge={handleUpdateEdge}
          onReverse={handleReverseEdge}
          onDelete={handleDeleteEdge}
          onClose={() => setEdgeMenu(null)}
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
        <Suspense fallback={<div className="board-view__panel-loading">Loading...</div>}>
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
        </Suspense>
      )}

      {wf.running && (
        <Suspense fallback={null}>
        <WorkflowRunner
          currentStep={wf.currentStep}
          waitingReview={wf.waitingReview}
          onApprove={() => wf.approveStep(wf.activeWorkflow?.id)}
          onCancel={() => wf.cancelWorkflow(wf.activeWorkflow?.id)}
        />
        </Suspense>
      )}

      {showAgentPanel && (
        <Suspense fallback={<div className="board-view__panel-loading">Loading...</div>}>
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
        </Suspense>
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

      {showAssetBrowser && (
        <Suspense fallback={<div className="board-view__panel-loading">Loading...</div>}>
          <AssetBrowser
            projectId={board?.project_id}
            onClose={() => setShowAssetBrowser(false)}
            onPlaceOnBoard={(asset) => {
              handleAddCard('image', {
                title: asset.name,
                content: asset.url ? `![${asset.name}](${asset.url})` : asset.name,
              });
              setShowAssetBrowser(false);
            }}
          />
        </Suspense>
      )}

      {showMarketplace && (
        <Suspense fallback={<div className="board-view__panel-loading">Loading...</div>}>
          <TemplateMarketplace
            boardId={boardId}
            onClose={() => setShowMarketplace(false)}
            onApplyTemplate={() => {
              // Refresh board after template applied
              window.location.reload();
            }}
          />
        </Suspense>
      )}

      {showExportDialog && (
        <Suspense fallback={<div className="board-view__panel-loading">Loading...</div>}>
          <ExportDialog
            boardId={boardId}
            boardName={board?.name}
            onClose={() => setShowExportDialog(false)}
          />
        </Suspense>
      )}

      {showIntegrations && (
        <Suspense fallback={<div className="board-view__panel-loading">Loading...</div>}>
          <IntegrationPanel
            boardId={boardId}
            onClose={() => setShowIntegrations(false)}
          />
        </Suspense>
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
