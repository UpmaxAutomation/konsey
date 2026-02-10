# Attachment System Overhaul - Execution Plan

## Objective
Implement comprehensive attachment system improvements to enable vision model support, per-message attachments, image paste, better previews, proper cleanup, and context size management.

## Current State Analysis
- `backend/files.py` has `format_files_for_vision()` function but it's **NEVER CALLED**
- Images are converted to text filenames instead of base64 multimodal content
- Attachments are conversation-level, not per-message
- No Ctrl+V paste support
- No file cleanup when conversations are deleted
- No context size limit management

## Execution Context
- Backend: FastAPI on port 8001
- Frontend: React 19 + Vite on port 5173
- File storage: `data/uploads/{conversation_id}/`
- API: OpenRouter (supports multimodal content)

---

## Task 1: Fix Vision Model Support for Images

### Problem
`format_files_for_vision()` exists but is never called. Images sent to LLMs become just text like `"--- File: image.png ---"` instead of actual base64 images.

### Solution
1. Modify `backend/council.py` to detect image files and use `format_files_for_vision()`
2. Update `backend/openrouter.py` to handle multimodal content array in messages
3. Check if selected models support vision before sending images

### Files to Modify
- `backend/council.py:549-554` - Add vision detection logic
- `backend/openrouter.py:query_model()` - Support content as array
- `backend/config.py` - Add VISION_MODELS list

### Implementation
```python
# In council.py, around line 549
if conversation_id and attached_files:
    from . import files
    # Separate images from text files
    image_files = [f for f in attached_files if files.is_image_file(f)]
    text_files = [f for f in attached_files if not files.is_image_file(f)]

    # Add text files to context
    if text_files:
        file_context = files.format_files_for_context(conversation_id, text_files)
        if file_context:
            context_sections.append(file_context)

    # Return image_files for multimodal handling
    multimodal_images = files.format_files_for_vision(conversation_id, image_files) if image_files else []
```

### Verification
- Upload image to conversation
- Send query with image
- Check OpenRouter API call includes base64 image content
- Verify model responds about image content

---

## Task 2: Add Per-Message Attachments

### Problem
Currently files are attached at conversation level. Users can't reference which files belong to which message.

### Solution
1. Add `attachments` field to message schema
2. Store attachment metadata with each message
3. Update frontend to show attachments inline with messages

### Files to Modify
- `backend/database/models.py` - Add MessageAttachment model
- `backend/storage_adapter.py` - Include attachments in message serialization
- `frontend/src/components/ChatInterface.jsx` - Display attachments with messages

### Database Schema
```python
class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50))  # 'image', 'code', 'document'
    file_size = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Verification
- Send message with attachments
- Verify attachments appear with that message in UI
- Check attachments survive page reload

---

## Task 3: Add Image Paste (Ctrl+V) Support

### Problem
Users must use file dialog to upload images. Can't paste from clipboard.

### Solution
1. Add paste event listener to textarea
2. Detect image data in clipboard
3. Auto-upload and attach pasted images

### Files to Modify
- `frontend/src/components/ChatInterface.jsx` - Add paste handler

### Implementation
```javascript
const handlePaste = async (e) => {
  const items = e.clipboardData?.items;
  if (!items) return;

  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault();
      const blob = item.getAsFile();
      const filename = `pasted-image-${Date.now()}.png`;
      const file = new File([blob], filename, { type: item.type });

      // Upload and attach
      const result = await api.uploadFile(conversationId, file);
      setPendingAttachments(prev => [...prev, result]);
    }
  }
};

