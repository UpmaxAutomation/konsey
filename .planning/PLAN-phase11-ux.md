# Phase 11: Claude-Like UX/UI Redesign

## Overview
**Priority**: 🟡 HIGH (User requested)
**Estimated Time**: 8-12 hours
**Impact**: Major UX improvement, professional polish

## Reference: Claude's Sidebar Structure

Based on screenshots provided:

```
┌─────────────────────────────────┐
│ Claude                      [≡] │
├─────────────────────────────────┤
│ [+ New chat]                    │
│ 🔍 Search                       │
│ 💬 Chats                        │
│ 📁 Projects                     │
│ 📦 Artifacts                    │
│ </> Code                        │
├─────────────────────────────────┤
│ ⭐ Starred                      │
│   • Project 1                   │
│   • Project 2                   │
├─────────────────────────────────┤
│ 🕐 Recents                      │
│   • Chat 1                      │
│   • Chat 2                      │
│   • Chat 3                      │
│   ...                           │
├─────────────────────────────────┤
│ [Avatar] User Name              │
│          Plan Type              │
└─────────────────────────────────┘
```

## Current LLM Council Sidebar Issues
1. Folders/Tags system is complex
2. No clear Projects concept
3. No Starred section
4. No search
5. Settings scattered
6. 26+ useState hooks (maintenance nightmare)

---

## Task 11.1: New Sidebar Layout Structure

<task type="auto">
  <name>Create new Sidebar component structure</name>
  <files>frontend/src/components/Sidebar.jsx</files>
  <action>
    Restructure sidebar into clear sections:

    1. **Header**
       - Logo/Brand
       - Collapse toggle

    2. **Primary Actions**
       - New Council (primary button)
       - Search (opens modal/inline)

    3. **Navigation**
       - Councils (conversations)
       - Projects
       - Presets (like Artifacts)
       - Settings

    4. **Starred Section**
       - User-starred conversations/projects

    5. **Recents Section**
       - Recent conversations (last 10-20)

    6. **User Profile (bottom)**
       - Avatar
       - Name
       - Budget/usage indicator
  </action>
</task>

### New Component Hierarchy
```
Sidebar/
├── SidebarHeader.jsx        # Logo, collapse toggle
├── SidebarNav.jsx           # Primary navigation items
├── SidebarSearch.jsx        # Search modal/inline
├── StarredSection.jsx       # Starred items
├── RecentsSection.jsx       # Recent conversations
├── UserProfile.jsx          # Bottom user info
└── index.jsx                # Main Sidebar orchestrator
```

---

## Task 11.2: Projects Feature (Claude-style)

<task type="auto">
  <name>Implement Projects system</name>
  <files>
    frontend/src/pages/Projects.jsx (new)
    frontend/src/pages/ProjectDetail.jsx (new)
    frontend/src/components/ProjectCard.jsx (new)
    backend/projects.py (enhance)
  </files>
  <action>
    Create Claude-like Projects view:

    1. **Projects List View** (`/projects`)
       - Search projects bar
       - "New project" button
       - Grid of project cards
       - Sort by: Activity, Name, Created
       - Each card shows:
         - Project name
         - Description (optional)
         - Last updated timestamp
         - Conversation count

    2. **Project Detail View** (`/projects/:id`)
       - Breadcrumb: "← All projects"
       - Project title (editable)
       - Star/favorite toggle
       - Right panel:
         - **Memory**: Project context/summary
         - **Instructions**: Custom system prompt
         - **Files**: Attached documents
       - Main area: Conversations in this project
       - New conversation within project

    3. **Backend Enhancements**
       - Project CRUD endpoints (already exist, enhance)
       - Project-conversation association
       - Project instructions storage
       - Project files attachment
  </action>
</task>

### Project Data Model
```typescript
interface Project {
  id: string;
  name: string;
  description?: string;
  instructions?: string;      // Custom system prompt
  memory?: string;            // Context/summary
  files?: ProjectFile[];      // Attached documents
  conversations: string[];    // Conversation IDs
  starred: boolean;
  created_at: string;
  updated_at: string;
  owner_id: string;
}

interface ProjectFile {
  id: string;
  name: string;
  type: 'pdf' | 'txt' | 'md' | 'doc';
  url: string;
  uploaded_at: string;
}
```

---

## Task 11.3: Starred Functionality

<task type="auto">
  <name>Add starring for conversations and projects</name>
  <files>
    frontend/src/components/StarredSection.jsx (new)
    backend/storage.py (enhance)
  </files>
  <action>
    1. Add `starred` field to conversations
    2. Add star toggle button on conversation items
    3. Create StarredSection component
    4. Filter starred items across conversations + projects
    5. Persist starred state to backend
    6. Show star icon (filled/outline) on items
  </action>
</task>

---

## Task 11.4: Search Functionality

