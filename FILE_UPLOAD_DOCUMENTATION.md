# File Upload Feature Documentation

## Overview

The LLM Council now supports file uploads for conversations. Users can upload code files, configuration files, and text documents that will be automatically included in the context when querying the council.

## Features

- **Upload files** to conversations (txt, md, py, js, ts, json, csv, html, css, yaml, etc.)
- **Automatic context inclusion**: Attached files are prepended to the query before sending to models
- **File management**: List, download, and delete files from conversations
- **Size limits**: Maximum 10MB per file
- **Security**: Validates file types and prevents path traversal attacks

## Supported File Types

```python
ALLOWED_EXTENSIONS = {
    '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx',
    '.json', '.csv', '.html', '.css', '.yaml', '.yml',
    '.xml', '.sql', '.sh', '.bash', '.c', '.cpp', '.h',
    '.java', '.go', '.rs', '.rb', '.php', '.swift', '.kt'
}
```

## API Endpoints

### 1. Upload File

**POST** `/api/conversations/{conversation_id}/upload`

Upload a file to a conversation.

**Request:**
- Content-Type: `multipart/form-data`
- Body: `file` (binary file data)

**Response:**
```json
{
  "status": "success",
  "message": "File 'example.py' uploaded successfully",
  "filename": "example.py",
  "size": 1024,
  "hash": "sha256_hash",
  "uploaded_at": "2025-12-25T10:30:00",
  "extension": ".py"
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:8001/api/conversations/{id}/upload \
  -F "file=@/path/to/file.py"
```

### 2. List Files

**GET** `/api/conversations/{conversation_id}/files`

List all files uploaded to a conversation.

**Response:**
```json
{
  "conversation_id": "uuid",
  "files": [
    {
      "filename": "example.py",
      "size": 1024,
      "uploaded_at": "2025-12-25T10:30:00",
      "extension": ".py"
    }
  ],
  "count": 1
}
```

### 3. Download File

**GET** `/api/conversations/{conversation_id}/files/{filename}`

Download a file from a conversation.

**Response:**
- Content-Type: `application/octet-stream`
- Binary file data

**Example (curl):**
```bash
curl http://localhost:8001/api/conversations/{id}/files/example.py \
  -o downloaded.py
```

### 4. Get File Content (Text)

**GET** `/api/conversations/{conversation_id}/files/{filename}/content`

Get the text content of a file as JSON.

**Response:**
```json
{
  "filename": "example.py",
  "content": "def hello():\n    print('Hello')",
  "size": 1024,
  "extension": ".py"
}
```

### 5. Delete File

**DELETE** `/api/conversations/{conversation_id}/files/{filename}`

Delete a file from a conversation.

**Response:**
```json
{
  "status": "success",
  "message": "File 'example.py' deleted successfully"
}
```

## Using Files with Messages

When sending a message, you can attach files by including their filenames in the `attached_files` array:

**POST** `/api/conversations/{conversation_id}/message`

```json
{
  "content": "Analyze this code and suggest improvements.",
  "attached_files": ["example.py", "config.json"]
}
```

The file contents will be automatically prepended to your query in this format:

```
**Attached Files:**

--- File: example.py ---
[file contents here]
--- End of example.py ---

--- File: config.json ---
[file contents here]
--- End of config.json ---

---

[Your actual question]
```

## File Storage

Files are stored in the following directory structure:

```
data/
└── uploads/
    └── {conversation_id}/
        ├── file1.py
        ├── file2.json
        └── file3.md
```

## Error Handling

### File Type Not Allowed
```json
{
  "detail": "File type .exe not allowed. Allowed types: .txt, .md, .py, ..."
}
```

### File Too Large
```json
{
  "detail": "File size 15.2MB exceeds maximum 10MB"
}
```

### File Not Found
```json
{
  "detail": "File not found"
}
```

### Conversation Not Found
```json
{
  "detail": "Conversation not found"
}
```

## Implementation Details

### Backend Modules

**`backend/files.py`**
- Core file management functions
- Validation logic
- Storage and retrieval

**`backend/main.py`**
- File upload endpoints
- Integration with conversation API

**`backend/council.py`**
- Updated `run_full_council()` to accept `attached_files` parameter
- Automatically formats and includes file contents in context

**`backend/storage.py`**
- Updated `add_user_message()` to track `attached_files` in message metadata

### Message Format

User messages with attached files are stored as:

```json
{
  "role": "user",
  "content": "Analyze this code",
  "attached_files": ["example.py", "config.json"]
}
```

## Security Features

1. **File Type Whitelist**: Only allows specific safe file extensions
2. **Size Limit**: Maximum 10MB per file
3. **Path Traversal Prevention**: Validates filenames don't contain `..`, `/`, or `\`
4. **Hash Verification**: SHA-256 hash generated for each file
5. **Isolated Storage**: Each conversation has its own directory

## Testing

Run the included test script:

```bash
./test_file_upload.sh
```

This script tests:
1. Creating a conversation
2. Uploading a file
3. Listing files
4. Getting file content
5. Sending a message with attached files
6. Downloading a file
7. Deleting a file
8. Verifying deletion

## Frontend Integration (To Be Implemented)

The frontend should:

1. **Upload UI**: Add a file upload button to the message input area
2. **File List**: Show uploaded files with delete buttons
3. **Attachment Selector**: Allow selecting files to attach to messages
4. **Progress Indicators**: Show upload progress for large files
5. **File Preview**: Optional preview of file contents before sending

Example frontend flow:
```javascript
// Upload file
const formData = new FormData();
formData.append('file', fileInput.files[0]);
const response = await fetch(`/api/conversations/${conversationId}/upload`, {
  method: 'POST',
  body: formData
});

// Send message with attached files
await fetch(`/api/conversations/${conversationId}/message`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    content: 'Analyze this code',
    attached_files: ['example.py']
  })
});
```

## Future Enhancements

1. **Multiple File Upload**: Accept multiple files in a single upload request
2. **File Previews**: Generate thumbnails or previews for certain file types
3. **Syntax Highlighting**: Return syntax-highlighted content for code files
4. **File Search**: Search within uploaded files
5. **Auto-Detection**: Automatically detect relevant files based on query content
6. **File Versioning**: Track versions of uploaded files
7. **Bulk Operations**: Upload/delete multiple files at once
8. **File Metadata**: Add tags, descriptions, or categories to files

## Performance Considerations

- Files are read from disk each time they're attached to a message
- For large files (>1MB), consider caching file contents
- Monitor disk usage as files accumulate
- Implement cleanup for old/unused conversations

## Limits and Quotas

Current limits:
- **Max file size**: 10MB
- **Max files per conversation**: Unlimited (but consider disk space)
- **Total storage**: Limited by available disk space

## Notes

- Files are NOT automatically attached to subsequent messages in a conversation
- Users must explicitly specify `attached_files` in each message
- File contents are included in the LLM context, so very large files may hit token limits
- The order of context sections: Files > Conversation History > Web Search > Memory
