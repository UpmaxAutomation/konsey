"""File management for LLM Council conversations."""

import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Base upload directory
UPLOAD_DIR = "data/uploads"

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {
    # Code files
    '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx',
    '.json', '.csv', '.html', '.css', '.yaml', '.yml',
    '.xml', '.sql', '.sh', '.bash', '.c', '.cpp', '.h',
    '.java', '.go', '.rs', '.rb', '.php', '.swift', '.kt',
    # Images (for vision models)
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg',
    # Documents
    '.pdf', '.doc', '.docx',
    # Data
    '.xls', '.xlsx'
}

# Image extensions for vision model support
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

# Maximum file size (25MB for images/PDFs)
MAX_FILE_SIZE = 25 * 1024 * 1024


def ensure_upload_dir(conversation_id: str) -> str:
    """
    Ensure the upload directory exists for a conversation.

    Args:
        conversation_id: Unique conversation identifier

    Returns:
        Path to the conversation's upload directory
    """
    upload_path = os.path.join(UPLOAD_DIR, conversation_id)
    Path(upload_path).mkdir(parents=True, exist_ok=True)
    return upload_path


def validate_file(filename: str, file_size: int) -> tuple[bool, Optional[str]]:
    """
    Validate file for upload.

    Args:
        filename: Name of the file
        file_size: Size of the file in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file extension
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type {file_ext} not allowed. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

    # Check file size
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        actual_mb = file_size / (1024 * 1024)
        return False, f"File size {actual_mb:.2f}MB exceeds maximum {max_mb}MB"

    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False, "Invalid filename - cannot contain path separators"

    return True, None


def save_file(conversation_id: str, filename: str, content: bytes) -> Dict:
    """
    Save a file to the conversation's upload directory.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the file
        content: File content as bytes

    Returns:
        Dict with file metadata

    Raises:
        ValueError: If file validation fails
    """
    # Validate file
    is_valid, error = validate_file(filename, len(content))
    if not is_valid:
        raise ValueError(error)

    # Ensure upload directory exists
    upload_path = ensure_upload_dir(conversation_id)

    # Generate file path
    file_path = os.path.join(upload_path, filename)

    # Check if file already exists and generate unique name if needed
    if os.path.exists(file_path):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(file_path):
            filename = f"{base}_{counter}{ext}"
            file_path = os.path.join(upload_path, filename)
            counter += 1

    # Save file
    with open(file_path, 'wb') as f:
        f.write(content)

    # Generate file hash for integrity checking
    file_hash = hashlib.sha256(content).hexdigest()

    # Return metadata
    return {
        "filename": filename,
        "size": len(content),
        "hash": file_hash,
        "uploaded_at": datetime.utcnow().isoformat(),
        "extension": os.path.splitext(filename)[1].lower()
    }


def get_file_content(conversation_id: str, filename: str) -> str:
    """
    Read file content as text.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the file

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        UnicodeDecodeError: If file is not valid text
    """
    file_path = os.path.join(UPLOAD_DIR, conversation_id, filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {filename} not found")

    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def get_file_bytes(conversation_id: str, filename: str) -> bytes:
    """
    Read file content as bytes.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the file

    Returns:
        File content as bytes

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    file_path = os.path.join(UPLOAD_DIR, conversation_id, filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {filename} not found")

    with open(file_path, 'rb') as f:
        return f.read()


def list_files(conversation_id: str) -> List[Dict]:
    """
    List all files for a conversation.

    Args:
        conversation_id: Unique conversation identifier

    Returns:
        List of file metadata dicts
    """
    upload_path = os.path.join(UPLOAD_DIR, conversation_id)

    if not os.path.exists(upload_path):
        return []

    files = []
    for filename in os.listdir(upload_path):
        file_path = os.path.join(upload_path, filename)
        if os.path.isfile(file_path):
            stat = os.stat(file_path)
            files.append({
                "filename": filename,
                "size": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": os.path.splitext(filename)[1].lower()
            })

    # Sort by upload time, newest first
    files.sort(key=lambda x: x["uploaded_at"], reverse=True)

    return files


def delete_file(conversation_id: str, filename: str) -> bool:
    """
    Delete a file from the conversation's upload directory.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the file

    Returns:
        True if file was deleted, False if file didn't exist
    """
    file_path = os.path.join(UPLOAD_DIR, conversation_id, filename)

    if not os.path.exists(file_path):
        return False

    os.remove(file_path)
    return True


def delete_all_files(conversation_id: str) -> int:
    """
    Delete all files for a conversation.

    Args:
        conversation_id: Unique conversation identifier

    Returns:
        Number of files deleted
    """
    upload_path = os.path.join(UPLOAD_DIR, conversation_id)

    if not os.path.exists(upload_path):
        return 0

    count = 0
    for filename in os.listdir(upload_path):
        file_path = os.path.join(upload_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            count += 1

    # Remove directory if empty
    try:
        os.rmdir(upload_path)
    except OSError:
        pass  # Directory not empty or other error

    return count


def get_file_info(conversation_id: str, filename: str) -> Optional[Dict]:
    """
    Get metadata for a specific file.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the file

    Returns:
        File metadata dict or None if file doesn't exist
    """
    file_path = os.path.join(UPLOAD_DIR, conversation_id, filename)

    if not os.path.exists(file_path):
        return None

    stat = os.stat(file_path)
    return {
        "filename": filename,
        "size": stat.st_size,
        "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": os.path.splitext(filename)[1].lower()
    }


def format_files_for_context(conversation_id: str, filenames: Optional[List[str]] = None) -> str:
    """
    Format file contents for inclusion in LLM context.

    Args:
        conversation_id: Unique conversation identifier
        filenames: Optional list of specific filenames to include (all files if None)

    Returns:
        Formatted string with file contents
    """
    if filenames is None:
        files = list_files(conversation_id)
        filenames = [f["filename"] for f in files]

    if not filenames:
        return ""

    context_parts = ["**Attached Files:**\n"]

    for filename in filenames:
        try:
            content = get_file_content(conversation_id, filename)
            context_parts.append(f"\n--- File: {filename} ---")
            context_parts.append(content)
            context_parts.append(f"--- End of {filename} ---\n")
        except Exception as e:
            context_parts.append(f"\n--- File: {filename} (Error reading: {str(e)}) ---\n")

    return "\n".join(context_parts)


def is_image_file(filename: str) -> bool:
    """Check if file is an image that can be used with vision models."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in IMAGE_EXTENSIONS


def get_image_base64(conversation_id: str, filename: str) -> Dict:
    """
    Get image as base64 for vision model API calls.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the image file

    Returns:
        Dict with base64 data and media type
    """
    import base64
    import mimetypes

    file_bytes = get_file_bytes(conversation_id, filename)
    base64_data = base64.b64encode(file_bytes).decode('utf-8')

    # Determine media type
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        ext = os.path.splitext(filename)[1].lower()
        mime_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_map.get(ext, 'image/png')

    return {
        "base64": base64_data,
        "media_type": mime_type,
        "filename": filename
    }


def extract_pdf_text(conversation_id: str, filename: str) -> str:
    """
    Extract text from a PDF file.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the PDF file

    Returns:
        Extracted text content
    """
    try:
        import fitz  # PyMuPDF

        file_path = os.path.join(UPLOAD_DIR, conversation_id, filename)
        doc = fitz.open(file_path)

        text_parts = []
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{text}")

        doc.close()
        return "\n\n".join(text_parts)
    except ImportError:
        return "[PDF extraction requires PyMuPDF: pip install pymupdf]"
    except Exception as e:
        return f"[Error extracting PDF: {str(e)}]"


def format_files_for_vision(conversation_id: str, filenames: List[str]) -> List[Dict]:
    """
    Format files for vision model API calls (multimodal content).

    Args:
        conversation_id: Unique conversation identifier
        filenames: List of filenames to include

    Returns:
        List of content parts for multimodal API call
    """
    content_parts = []

    for filename in filenames:
        ext = os.path.splitext(filename)[1].lower()

        if ext in IMAGE_EXTENSIONS:
            # Image - include as base64
            try:
                img_data = get_image_base64(conversation_id, filename)
                content_parts.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img_data["media_type"],
                        "data": img_data["base64"]
                    }
                })
            except Exception as e:
                content_parts.append({
                    "type": "text",
                    "text": f"[Error loading image {filename}: {str(e)}]"
                })
        elif ext == '.pdf':
            # PDF - extract text
            text = extract_pdf_text(conversation_id, filename)
            content_parts.append({
                "type": "text",
                "text": f"--- PDF: {filename} ---\n{text}\n--- End PDF ---"
            })
        else:
            # Text file
            try:
                content = get_file_content(conversation_id, filename)
                content_parts.append({
                    "type": "text",
                    "text": f"--- File: {filename} ---\n{content}\n--- End File ---"
                })
            except Exception as e:
                content_parts.append({
                    "type": "text",
                    "text": f"[Error reading {filename}: {str(e)}]"
                })

    return content_parts
