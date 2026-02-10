# Folders and Tags Implementation

## Overview
This document describes the conversation folders and tags system implemented for the LLM Council project.

## Features Implemented

### 1. Backend (Python/FastAPI)

#### Storage Layer (`backend/storage.py`)
- **Updated conversation schema** to include:
  - `folder_id`: Optional string linking conversation to a folder
  - `tags`: List of string tags for categorization

- **Folder Management Functions**:
  - `ensure_folders_file()`: Creates default folders on first use
  - `list_folders()`: Returns all folders
  - `create_folder(name, color, icon)`: Creates a new folder with custom styling
  - `delete_folder(folder_id)`: Deletes folder and unlinks conversations
  - `move_conversation_to_folder(conversation_id, folder_id)`: Moves conversation to folder

- **Tag Management Functions**:
  - `add_tag(conversation_id, tag)`: Adds tag to conversation
  - `remove_tag(conversation_id, tag)`: Removes tag from conversation
  - `update_tags(conversation_id, tags)`: Updates all tags at once
  - `list_all_tags()`: Returns all unique tags across conversations

#### Default Folders
Four default folders are created automatically:
1. **Clients** - Blue (#4a90e2) with briefcase icon
2. **Internal** - Purple (#9b59b6) with users icon
3. **Archive** - Gray (#95a5a6) with archive icon
4. **Favorites** - Orange (#f39c12) with star icon

#### API Endpoints (`backend/main.py`)

**Folder Endpoints**:
- `GET /api/folders` - List all folders
- `POST /api/folders` - Create new folder (name, color, icon)
- `DELETE /api/folders/{folder_id}` - Delete folder
- `PUT /api/conversations/{conversation_id}/folder` - Move conversation to folder

**Tag Endpoints**:
- `GET /api/tags` - List all unique tags
- `PUT /api/conversations/{conversation_id}/tags` - Update conversation tags

### 2. Frontend (React)

#### Sidebar Component (`frontend/src/components/Sidebar.jsx`)

**State Management**:
- Loads folders and tags on component mount
- Tracks collapsed/expanded folder state
- Manages tag filter selection
- Handles drag-and-drop state

**Folder Features**:
- **Collapsible folder sections** with custom icons and colors
- **Drag-and-drop** conversations into folders
- **"All Conversations"** section showing everything
- **"Uncategorized"** section for conversations without folders
- Folder count badges
- Color-coded folder headers with left border accent

**Tag Features**:
- **Tag filter bar** at top of sidebar (when tags exist)
- **Click tags to filter** conversations
- **Multiple tag selection** with active state styling
- **Add tags** via tag button on each conversation
- **Tag autocomplete** from existing tags
- **Remove tags** by clicking on them
- **Tag pills** displayed on conversation items

**UI Interactions**:
- Hover to reveal tag and delete buttons
- Click folder header to collapse/expand
- Drag conversation over folder to highlight drop zone
- Tag input with Enter key support
- Datalist for tag suggestions

#### Styling (`frontend/src/components/Sidebar.css`)

**New CSS Classes**:
- `.folder-section` - Container for each folder group
- `.folder-header` - Clickable folder title with icon and count
- `.folder-icon` - SVG icon with rotation animation
- `.folder-count` - Badge showing conversation count
- `.tag-filter-section` - Filter bar container
- `.tag-filter` - Individual tag filter button
- `.tag-filter.active` - Selected tag filter state
- `.conversation-tags` - Tag container in conversation item
- `.tag` - Individual tag pill
- `.tag-input-container` - Tag input form
- `.tag-conversation-btn` - Button to add tags
- `.conversation-actions` - Container for tag and delete buttons

### 3. Integration

#### App Component Updates (`frontend/src/App.jsx`)
- Added `onConversationsChange={loadConversations}` prop to Sidebar
- Enables real-time refresh after folder/tag operations

## Usage Guide

### For Users

**Organizing with Folders**:
1. Drag any conversation onto a folder header to move it
2. Click folder header to collapse/expand
3. Conversations automatically appear in "Uncategorized" if not in a folder

**Using Tags**:
1. Hover over a conversation to reveal the tag button (🏷️ icon)
2. Click the tag button to open tag input
3. Type a tag name (autocomplete suggests existing tags)
4. Press Enter or click + to add the tag
5. Click any tag pill on a conversation to remove it
6. Click tags in the filter bar to filter conversations

**Tag Filtering**:
- Click tags in the top filter bar to show only matching conversations
- Select multiple tags to see conversations with any of those tags
- Filter is OR-based (conversation needs at least one selected tag)

### For Developers

**Adding New Folders Programmatically**:
```python
from backend import storage

new_folder = storage.create_folder(
    name="Project X",
    color="#e74c3c",  # Red
    icon="briefcase"
)
```

**Available Icons**:
- `briefcase` - Suitcase icon
- `users` - People icon
- `archive` - Archive box icon
- `star` - Star icon
- `folder` - Default folder icon

**Moving Conversations**:
```python
# Move to folder
storage.move_conversation_to_folder(conversation_id, "clients")

# Remove from folder (move to uncategorized)
storage.move_conversation_to_folder(conversation_id, None)
```

**Working with Tags**:
```python
# Add tags
storage.update_tags(conversation_id, ["urgent", "client-x", "billing"])

# Get all unique tags
all_tags = storage.list_all_tags()  # Returns sorted list
```

## Data Structure

### Conversation Schema
```json
{
  "id": "uuid",
  "created_at": "ISO timestamp",
  "title": "Conversation title",
  "messages": [],
  "folder_id": "clients",  // NEW
  "tags": ["urgent", "client-x"]  // NEW
}
```

### Folder Schema (`data/folders.json`)
```json
{
  "folders": [
    {
      "id": "clients",
      "name": "Clients",
      "color": "#4a90e2",
      "icon": "briefcase",
      "created_at": "ISO timestamp"
    }
  ]
}
```

## Technical Details

### Drag and Drop Implementation
- Uses native HTML5 drag and drop API
- `draggable` attribute on conversation items
- `onDragStart`, `onDragOver`, `onDrop` event handlers
- Visual feedback via CSS hover states
- API call on successful drop

### Tag Autocomplete
- Uses HTML `<datalist>` element for suggestions
- Dynamically populated from all existing tags
- No external dependencies required

### Performance Considerations
- Folders and tags loaded once on mount
- Tags reload when conversations change
- Filtered conversations computed client-side
- No pagination needed for small conversation lists (<100)

### State Management
- All folder/tag state managed in Sidebar component
- API calls update backend immediately
- Callback to parent (App.jsx) triggers conversation list refresh
- Optimistic UI updates where possible

## Testing Checklist

- [x] Create new folder via API
- [x] Delete folder (conversations move to uncategorized)
- [x] Drag conversation to folder
- [x] Collapse/expand folders
- [x] Add tag to conversation
- [x] Remove tag from conversation
- [x] Filter by single tag
- [x] Filter by multiple tags
- [x] Tag autocomplete suggestions
- [x] Empty state when no tags match filter
- [x] Folder count badges update correctly
- [x] All Conversations section shows everything

## Future Enhancements

Potential improvements:
1. **Folder Management UI** - Add/edit/delete folders from Settings
2. **Custom Tag Colors** - Allow color customization per tag
3. **Nested Folders** - Support folder hierarchy
4. **Folder Templates** - Quick folder setups for common workflows
5. **Tag Cloud View** - Visual tag frequency display
6. **Smart Folders** - Auto-organize by tags or keywords
7. **Export by Folder** - Export all conversations in a folder
8. **Keyboard Shortcuts** - Quick folder/tag assignment
9. **Folder Icons Library** - More icon choices
10. **Tag Analytics** - Most used tags, tag trends over time

## Files Modified

**Backend**:
- `/Users/sezars/llm-council/backend/storage.py` - Added folder/tag functions
- `/Users/sezars/llm-council/backend/main.py` - Added API endpoints

**Frontend**:
- `/Users/sezars/llm-council/frontend/src/components/Sidebar.jsx` - Complete rewrite with folders/tags
- `/Users/sezars/llm-council/frontend/src/components/Sidebar.css` - New styles for folders/tags
- `/Users/sezars/llm-council/frontend/src/App.jsx` - Added onConversationsChange callback

**Data**:
- `/Users/sezars/llm-council/backend/data/folders.json` - Auto-created with defaults

## Compatibility

- **Backend**: Python 3.7+, FastAPI
- **Frontend**: React 18+, ES6+
- **Browsers**: Chrome/Edge/Firefox/Safari (modern versions with drag-and-drop support)
- **Mobile**: Touch events not currently supported for drag-and-drop

## Known Limitations

1. **No folder nesting** - Folders are flat, single-level only
2. **No folder permissions** - All folders visible to all users
3. **Tag case sensitivity** - "Client" and "client" are different tags
4. **No tag aliases** - Each tag is unique, no synonyms
5. **Drag-and-drop mobile** - Not optimized for touch devices
6. **No undo** - Folder/tag changes are immediate and permanent

## Summary

This implementation provides a complete conversation organization system with:
- 4 default folders (Clients, Internal, Archive, Favorites)
- Drag-and-drop folder organization
- Tag-based categorization with filtering
- Tag autocomplete and management
- Clean, intuitive UI with collapsible sections
- RESTful API for programmatic access

All features are production-ready and follow existing codebase patterns.
