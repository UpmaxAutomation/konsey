# Testing Folder & Tag System

Complete test guide for the conversation folders and tags implementation.

## Prerequisites

1. Backend running: `cd /Users/sezars/llm-council && python -m backend.main`
2. Frontend running: `cd /Users/sezars/llm-council/frontend && npm run dev`
3. Open browser to `http://localhost:5173`

## Test Checklist

### ✅ Initial Setup Tests

**Test 1: Default Folders Load**
- [ ] Sidebar loads without errors
- [ ] 4 default folders visible: Clients, Internal, Archive, Favorites
- [ ] Each folder shows count (0)
- [ ] Folders have different colors

**Test 2: All Conversations Section**
- [ ] "All Conversations" section visible
- [ ] Shows total count of conversations
- [ ] Can be collapsed/expanded

### ✅ Folder Management Tests

**Test 3: Create New Folder**
- [ ] Click "New Folder" button
- [ ] Input field appears
- [ ] Type "Test Project"
- [ ] Press Enter or click + button
- [ ] New folder appears in sidebar
- [ ] Input field closes

**Test 4: Delete Folder**
- [ ] Hover over "Test Project" folder
- [ ] Delete button (trash icon) appears
- [ ] Click delete button
- [ ] Confirmation dialog appears
- [ ] Confirm deletion
- [ ] Folder disappears from sidebar
- [ ] Conversations (if any) move to Uncategorized

**Test 5: Collapse/Expand Folders**
- [ ] Click on "Clients" folder header
- [ ] Folder collapses (conversations hidden)
- [ ] Click again
- [ ] Folder expands (conversations visible)
- [ ] Chevron icon rotates correctly

### ✅ Drag & Drop Tests

**Test 6: Move Conversation to Folder**
1. Create a new conversation
2. [ ] Drag conversation item
3. [ ] Drop on "Clients" folder header
4. [ ] Conversation appears under "Clients" folder
5. [ ] Conversation disappears from "Uncategorized"
6. [ ] Folder count updates

**Test 7: Move Conversation Between Folders**
1. [ ] Drag conversation from "Clients"
2. [ ] Drop on "Internal" folder
3. [ ] Conversation moves to "Internal"
4. [ ] Both folder counts update

**Test 8: Move to Uncategorized**
1. [ ] Drag conversation from any folder
2. [ ] Drop on "Uncategorized" section
3. [ ] Conversation appears in "Uncategorized"
4. [ ] Folder count decrements

### ✅ Tag Management Tests

**Test 9: Add Tag to Conversation**
1. [ ] Hover over conversation
2. [ ] Tag icon button appears
3. [ ] Click tag icon
4. [ ] Input field appears
5. [ ] Type "urgent"
6. [ ] Press Enter
7. [ ] Tag chip appears on conversation
8. [ ] Input field closes

**Test 10: Add Multiple Tags**
1. [ ] Click tag icon again
2. [ ] Type "react"
3. [ ] Press Enter
4. [ ] Second tag appears
5. [ ] Repeat for "frontend"
6. [ ] Three tag chips visible

**Test 11: Tag Autocomplete**
1. [ ] Add "urgent" tag to another conversation
2. [ ] Click tag icon on third conversation
3. [ ] Type "ur"
4. [ ] Autocomplete suggests "urgent"
5. [ ] Select from suggestions
6. [ ] Tag added correctly

**Test 12: Remove Tag**
1. [ ] Click on "urgent" tag chip
2. [ ] Tag disappears
3. [ ] Other tags remain
4. [ ] Conversation still visible

### ✅ Tag Filter Tests

**Test 13: Tag Filter Appears**
- [ ] When any conversation has tags
- [ ] "Filter by tags:" section appears at top
- [ ] All unique tags shown as buttons
- [ ] Tags sorted alphabetically

**Test 14: Filter by Single Tag**
1. [ ] Click "react" tag in filter section
2. [ ] Only conversations with "react" tag visible
3. [ ] Other conversations hidden
4. [ ] Filter button highlighted (blue background)

**Test 15: Filter by Multiple Tags (OR)**
1. [ ] Click "urgent" filter (while "react" selected)
2. [ ] Conversations with either "react" OR "urgent" shown
3. [ ] Both filter buttons highlighted
4. [ ] Folder counts update to match filtered results

**Test 16: Clear Filters**
1. [ ] Click active filter buttons to deselect
2. [ ] All conversations become visible again
3. [ ] Filter buttons return to normal state
4. [ ] Folder counts return to full totals

### ✅ Integration Tests

**Test 17: Folders + Tags Together**
1. Create conversation A with tags ["urgent", "react"]
2. Move to "Clients" folder
3. [ ] Conversation appears in Clients with tags
4. [ ] Filter by "urgent" - conversation visible in Clients
5. [ ] Clear filter - conversation still in Clients

**Test 18: Persistence**
1. Create folder "QA Testing"
2. Move conversation to "QA Testing"
3. Add tags ["test", "qa"]
4. [ ] Refresh page (F5)
5. [ ] Folder still exists
6. [ ] Conversation still in folder
7. [ ] Tags still attached
8. [ ] Filter still works