<task type="auto">
  <name>Add global search</name>
  <files>
    frontend/src/components/SidebarSearch.jsx (new)
    frontend/src/components/SearchModal.jsx (new)
    backend/search.py (new)
  </files>
  <action>
    1. Add search icon in sidebar
    2. Click opens search modal (Cmd+K shortcut)
    3. Search across:
       - Conversation titles
       - Conversation content
       - Project names
       - Project instructions
    4. Show results grouped by type
    5. Click result navigates to item
    6. Recent searches history
  </action>
</task>

### Search UI
```
┌─────────────────────────────────────┐
│ 🔍 Search conversations, projects...│
├─────────────────────────────────────┤
│ Recent                              │
│   • "API design"                    │
│   • "Budget tracking"               │
├─────────────────────────────────────┤
│ Conversations                       │
│   💬 Council query about React...   │
│   💬 Voting on database choice...   │
├─────────────────────────────────────┤
│ Projects                            │
│   📁 UPMAX Dev                      │
│   📁 Yasemin Law                    │
└─────────────────────────────────────┘
```

---

## Task 11.5: Recents Section

<task type="auto">
  <name>Create Recents section</name>
  <files>frontend/src/components/RecentsSection.jsx</files>
  <action>
    1. Show last 15-20 conversations
    2. Sorted by last message time
    3. Truncated title (max 30 chars)
    4. Hover shows full title
    5. Click navigates to conversation
    6. Right-click context menu:
       - Star/Unstar
       - Add to Project
       - Rename
       - Delete
  </action>
</task>

---

## Task 11.6: User Profile Section

<task type="auto">
  <name>Create user profile footer</name>
  <files>frontend/src/components/UserProfile.jsx</files>
  <action>
    1. User avatar (initials or image)
    2. User name
    3. Plan/tier indicator
    4. Budget usage bar (if applicable)
    5. Click expands menu:
       - Settings
       - API Keys
       - Team (if applicable)
       - Sign out
  </action>
</task>

---

## Task 11.7: Sidebar State Refactor

<task type="auto">
  <name>Refactor sidebar state with useReducer</name>
  <files>
    frontend/src/components/Sidebar/useSidebarState.js (new)
    frontend/src/components/Sidebar/sidebarReducer.js (new)
  </files>
  <action>
    Replace 26+ useState with single useReducer:

    1. Create action types:
       - SET_CONVERSATIONS
       - SET_PROJECTS
       - SET_STARRED
       - SET_SEARCH_QUERY
       - TOGGLE_SECTION (starred, recents)
       - SELECT_ITEM
       - SET_LOADING
       - SET_ERROR

    2. Create reducer with immutable updates

    3. Create custom hook `useSidebarState()`

    4. Migrate all state to new system
  </action>
</task>

### State Shape
```typescript
interface SidebarState {
  // Data
  conversations: Conversation[];
  projects: Project[];
  starredItems: (Conversation | Project)[];

  // UI State
  selectedId: string | null;
  searchQuery: string;
  isSearchOpen: boolean;
  collapsedSections: {
    starred: boolean;
    recents: boolean;
  };

  // Loading/Error
  isLoading: boolean;
  error: string | null;
}
```

---

## Task 11.8: Navigation Routes

<task type="auto">
  <name>Update routing for new structure</name>
  <files>frontend/src/App.jsx</files>
  <action>
    Add routes:
    - `/` - Home (new council)
    - `/c/:id` - Conversation detail
    - `/projects` - Projects list
    - `/projects/:id` - Project detail
    - `/presets` - Presets/templates
    - `/settings` - Settings page
  </action>
</task>

---

## Task 11.9: Visual Polish

<task type="auto">
  <name>Match Claude's visual style</name>
  <files>
    frontend/src/components/Sidebar/Sidebar.css
    frontend/src/index.css
  </files>
  <action>
    1. Clean, minimal sidebar width (~250px)
    2. Subtle hover states
    3. Clear section dividers
    4. Consistent icon style (outline)
    5. Proper spacing (12-16px padding)
    6. Smooth transitions
    7. Collapsible sidebar for mobile
    8. Dark mode support
  </action>
</task>

### Color Palette (Light Mode)
```css
--sidebar-bg: #f9fafb;
--sidebar-hover: #f3f4f6;
--sidebar-active: #e5e7eb;
--sidebar-text: #374151;
--sidebar-text-muted: #6b7280;
--sidebar-border: #e5e7eb;
--accent-color: #4a90e2;
```

---

## Implementation Order

1. **State Refactor** (Task 11.7) - Foundation for everything
2. **Sidebar Layout** (Task 11.1) - New structure
3. **Recents Section** (Task 11.5) - Basic functionality
4. **Starred Functionality** (Task 11.3) - Quick win
5. **Search** (Task 11.4) - Major UX improvement
6. **Projects Feature** (Task 11.2) - Biggest feature
7. **User Profile** (Task 11.6) - Polish
8. **Routes** (Task 11.8) - Connect everything
9. **Visual Polish** (Task 11.9) - Final touches

---

## Wireframe: New Sidebar

