# UX Improvement Plan

> No tutorials/onboarding. Focus on reducing redundancy and cleaning up the interface.

---

## Summary of Changes

| Change | Files | Effort |
|--------|-------|--------|
| Remove header settings panel | ChatInterface.jsx, ChatInterface.css | Small |
| Consolidate settings into tabbed modal | Settings.jsx, Settings.css | Medium |
| Improve model picker UX | ChatInterface.jsx, ChatInterface.css | Medium |
| Clean up header | ChatInterface.jsx | Small |

---

## Phase 1: Remove Redundant Header Settings

### Problem
Two places to access settings:
- Sidebar gear → Full Settings modal (API Keys, Models, Presets)
- Chat Header gear → Inline panel (Features, Memory, Instructions)

This is confusing. Users don't know which settings is which.

### Solution
Remove the inline settings panel from ChatInterface. Move Features/Memory/Instructions into the main Settings modal as new tabs.

### Changes

**ChatInterface.jsx**
1. Remove `showSettings` state and `setShowSettings`
2. Remove `features`, `memoryContext`, `memoryStats`, `systemInstructions` state
3. Remove `loadMemory`, `saveInstructions`, `toggleFeature`, `handleClearMemory` functions
4. Remove the settings button in header (line ~1224-1233)
5. Remove the entire `{showSettings && ...}` settings panel block (lines ~1237-1326)

**Settings.jsx** - Add new tabs:
1. Add "Features" tab with toggles (Memory, Web Search, Deep Search, Code Execution)
2. Add "Memory" tab with memory view, stats, and clear button
3. Add "Instructions" tab with system instructions textarea

**Tab structure becomes:**
```
[ Routing | API Keys | Models | Features | Memory | Instructions ]
```

---

## Phase 2: Clean Up Header

### Current Header
```
[Mode Tabs] [Model Selector/Auto/Council Badge] ... [Export] [Shortcuts] [Settings]
```

### Problem
- Settings button removed (Phase 1)
- Export button only shows when conversation has messages
- Shortcuts button is rarely used
- Header feels cluttered

### New Header
```
[Mode Tabs] [Model Selector/Auto/Council Badge] ... [Shortcuts ⌘?]
```

### Changes

**ChatInterface.jsx**
1. Remove settings button (done in Phase 1)
2. Move Export to message context menu (three-dot menu on hover)
3. Keep Shortcuts button but make it more compact (just keyboard icon, tooltip shows "⌘?")

**ChatInterface.css**
1. Adjust header spacing after removing elements
2. Clean up orphaned styles

---

## Phase 3: Improve Model Picker

### Current Problems
1. Long scrolling list (50+ models)
2. No visual hierarchy
3. Search is required for usability
4. Groups show max 5 models without search

### Solution
Better categorization + visual improvements (no search required for common use)

### Changes

**Model Picker Structure**
```
┌─────────────────────────────────┐
│ ⭐ Favorites (pinned at top)    │
│ ────────────────────────────── │
│ ⏱️ Recent (last 3, not 5)       │
│ ────────────────────────────── │
│ 🔥 Popular (top 6 models)       │
│ ────────────────────────────── │
│ ▼ Anthropic (expandable)        │
│ ▼ OpenAI (expandable)           │
│ ▼ Google (expandable)           │
│ ▼ Other Providers...            │
└─────────────────────────────────┘
```

**ChatInterface.jsx**
1. Reduce `MAX_RECENT_MODELS` from 5 to 3
2. Make provider groups collapsible (accordion style)
3. Show Popular section with 6 models (current top picks)
4. Add dividers between sections for visual clarity

**ChatInterface.css**
1. Add accordion chevron for collapsed/expanded groups
2. Add subtle dividers between sections
3. Increase max-height slightly to reduce scrolling
4. Add visual hierarchy with different text weights

---

## Phase 4: Settings Modal Improvements

### Current Problems
1. All settings in single scroll view
2. No clear organization
3. Tabs exist but could be clearer

### Solution
Clean tab organization with clear purpose per tab

### Final Tab Structure

| Tab | Contains |
|-----|----------|
| **Routing** | Auto-routing config, model routing rules |
| **API Keys** | Provider API keys with status indicators |
| **Council** | Council models + Chairman + Presets |
| **Features** | Toggle switches (Memory, Web, Code, etc.) |
| **Memory** | View/clear memory, stats |
| **System** | System instructions, export/import config |

**Settings.jsx**
1. Rename "Models" tab to "Council"
2. Add "Features" tab (from ChatInterface)
3. Add "Memory" tab (from ChatInterface)
4. Rename/add "System" tab for system instructions + config backup

**Settings.css**
1. Ensure consistent tab styling
2. Add icons to tab labels for quick recognition
3. Keep compact but readable

---

## Implementation Order

1. **Phase 1** - Remove inline settings (ChatInterface.jsx cleanup)
2. **Phase 4** - Add tabs to Settings.jsx (Features, Memory, System)
3. **Phase 2** - Clean up header (remove settings btn, compact shortcuts)
4. **Phase 3** - Model picker improvements (accordion, dividers)

This order ensures we don't break functionality - we add new tabs before removing old UI.

---

## Files to Modify

```
frontend/src/components/
├── ChatInterface.jsx    # Remove inline settings, clean header
├── ChatInterface.css    # Remove orphaned styles, adjust header
├── Settings.jsx         # Add Features, Memory, System tabs
└── Settings.css         # Tab styling updates
```

---

## Success Criteria

- [ ] Single settings location (sidebar gear only)
- [ ] All features accessible from Settings modal
- [ ] Header has only essential controls
- [ ] Model picker works without search for common models
- [ ] No broken functionality
- [ ] Clean, uncluttered interface