**Test 19: Delete Folder with Conversations**
1. Move 3 conversations to "Clients"
2. Delete "Clients" folder
3. [ ] Confirmation dialog appears
4. [ ] Confirm deletion
5. [ ] All 3 conversations move to Uncategorized
6. [ ] Tags remain on conversations
7. [ ] No errors in console

**Test 20: Empty States**
- [ ] Delete all conversations → "No conversations yet" message
- [ ] Filter with no matches → "No conversations with selected tags" message
- [ ] Collapsed folder shows correct count even when empty

## API Tests (Optional - Using curl)

### Test API Endpoints

**List Folders:**
```bash
curl http://localhost:8001/api/folders
```
Expected: `{"folders": [...]}`

**Create Folder:**
```bash
curl -X POST http://localhost:8001/api/folders \
  -H "Content-Type: application/json" \
  -d '{"name": "API Test", "color": "#ff0000"}'
```
Expected: `{"id": "api_test", "name": "API Test", ...}`

**List Tags:**
```bash
curl http://localhost:8001/api/tags
```
Expected: `{"tags": ["urgent", "react", ...]}`

**Update Conversation Tags:**
```bash
# Get conversation ID from UI first
curl -X PUT http://localhost:8001/api/conversations/{CONVERSATION_ID}/tags \
  -H "Content-Type: application/json" \
  -d '{"tags": ["api", "test"]}'
```
Expected: `{"status": "success", "tags": ["api", "test"]}`

**Move Conversation to Folder:**
```bash
curl -X PUT http://localhost:8001/api/conversations/{CONVERSATION_ID}/folder \
  -H "Content-Type: application/json" \
  -d '{"folder_id": "clients"}'
```
Expected: `{"status": "success", "folder_id": "clients"}`

## Performance Tests

**Test 21: Many Folders**
1. Create 20 folders
2. [ ] UI remains responsive
3. [ ] Scrolling smooth
4. [ ] No lag when expanding/collapsing

**Test 22: Many Tags**
1. Add 50 unique tags across conversations
2. [ ] Tag filter section shows all tags
3. [ ] Autocomplete works quickly
4. [ ] Filtering instant

**Test 23: Large Conversation Count**
1. Create 100 conversations
2. Distribute across 5 folders
3. [ ] Sidebar scrolls smoothly
4. [ ] Drag & drop still works
5. [ ] No memory leaks (check DevTools)

## Error Handling Tests

**Test 24: Network Failure**
1. Stop backend server
2. Try to create folder
3. [ ] Error logged to console (check DevTools)
4. [ ] UI doesn't freeze
5. [ ] Restart backend
6. [ ] Retry operation succeeds

**Test 25: Invalid Data**
1. Try to create folder with empty name
2. [ ] Nothing happens (validation works)
3. Try to add empty tag
4. [ ] Tag not added

**Test 26: Rapid Operations**
1. Quickly create 5 folders
2. [ ] All folders appear correctly
3. Rapidly add/remove same tag
4. [ ] Final state is consistent
5. Drag conversation back and forth quickly
6. [ ] No duplicate conversations
7. [ ] Counts remain accurate

## UI/UX Tests

**Test 27: Visual Feedback**
- [ ] Hover states work on all buttons
- [ ] Delete buttons appear on hover
- [ ] Active states visible (selected filters, active conversation)
- [ ] Drag operation shows visual feedback
- [ ] Colors are distinct and readable

**Test 28: Responsive Behavior**
- [ ] Sidebar maintains 260px width
- [ ] Long folder names truncate with ellipsis
- [ ] Tag chips wrap to next line if needed
- [ ] Scrollbar appears when content overflows

**Test 29: Accessibility**
- [ ] All buttons have title attributes (tooltips)
- [ ] Keyboard navigation works (Tab key)
- [ ] Enter key works in input fields
- [ ] Escape key could close inputs (nice to have)

## Known Limitations

1. **Folder Icons**: Fixed set of icons, not customizable via UI
2. **Folder Colors**: Fixed colors, not customizable via UI
3. **Nested Folders**: Not supported (flat structure only)
4. **Tag Colors**: All tags use same color (blue)
5. **Bulk Operations**: Can't move multiple conversations at once
6. **Smart Folders**: No dynamic filtering rules
7. **Folder Ordering**: Fixed order (can't reorder folders)

## Success Criteria

All tests passing means:
- ✅ Folders can be created, deleted, and used for organization
- ✅ Drag & drop works reliably
- ✅ Tags can be added, removed, and filtered
- ✅ Data persists across page refreshes
- ✅ UI is responsive and provides good feedback
- ✅ No errors in console during normal operation
- ✅ Performance is acceptable with realistic data volumes

## Troubleshooting

**Issue: Folders don't appear**
- Check browser console for errors
- Verify backend is running on port 8001
- Check `data/conversations/folders.json` exists

**Issue: Tags don't persist**
- Check conversation JSON files in `data/conversations/`
- Verify "tags" array is present
- Check API responses in Network tab

**Issue: Drag & drop not working**
- Ensure conversation items have `draggable` attribute
- Check folder sections have `onDrop` handlers
- Look for JavaScript errors in console

**Issue: Filters not working**
- Verify tag filter logic in Sidebar.jsx
- Check selectedTags state in React DevTools
- Ensure filteredConversations computed correctly
