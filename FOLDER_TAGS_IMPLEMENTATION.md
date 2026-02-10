# Conversation Folders & Tags Implementation

Complete implementation of folder organization and tagging system for LLM Council conversations.

## Features Implemented

### 1. Folder Management
- **Create Folders**: Click "New Folder" button to create custom folders
- **Delete Folders**: Hover over folder header to reveal delete button
- **Drag & Drop**: Drag conversations between folders
- **Collapsible Sections**: Click folder header to expand/collapse
- **Color-coded**: Each folder has a unique color and icon
- **Default Folders**: Clients, Internal, Archive, Favorites (pre-configured)

### 2. Tag System
- **Add Tags**: Click tag icon on conversation, type tag name, press Enter
- **Remove Tags**: Click on tag chip to remove from conversation
- **Tag Autocomplete**: Suggestions from existing tags while typing
- **Filter by Tags**: Click tags in filter section to show only tagged conversations
- **Multi-tag Filter**: Select multiple tags to filter (OR logic)
- **Tag Chips**: Visual tag indicators on each conversation

### 3. Conversation Organization
- **All Conversations**: View all conversations in one section
- **Folder Groups**: Conversations organized by folder
- **Uncategorized**: Conversations not in any folder
- **Drag & Drop**: Move conversations to folders or uncategorized
- **Smart Grouping**: Automatic grouping by folder with counts

## Backend Implementation

### Storage Functions (`backend/storage.py`)
```python
# Folder Management
list_folders()                              # Get all folders
create_folder(name, color, icon)            # Create new folder
delete_folder(folder_id)                    # Delete folder (moves conversations to uncategorized)
move_conversation_to_folder(conv_id, folder_id)  # Move conversation

# Tag Management
add_tag(conversation_id, tag)               # Add single tag
remove_tag(conversation_id, tag)            # Remove single tag
update_tags(conversation_id, tags)          # Replace all tags
list_all_tags()                             # Get all unique tags
```

### API Endpoints (`backend/main.py`)
```
GET    /api/folders                         # List all folders
POST   /api/folders                         # Create folder
DELETE /api/folders/{folder_id}             # Delete folder

PUT    /api/conversations/{id}/folder       # Move to folder
GET    /api/tags                            # List all tags
PUT    /api/conversations/{id}/tags         # Update tags
```

### Data Structure

**Folder Object:**
```json
{
  "id": "clients",
  "name": "Clients",
  "color": "#4a90e2",
  "icon": "briefcase",
  "created_at": "2025-12-25T10:00:00.000000"
}
```

**Conversation with Folder/Tags:**
```json
{
  "id": "uuid-here",
  "title": "Conversation Title",
  "folder_id": "clients",
  "tags": ["urgent", "web-dev", "react"],
  "messages": [],
  "created_at": "2025-12-25T10:00:00.000000"
}
```

## Frontend Implementation

### API Client (`frontend/src/api.js`)
```javascript
// Folder API
api.listFolders()
api.createFolder({ name, color, icon })
api.deleteFolder(folderId)
api.moveConversationToFolder(conversationId, folderId)

// Tag API
api.listAllTags()
api.updateConversationTags(conversationId, tags)
```

### UI Components (`frontend/src/components/Sidebar.jsx`)

**Folder Features:**
- New Folder button at top of conversation list
- Inline folder creation with input field
- Delete button on folder headers (visible on hover)
- Drag & drop zones on each folder section
- Collapsible folder headers with chevron icon

**Tag Features:**
- Tag filter section at top (when tags exist)
- Tag icon button on each conversation (visible on hover)
- Inline tag input with autocomplete
- Tag chips on conversations (click to remove)
- Multi-select tag filter buttons

### Styling (`frontend/src/components/Sidebar.css`)

**New Classes:**
- `.add-folder-btn` - New folder button
- `.new-folder-container` - Folder creation input container
- `.new-folder-input` - Folder name input field
- `.new-folder-btn` / `.cancel-folder-btn` - Confirm/cancel buttons
- `.delete-folder-btn` - Folder delete button
- `.tag-filter-section` - Tag filter container
- `.tag-filter` - Individual tag filter button
- `.conversation-tags` - Tag chips container
- `.tag` - Individual tag chip
- `.tag-input-container` - Tag input field container

## User Workflow

### Creating a Folder
1. Click "New Folder" button
2. Type folder name
3. Press Enter or click + button
4. Folder appears in sidebar with default color/icon

### Organizing Conversations
1. Drag conversation item
2. Drop on folder header to move to folder
3. Drop on "Uncategorized" to remove from folders
4. Visual feedback during drag operation

### Tagging Conversations
1. Hover over conversation
2. Click tag icon button
3. Type tag name (autocomplete suggests existing tags)
4. Press Enter to add
5. Click tag chip to remove

### Filtering by Tags
1. Tags appear in filter section when any conversation is tagged
2. Click tag to filter conversations
3. Click again to remove filter
4. Multiple tags can be selected (OR logic)
5. Clear all filters by deselecting all tags

## Default Folders

Four pre-configured folders created on first run:

1. **Clients** (Blue, Briefcase icon) - Client work conversations
2. **Internal** (Purple, Users icon) - Internal team discussions
3. **Archive** (Gray, Archive icon) - Archived conversations
4. **Favorites** (Orange, Star icon) - Favorited conversations

Users can create additional custom folders as needed.

## Technical Notes

### Persistence
- Folders stored in `data/conversations/folders.json`
- Conversation folder_id and tags stored in each conversation JSON file
- Changes saved immediately to disk

### State Management
- Folders loaded on component mount
- Tags reloaded when conversations change
- Drag & drop state tracked with React hooks
- Optimistic UI updates with error handling

### Drag & Drop
- Native HTML5 drag and drop API
- Conversations are draggable
- Folder sections are drop zones
- Visual feedback with `onDragOver` effect

### Tag Autocomplete
- Uses HTML5 `<datalist>` element
- Populated with all existing tags
- Browser-native autocomplete UI
- No external dependencies

## Error Handling

All API calls wrapped with try/catch:
- Failed folder creation: Silent failure, logs error
- Failed tag update: Silent failure, logs error
- Failed drag & drop: Resets drag state, logs error
- Network errors: Graceful degradation, no UI freeze

## Performance Considerations

- Folders/tags loaded once on mount
- Tags reloaded only when conversations change
- Drag state managed with minimal re-renders
- Collapsed folders don't render conversations (performance optimization)
- Filter logic runs client-side for instant feedback

## Future Enhancements

Possible improvements (not currently implemented):
- Custom folder colors/icons via UI
- Nested folders (subfolders)
- Folder-level settings (auto-tag, default chairman, etc.)
- Tag categories/groups
- Smart folders (dynamic filters)
- Bulk operations (move multiple conversations)
- Keyboard shortcuts for folder/tag management
- Export/import folder configurations
