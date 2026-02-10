# Folders and Tags - Quick Start Guide

## User Guide

### Working with Folders

**Default Folders Available**:
- 🧳 **Clients** (Blue) - Client-related conversations
- 👥 **Internal** (Purple) - Internal team discussions
- 📦 **Archive** (Gray) - Archived conversations
- ⭐ **Favorites** (Orange) - Starred/important conversations

**Moving Conversations to Folders**:
1. Click and hold on any conversation in the sidebar
2. Drag it over a folder header (it will highlight)
3. Release to drop the conversation into that folder
4. The conversation immediately moves to that folder

**Removing from Folders**:
- Drag the conversation to the "Uncategorized" section
- OR drag it to a different folder

**Collapsing/Expanding Folders**:
- Click any folder header to collapse/expand that section
- Collapsed folders show a rotated icon
- Folder state persists during your session

### Working with Tags

**Adding Tags**:
1. Hover over any conversation
2. Click the tag icon (🏷️) that appears
3. Type a tag name
4. Press Enter or click the + button
5. Tag appears as a colored pill on the conversation

**Removing Tags**:
- Click any tag pill directly on a conversation
- It will be immediately removed

**Tag Autocomplete**:
- As you type, existing tags will be suggested
- This helps maintain consistency
- Press Tab to accept a suggestion

**Filtering by Tags**:
1. Tags appear in a filter bar above the conversation list
2. Click any tag to filter conversations
3. Click multiple tags to see conversations with ANY of those tags
4. Click again to remove the filter

### Keyboard Shortcuts

- **Search**: `Cmd/Ctrl + K` - Open conversation search
- **Enter**: Add tag when tag input is focused

## API Reference

### Folder Endpoints

```bash
# List all folders
GET /api/folders

# Create new folder
POST /api/folders
{
  "name": "Project X",
  "color": "#e74c3c",
  "icon": "briefcase"
}

# Delete folder
DELETE /api/folders/{folder_id}

# Move conversation to folder
PUT /api/conversations/{conversation_id}/folder
{
  "folder_id": "clients"  // or null to remove from folder
}
```

### Tag Endpoints

```bash
# List all unique tags
GET /api/tags

# Update conversation tags
PUT /api/conversations/{conversation_id}/tags
{
  "tags": ["urgent", "client-x", "billing"]
}
```

## Python Examples

### Creating Custom Folders

```python
from backend import storage

# Create a new project folder
folder = storage.create_folder(
    name="Website Redesign",
    color="#3498db",  # Custom blue
    icon="briefcase"
)

# Create a priority folder
priority_folder = storage.create_folder(
    name="High Priority",
    color="#e74c3c",  # Red
    icon="star"
)
```

### Managing Tags Programmatically

```python
from backend import storage

# Add tags to a conversation
storage.update_tags("conversation-uuid", ["urgent", "needs-review", "client-acme"])

# Get all unique tags across all conversations
all_tags = storage.list_all_tags()
print(f"Available tags: {', '.join(all_tags)}")

# Find conversations with specific tags (you'll need to filter yourself)
conversations = storage.list_conversations()
urgent_convs = [c for c in conversations if "urgent" in c.get("tags", [])]
```

### Bulk Organization

```python
from backend import storage

# Move all conversations with "client-x" tag to Clients folder
conversations = storage.list_conversations()

for conv in conversations:
    if "client-x" in conv.get("tags", []):
        storage.move_conversation_to_folder(conv["id"], "clients")

print("Bulk organization complete!")
```

## Common Workflows

### Workflow 1: Client Project Organization
1. Create conversation with client
2. Add tag: "client-acme"
3. Drag to "Clients" folder
4. Add additional tags: "website", "redesign"
5. Filter by "client-acme" to see all related conversations

### Workflow 2: Task Prioritization
1. Tag conversations with priority levels: "urgent", "medium", "low"
2. Move urgent ones to "Favorites" folder
3. Filter by "urgent" tag to see all high-priority items
4. Archive completed conversations to "Archive" folder

### Workflow 3: Topic Categorization
1. Use tags for topics: "billing", "support", "sales", "technical"
2. Keep folders for status: "Active", "Archived", "Needs Review"
3. Filter by topic tag to see all conversations about that topic
4. Organize by folder based on conversation status

## Tips and Best Practices

### Folder Strategy
- **Use folders for STATUS** (Active, Archived, In Review)
- **Use tags for CATEGORIES** (client name, topic, priority)
- Keep folder count low (4-8 folders max)
- Regularly archive old conversations

### Tag Strategy
- **Be consistent** - Use autocomplete to reuse existing tags
- **Use lowercase** - Easier to type and more consistent
- **Use dashes for multi-word tags** - "client-acme" not "Client ACME"
- **Create a tag taxonomy** - Decide on standard tags upfront
- **Don't over-tag** - 2-4 tags per conversation is ideal

### Tag Naming Conventions
```
Clients:      client-acme, client-globex
Projects:     project-website, project-app
Priority:     urgent, high-priority, low-priority
Topics:       billing, support, sales, technical
Status:       needs-review, waiting-response, completed
```

## Troubleshooting

**Problem: Can't drag conversations**
- Make sure you're clicking and holding on the conversation item
- Try refreshing the page
- Check browser console for errors

**Problem: Tags not showing up**
- Refresh the conversation list
- Check that tags were saved (look in conversation details)
- Ensure conversation list has reloaded

**Problem: Folder colors not showing**
- Check that folder has a valid hex color code
- Try creating a new folder with a different color
- Refresh the page

**Problem: Tag filter not working**
- Click the tag again to deselect it
- Refresh the page to reset filters
- Check that conversations actually have those tags

## Advanced Usage

### Custom Folder Icons
Available icon options:
- `briefcase` - Suitcase/work icon
- `users` - People/team icon
- `archive` - Archive box icon
- `star` - Star/favorite icon
- `folder` - Default folder icon

### Programmatic Access
All folder and tag operations are available via the REST API, allowing you to:
- Build custom organization scripts
- Auto-tag conversations based on content
- Create smart folders that auto-populate
- Generate reports by folder/tag
- Bulk import/export with organization preserved

### Integration Ideas
- **Auto-tagging**: Parse conversation content to suggest tags
- **Smart folders**: Auto-move conversations based on rules
- **Tag analytics**: Track most-used tags, tag trends
- **Folder templates**: Quick setups for common workflows
- **Export by folder**: Download all conversations in a folder as markdown

## Need Help?

See `FOLDERS_AND_TAGS_IMPLEMENTATION.md` for complete technical documentation.