// In textarea: onPaste={handlePaste}
```

### Verification
- Copy image to clipboard (screenshot or from web)
- Paste into textarea with Ctrl+V
- Verify image appears in pending attachments
- Send message and verify image is included

---

## Task 4: Improve File Preview with Thumbnails

### Problem
Images show as emoji icons, no actual preview in file list.

### Solution
1. Generate thumbnails for images
2. Add syntax highlighting for code files
3. Show better file type indicators

### Files to Modify
- `frontend/src/components/FileUpload.jsx` - Add preview rendering
- `frontend/src/components/FileUpload.css` - Preview styles
- `backend/main.py` - Add thumbnail endpoint (optional)

### Implementation
```jsx
// In FileUpload.jsx, update the file-item rendering
{isImage(file.filename) ? (
  <img
    src={`/api/conversations/${conversationId}/files/${file.filename}`}
    className="file-thumbnail"
    alt={file.filename}
  />
) : isCode(file.filename) ? (
  <div className="file-code-preview">
    <code>{file.preview || '...'}</code>
  </div>
) : (
  <span className="file-icon">{getFileIcon(file.filename)}</span>
)}
```

### Verification
- Upload image - see thumbnail preview
- Upload code file - see syntax preview
- Check preview sizes are reasonable

---

## Task 5: Fix File Cleanup on Conversation Delete

### Problem
When conversations are deleted, uploaded files remain on disk forever.

### Solution
1. Add cleanup call when deleting conversation
2. Use `files.delete_all_files()` which already exists

### Files to Modify
- `backend/storage_adapter.py` - Call file cleanup in delete_conversation
- `backend/main.py` - Ensure delete endpoint triggers cleanup

### Implementation
```python
# In storage_adapter.py delete_conversation()
async def delete_conversation(self, conversation_id: str, user_id: Optional[uuid.UUID] = None) -> bool:
    # ... existing delete logic ...

    # Clean up uploaded files
    from . import files
    deleted_count = files.delete_all_files(conversation_id)
    logger.info(f"Deleted {deleted_count} files for conversation {conversation_id}")

    return True
```

### Verification
- Upload files to conversation
- Check `data/uploads/{conversation_id}/` directory exists
- Delete conversation
- Verify directory is removed

---

## Task 6: Add File Size Limits for LLM Context

### Problem
Large files can exceed LLM context limits, causing failures or truncation.

### Solution
1. Calculate total context size before sending
2. Warn user if approaching limits
3. Truncate/summarize large files automatically

### Files to Modify
- `backend/files.py` - Add context size calculation
- `backend/council.py` - Check limits before sending
- `frontend/src/components/FileUpload.jsx` - Show size warnings

### Implementation
```python
# In files.py
MAX_CONTEXT_CHARS = 100_000  # ~25k tokens

def calculate_context_size(conversation_id: str, filenames: List[str]) -> Dict:
    """Calculate total context size and warn if too large."""
    total_size = 0
    file_sizes = []

    for filename in filenames:
        try:
            if is_image_file(filename):
                # Images are ~1k tokens each
                file_sizes.append({"filename": filename, "tokens": 1000, "type": "image"})
            else:
                content = get_file_content(conversation_id, filename)
                chars = len(content)
                tokens = chars // 4  # Rough estimate
                file_sizes.append({"filename": filename, "tokens": tokens, "type": "text"})
        except:
            pass

    total_tokens = sum(f["tokens"] for f in file_sizes)

    return {
        "total_tokens": total_tokens,
        "files": file_sizes,
        "warning": total_tokens > 20000,
        "error": total_tokens > 100000
    }
```

### Verification
- Upload large file (>100KB)
- See warning indicator in UI
- Verify truncation happens gracefully

---

## Execution Order

1. **Task 5: File Cleanup** - Quick fix, prevents disk bloat (15 min)
2. **Task 1: Vision Support** - Core functionality, enables images (1 hour)
3. **Task 3: Image Paste** - UX improvement, easy win (30 min)
4. **Task 4: File Preview** - Polish, better UX (45 min)
5. **Task 2: Per-Message Attachments** - Schema change, more complex (1.5 hours)
6. **Task 6: Context Limits** - Safety feature, can be basic (30 min)

**Total Estimated: ~4.5 hours**

---

## Success Criteria

- [x] Images sent to vision-capable models render properly and models can describe them
- [x] Each message shows its associated attachments
- [x] Ctrl+V paste works for images
- [x] Image thumbnails appear in file list
- [x] Deleting conversation removes files from disk
- [x] Large files are auto-truncated with context limits

## Implementation Complete (2026-01-25)

All 6 attachment system improvements have been implemented:

1. **File Cleanup**: Conversations now clean up their files on delete
2. **Vision Support**: Images sent to vision models as base64 multimodal content
3. **Image Paste**: Ctrl+V uploads and attaches images to messages
4. **File Thumbnails**: Image previews in file upload dialog
5. **Context Limits**: Auto-truncation for large files (50k tokens/file, 100k total)
6. **Per-Message Attachments**: Files displayed inline with messages

---

## Output
- Updated `backend/council.py` with vision support
- Updated `backend/openrouter.py` for multimodal content
- Updated `backend/storage_adapter.py` with file cleanup
- Updated `frontend/src/components/ChatInterface.jsx` with paste support
- Updated `frontend/src/components/FileUpload.jsx` with thumbnails
- New `backend/database/models.py` MessageAttachment model (if needed)