```
┌──────────────────────────────────┐
│ ✦ LLM Council              [☰]  │
├──────────────────────────────────┤
│ [+ New Council]                  │
├──────────────────────────────────┤
│ 🔍 Search                  ⌘K   │
│ 💬 Councils                      │
│ 📁 Projects                      │
│ ⚙️ Presets                       │
├──────────────────────────────────┤
│ ⭐ STARRED                   ▼  │
│   ★ UPMAX Dev                    │
│   ★ Important Query              │
├──────────────────────────────────┤
│ 🕐 RECENTS                   ▼  │
│   Code review discussion...      │
│   API design council...          │
│   Budget analysis...             │
│   Marketing strategy...          │
│   Database comparison...         │
│   ...                            │
├──────────────────────────────────┤
│ ┌────┐                           │
│ │ SA │ Sezgin Arslan             │
│ └────┘ Pro Plan · $4.20 used     │
└──────────────────────────────────┘
```

---

## Wireframe: Projects View

```
┌─────────────────────────────────────────────────────────────┐
│ Projects                                    [+ New project] │
├─────────────────────────────────────────────────────────────┤
│ 🔍 Search projects...              Sort by: [Activity ▼]   │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐│
│ │ Yasemin Law     │  │ UPMAX Dev       │  │ Rayden Arslan ││
│ │                 │  │                 │  │               ││
│ │ Updated 1mo ago │  │ Updated 7mo ago │  │ Updated 10d   ││
│ └─────────────────┘  └─────────────────┘  └───────────────┘│
│ ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐│
│ │ Zazanga Project │  │ Mindset Yasemin │  │ UPMAX Agree.  ││
│ │                 │  │                 │  │               ││
│ │ Updated 1mo ago │  │ Updated 1mo ago │  │ Updated 6mo   ││
│ └─────────────────┘  └─────────────────┘  └───────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Wireframe: Project Detail

```
┌─────────────────────────────────────────────────────────────────────┐
│ ← All projects                                                      │
├───────────────────────────────────────┬─────────────────────────────┤
│                                       │ Memory              [Only you]│
│ Yasemin Law                     ☆    │ Purpose: Sezgin is navigating│
│                                       │ a complex immigration...     │
│ ┌─────────────────────────────────┐  │ Last updated: 1 day ago      │
│ │ Reply...                        │  ├─────────────────────────────┤
│ │                        [Opus ▼] │  │ Instructions            [+] │
│ └─────────────────────────────────┘  │ Add instructions to tailor   │
│                                       │ Claude's responses           │
│ 📄 N-400 filing concerns...          ├─────────────────────────────┤
│    Last message 1 day ago            │ Files                    [+] │
│                                       │ ┌─────┐ ┌─────┐            │
│ 📄 Yasemin's I-290B corrections...   │ │ PDF │ │ DOC │            │
│    Last message 15 days ago          │ └─────┘ └─────┘            │
│                                       │                             │
│ 📄 I-290B motion to reopen...        │ Add PDFs, documents, or     │
│    Last message 25 days ago          │ other text to reference in  │
│                                       │ this project.               │
│ 📄 Malpractice case outcomes...      │                             │
│    Last message 25 days ago          │                             │
└───────────────────────────────────────┴─────────────────────────────┘
```

---

## Files to Create/Modify

### New Files
```
frontend/src/components/Sidebar/
├── index.jsx
├── Sidebar.css
├── SidebarHeader.jsx
├── SidebarNav.jsx
├── SidebarSearch.jsx
├── StarredSection.jsx
├── RecentsSection.jsx
├── UserProfile.jsx
├── useSidebarState.js
└── sidebarReducer.js

frontend/src/pages/
├── Projects.jsx
├── Projects.css
├── ProjectDetail.jsx
└── ProjectDetail.css

frontend/src/components/
├── ProjectCard.jsx
├── ProjectCard.css
├── SearchModal.jsx
└── SearchModal.css

backend/
└── search.py (new)
```

### Modified Files
```
frontend/src/App.jsx          # New routes
frontend/src/api/projects.js  # Enhanced API
backend/storage.py            # Starred field
backend/main.py               # Search endpoint
```

---

## Estimated Time Breakdown

| Task | Hours |
|------|-------|
| 11.1 Sidebar Layout | 2h |
| 11.2 Projects Feature | 3h |
| 11.3 Starred | 1h |
| 11.4 Search | 2h |
| 11.5 Recents | 1h |
| 11.6 User Profile | 0.5h |
| 11.7 State Refactor | 2h |
| 11.8 Routes | 0.5h |
| 11.9 Visual Polish | 1h |
| **Total** | **~13h** |

---

## Success Criteria

- [ ] Sidebar matches Claude's UX pattern
- [ ] Projects view works like Claude's
- [ ] Project detail has Memory/Instructions/Files
- [ ] Starred section functional
- [ ] Search finds conversations + projects
- [ ] State uses useReducer (not 26+ useState)
- [ ] Mobile responsive
- [ ] Dark mode works
- [ ] All existing functionality preserved
