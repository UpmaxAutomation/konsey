"""File management for LLM Council conversations."""

import os
import re
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

# Tokenizer cache for tiktoken
_tokenizer = None


def _get_tokenizer():
    """Get cached tiktoken tokenizer (cl100k_base for GPT-4/Claude compatibility)."""
    global _tokenizer
    if _tokenizer is None:
        try:
            import tiktoken
            _tokenizer = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            return None
    return _tokenizer


def count_tokens(text: str) -> int:
    """
    Count tokens in text using tiktoken (accurate) or fallback to char estimate.

    Args:
        text: Text to count tokens for

    Returns:
        Token count
    """
    tokenizer = _get_tokenizer()
    if tokenizer is not None:
        return len(tokenizer.encode(text))
    # Fallback: rough estimate (4 chars per token)
    return len(text) // 4


def count_tokens_fast(text: str, sample_size: int = 10000) -> int:
    """
    Estimate token count for large texts by sampling.

    For files > sample_size chars, samples the beginning and extrapolates.
    This avoids tokenizing huge files just to check size.

    Args:
        text: Text to estimate tokens for
        sample_size: Number of chars to sample for estimation

    Returns:
        Estimated token count
    """
    if len(text) <= sample_size:
        return count_tokens(text)

    # Sample and extrapolate
    sample = text[:sample_size]
    sample_tokens = count_tokens(sample)
    ratio = sample_tokens / sample_size
    return int(len(text) * ratio)


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


def _safe_file_path(conversation_id: str, filename: str) -> str:
    """
    Construct a safe file path, preventing path traversal attacks.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the file

    Returns:
        Safe absolute file path

    Raises:
        ValueError: If path traversal is detected
    """
    # Validate filename doesn't contain path separators
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValueError("Invalid filename - cannot contain path separators")

    # Construct the path
    base_path = os.path.abspath(os.path.join(UPLOAD_DIR, conversation_id))
    file_path = os.path.abspath(os.path.join(base_path, filename))

    # Verify the resolved path is still within the base path
    if not file_path.startswith(base_path + os.sep) and file_path != base_path:
        raise ValueError("Invalid filename - path traversal detected")

    return file_path


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
    Read file content as text with graceful encoding handling.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the file

    Returns:
        File content as string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If path traversal is detected
    """
    file_path = _safe_file_path(conversation_id, filename)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {filename} not found")

    # Try multiple encodings
    encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']

    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    # If all encodings fail, read as binary and decode with errors='replace'
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            # Try to decode with replacement for invalid chars
            return content.decode('utf-8', errors='replace')
    except Exception:
        # Last resort - return placeholder
        return f"[Binary file - content cannot be displayed: {filename}]"


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
        ValueError: If path traversal is detected
    """
    file_path = _safe_file_path(conversation_id, filename)

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

    Raises:
        ValueError: If path traversal is detected
    """
    file_path = _safe_file_path(conversation_id, filename)

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

    Raises:
        ValueError: If path traversal is detected
    """
    file_path = _safe_file_path(conversation_id, filename)

    if not os.path.exists(file_path):
        return None

    stat = os.stat(file_path)
    return {
        "filename": filename,
        "size": stat.st_size,
        "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": os.path.splitext(filename)[1].lower()
    }


def format_files_for_context(
    conversation_id: str,
    filenames: Optional[List[str]] = None,
    max_tokens_per_file: int = 50_000,
    max_total_tokens: int = 100_000,
    query: Optional[str] = None
) -> str:
    """
    Format file contents for inclusion in LLM context with automatic truncation.

    When a query is provided, files are ranked by relevance so the most
    important content appears first (before potential truncation).

    Args:
        conversation_id: Unique conversation identifier
        filenames: Optional list of specific filenames to include (all files if None)
        max_tokens_per_file: Maximum tokens per individual file (default 50k)
        max_total_tokens: Maximum total tokens for all files (default 100k)
        query: Optional user query for relevance-based file ordering

    Returns:
        Formatted string with file contents
    """
    if filenames is None:
        files = list_files(conversation_id)
        filenames = [f["filename"] for f in files]

    if not filenames:
        return ""

    # Rank files by relevance if query provided
    if query:
        filenames = rank_files_by_relevance(conversation_id, filenames, query)

    context_parts = ["**Attached Files:**\n"]
    total_tokens = 0

    for filename in filenames:
        try:
            ext = os.path.splitext(filename)[1].lower()

            # Handle different file types
            if ext == '.pdf':
                content = extract_pdf_text(conversation_id, filename)
            elif ext in ('.docx', '.doc'):
                content = extract_docx_text(conversation_id, filename)
            elif ext in ('.xls', '.xlsx'):
                content = "[Excel files not yet supported - please convert to CSV]"
            elif is_image_file(filename):
                # Skip images - they should be handled separately via format_files_for_vision
                continue
            else:
                # Regular text file
                content = get_file_content(conversation_id, filename)

            # Truncate individual file if too large (with code-aware truncation for code files)
            content = truncate_file_content(content, max_tokens_per_file, ext)

            # Check if adding this file would exceed total limit
            file_tokens = count_tokens_fast(content)
            if total_tokens + file_tokens > max_total_tokens:
                remaining_tokens = max_total_tokens - total_tokens
                if remaining_tokens > 500:  # Only include if we have meaningful space
                    content = truncate_file_content(content, remaining_tokens, ext)
                else:
                    context_parts.append(f"\n--- File: {filename} (Skipped - context limit reached) ---\n")
                    continue

            context_parts.append(f"\n--- File: {filename} ---")
            context_parts.append(content)
            context_parts.append(f"--- End of {filename} ---\n")
            total_tokens += count_tokens_fast(content)

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
    Extract text from a PDF file with OCR fallback for scanned documents.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the PDF file

    Returns:
        Extracted text content
    """
    try:
        import fitz  # PyMuPDF

        file_path = _safe_file_path(conversation_id, filename)
        doc = fitz.open(file_path)
        num_pages = len(doc)

        # First pass: try text extraction
        text_parts = []
        total_chars = 0
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {page_num} ---\n{text}")
                total_chars += len(text)

        doc.close()

        # Check if this might be a scanned PDF (very little text per page)
        avg_chars_per_page = total_chars / max(num_pages, 1)

        if avg_chars_per_page < 50 and num_pages > 0:
            # Likely a scanned document - attempt OCR
            ocr_text = _extract_pdf_with_ocr(file_path, num_pages)
            if ocr_text:
                return ocr_text
            # If OCR failed or unavailable, return what we got (might be empty)
            if not text_parts:
                return "[Scanned PDF detected but OCR unavailable. Install tesseract: brew install tesseract (macOS) or apt-get install tesseract-ocr (Linux)]"

        return "\n\n".join(text_parts) if text_parts else "[PDF appears to be empty or contains only images]"
    except ImportError:
        return "[PDF extraction requires PyMuPDF: pip install pymupdf]"
    except Exception as e:
        return f"[Error extracting PDF: {str(e)}]"


def _extract_pdf_with_ocr(file_path: str, num_pages: int) -> Optional[str]:
    """
    Extract text from a scanned PDF using OCR.

    Args:
        file_path: Path to the PDF file
        num_pages: Number of pages in the PDF

    Returns:
        Extracted text or None if OCR unavailable
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract

        # Convert PDF pages to images (process in batches for large PDFs)
        text_parts = []
        batch_size = 5  # Process 5 pages at a time to manage memory

        for start_page in range(0, num_pages, batch_size):
            end_page = min(start_page + batch_size, num_pages)

            # Convert pages to images
            images = convert_from_path(
                file_path,
                first_page=start_page + 1,
                last_page=end_page,
                dpi=200  # Balance between quality and speed
            )

            for i, image in enumerate(images):
                page_num = start_page + i + 1
                # Run OCR on the image
                text = pytesseract.image_to_string(image)
                if text.strip():
                    text_parts.append(f"--- Page {page_num} (OCR) ---\n{text}")

                # Free memory
                image.close()

        return "\n\n".join(text_parts) if text_parts else None

    except ImportError:
        # pytesseract or pdf2image not installed
        return None
    except Exception as e:
        # OCR failed (tesseract not installed, etc.)
        print(f"OCR failed for {file_path}: {e}")
        return None


def extract_docx_text(conversation_id: str, filename: str) -> str:
    """
    Extract text from a .docx file.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the .docx file

    Returns:
        Extracted text content
    """
    try:
        from docx import Document

        file_path = _safe_file_path(conversation_id, filename)
        doc = Document(file_path)

        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text_parts.append(" | ".join(row_text))

        return "\n\n".join(text_parts)
    except ImportError:
        return "[DOCX extraction requires python-docx: pip install python-docx]"
    except Exception as e:
        return f"[Error extracting DOCX: {str(e)}]"


# Binary document extensions that need special handling
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx'}


def format_files_for_vision(
    conversation_id: str,
    filenames: List[str],
    query: Optional[str] = None
) -> List[Dict]:
    """
    Format files for vision model API calls (multimodal content).

    When a query is provided, non-image files are ranked by relevance.

    Args:
        conversation_id: Unique conversation identifier
        filenames: List of filenames to include
        query: Optional user query for relevance-based ordering

    Returns:
        List of content parts for multimodal API call
    """
    # Rank files by relevance if query provided
    if query:
        filenames = rank_files_by_relevance(conversation_id, filenames, query)

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


# Context size limits (in tokens)
MAX_CONTEXT_TOKENS = 100_000  # Total context budget
MAX_SINGLE_FILE_TOKENS = 50_000  # Per-file limit

# Common English stopwords for relevance scoring
STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
    'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who',
    'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few',
    'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
    'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now',
    'file', 'files', 'please', 'help', 'need', 'want', 'using', 'use'
}


def extract_keywords(text: str) -> List[str]:
    """
    Extract keywords from text, removing stopwords and normalizing.

    Args:
        text: Input text

    Returns:
        List of keywords (lowercase, no stopwords)
    """
    # Simple word extraction: lowercase, split on non-alphanumeric
    words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text.lower())
    # Filter stopwords and very short words
    return [w for w in words if w not in STOPWORDS and len(w) > 2]


def score_file_relevance(filename: str, content: str, query: str) -> float:
    """
    Score a file's relevance to a query using keyword matching.

    Args:
        filename: Name of the file
        content: File content
        query: User query

    Returns:
        Relevance score (higher = more relevant)
    """
    import math

    query_words = extract_keywords(query)
    if not query_words:
        return 0.0

    content_lower = content.lower()
    filename_lower = filename.lower()

    score = 0.0
    for word in query_words:
        # Count occurrences in content
        score += content_lower.count(word)
        # Bonus for filename match (10x weight)
        if word in filename_lower:
            score += 10

    # Normalize by content length to avoid bias toward long files
    content_length_factor = max(math.log10(len(content) / 1000 + 1), 1)
    score = score / content_length_factor

    return score


def rank_files_by_relevance(
    conversation_id: str,
    filenames: List[str],
    query: str
) -> List[str]:
    """
    Rank files by relevance to a query.

    Args:
        conversation_id: Unique conversation identifier
        filenames: List of filenames to rank
        query: User query

    Returns:
        List of filenames sorted by relevance (most relevant first)
    """
    if not query or not filenames:
        return filenames

    scored_files = []
    for filename in filenames:
        try:
            # Skip images for relevance scoring
            if is_image_file(filename):
                scored_files.append((filename, 0.0))
                continue

            content = get_file_content(conversation_id, filename)
            score = score_file_relevance(filename, content, query)
            scored_files.append((filename, score))
        except Exception:
            # On error, give neutral score
            scored_files.append((filename, 0.0))

    # Sort by score descending
    scored_files.sort(key=lambda x: x[1], reverse=True)

    return [f[0] for f in scored_files]


def calculate_context_size(conversation_id: str, filenames: Optional[List[str]] = None) -> Dict:
    """
    Calculate total context size for files and warn if too large.

    Args:
        conversation_id: Unique conversation identifier
        filenames: Optional list of specific filenames to check (all files if None)

    Returns:
        Dict with total_tokens, files breakdown, and warning/error flags
    """
    if filenames is None:
        files_list = list_files(conversation_id)
        filenames = [f["filename"] for f in files_list]

    if not filenames:
        return {
            "total_tokens": 0,
            "files": [],
            "warning": False,
            "error": False,
            "message": None
        }

    file_sizes = []
    total_tokens = 0

    for filename in filenames:
        try:
            if is_image_file(filename):
                # Images are roughly 1-2k tokens each for vision models
                tokens = 1500
                file_sizes.append({
                    "filename": filename,
                    "tokens": tokens,
                    "type": "image",
                    "truncated": False
                })
            else:
                # Text file - use tiktoken for accurate count
                content = get_file_content(conversation_id, filename)
                tokens = count_tokens_fast(content)

                truncated = tokens > MAX_SINGLE_FILE_TOKENS
                actual_tokens = min(tokens, MAX_SINGLE_FILE_TOKENS) if truncated else tokens

                file_sizes.append({
                    "filename": filename,
                    "tokens": actual_tokens,
                    "type": "text",
                    "truncated": truncated,
                    "original_tokens": tokens
                })
            total_tokens += file_sizes[-1]["tokens"]
        except Exception as e:
            file_sizes.append({
                "filename": filename,
                "tokens": 0,
                "type": "error",
                "error": str(e)
            })

    # Determine warning/error status
    warning = total_tokens > MAX_CONTEXT_TOKENS * 0.7  # 70% threshold
    error = total_tokens > MAX_CONTEXT_TOKENS

    message = None
    if error:
        message = f"Total file context ({total_tokens:,} tokens) exceeds limit ({MAX_CONTEXT_TOKENS:,} tokens). Files will be truncated."
    elif warning:
        message = f"Large file context ({total_tokens:,} tokens). Some models may have issues."

    return {
        "total_tokens": total_tokens,
        "files": file_sizes,
        "warning": warning,
        "error": error,
        "message": message,
        "limit": MAX_CONTEXT_TOKENS
    }


def truncate_file_content(content: str, max_tokens: int = MAX_SINGLE_FILE_TOKENS, file_ext: str = "") -> str:
    """
    Truncate file content to fit within token limit.

    Uses tiktoken for accurate truncation. For code files, attempts to truncate
    at logical boundaries (functions, classes) rather than mid-statement.

    Args:
        content: File content string
        max_tokens: Maximum tokens allowed
        file_ext: File extension for code-aware truncation (e.g., ".py", ".js")

    Returns:
        Truncated content with indicator if truncated
    """
    current_tokens = count_tokens_fast(content)

    if current_tokens <= max_tokens:
        return content

    # For code files, try code-aware truncation
    if file_ext in {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.rb', '.c', '.cpp', '.h'}:
        truncated = _truncate_code_aware(content, max_tokens, file_ext)
        if truncated:
            return truncated

    # Fallback: binary search for the right character position
    # Start with estimate and refine
    estimated_chars = int(len(content) * (max_tokens / current_tokens) * 0.95)  # 5% buffer

    # Find a good truncation point (paragraph or line boundary)
    truncation_point = _find_truncation_boundary(content, estimated_chars)

    truncated = content[:truncation_point]
    return f"{truncated}\n\n[... Content truncated ({current_tokens:,} tokens → {max_tokens:,} max) ...]"


def _truncate_code_aware(content: str, max_tokens: int, file_ext: str) -> Optional[str]:
    """
    Truncate code files at logical boundaries (functions, classes).

    Args:
        content: Code content
        max_tokens: Maximum tokens allowed
        file_ext: File extension (e.g., ".py", ".js")

    Returns:
        Truncated content or None if can't find good boundary
    """
    # Define boundary patterns for different languages
    if file_ext == '.py':
        # Python: match function/class definitions
        boundary_pattern = r'\n(?=(?:def |class |async def |@))'
    elif file_ext in {'.js', '.ts', '.jsx', '.tsx'}:
        # JavaScript/TypeScript: match function/class/export definitions
        boundary_pattern = r'\n(?=(?:function |class |export |const \w+ = |let \w+ = |var \w+ = |async function ))'
    elif file_ext in {'.java', '.c', '.cpp', '.h', '.go', '.rs'}:
        # C-style: match function definitions (simplified - looks for type + name + parens)
        boundary_pattern = r'\n(?=(?:public |private |protected |func |fn |void |int |string |bool |\w+\s+\w+\s*\())'
    elif file_ext == '.rb':
        # Ruby: match def/class/module
        boundary_pattern = r'\n(?=(?:def |class |module |end\n))'
    else:
        # Generic: try to find function-like patterns
        boundary_pattern = r'\n(?=(?:function |def |class ))'

    # Find all boundary positions
    boundaries = [0]  # Start of file is always a boundary
    for match in re.finditer(boundary_pattern, content):
        boundaries.append(match.start())

    if len(boundaries) <= 1:
        return None  # No good boundaries found

    # Estimate chars per token ratio from a sample
    sample = content[:min(5000, len(content))]
    sample_tokens = count_tokens(sample)
    chars_per_token = len(sample) / max(sample_tokens, 1)

    # Target character count (with buffer)
    target_chars = int(max_tokens * chars_per_token * 0.9)

    # Find the last boundary before target
    best_boundary = 0
    for boundary in boundaries:
        if boundary <= target_chars:
            best_boundary = boundary
        else:
            break

    if best_boundary == 0 and boundaries[0] == 0:
        # First boundary is already past our target, try first one anyway
        best_boundary = boundaries[1] if len(boundaries) > 1 else 0

    if best_boundary < len(content) * 0.1:
        return None  # Too little content would remain

    truncated = content[:best_boundary]

    # Verify token count and adjust if needed
    actual_tokens = count_tokens(truncated)
    if actual_tokens > max_tokens:
        # Still too big, fall back to paragraph truncation
        return None

    return f"{truncated}\n\n[... Code truncated at function boundary ({actual_tokens:,} of {count_tokens_fast(content):,} tokens) ...]"


def _find_truncation_boundary(content: str, target_pos: int) -> int:
    """
    Find a good boundary to truncate at (paragraph > line > word).

    Args:
        content: Full content
        target_pos: Target character position

    Returns:
        Best boundary position near target
    """
    if target_pos >= len(content):
        return len(content)

    # Look for paragraph boundary (double newline) within 500 chars before target
    search_start = max(0, target_pos - 500)
    search_region = content[search_start:target_pos]

    # Try paragraph boundary first
    para_pos = search_region.rfind('\n\n')
    if para_pos != -1:
        return search_start + para_pos

    # Try single newline
    line_pos = search_region.rfind('\n')
    if line_pos != -1:
        return search_start + line_pos

    # Fallback to space (word boundary)
    space_pos = search_region.rfind(' ')
    if space_pos != -1:
        return search_start + space_pos

    # Last resort: exact position
    return target_pos


# ============================================================================
# Code-Aware Chunking
# ============================================================================

# Language-specific boundary patterns for code chunking
CODE_BOUNDARY_PATTERNS = {
    '.py': {
        'pattern': r'^(?:def |class |async def |@\w+)',
        'block_end': None,  # Python uses indentation
        'description': 'Python function/class definitions'
    },
    '.js': {
        'pattern': r'^(?:function |class |export (?:default )?(?:function |class |const |let |var )|const \w+\s*=\s*(?:function|\(|async)|let \w+\s*=\s*(?:function|\(|async)|var \w+\s*=\s*(?:function|\(|async)|async function )',
        'block_end': r'^}',
        'description': 'JavaScript function/class/export definitions'
    },
    '.ts': {
        'pattern': r'^(?:function |class |export (?:default )?(?:function |class |const |let |var |interface |type )|const \w+\s*=\s*(?:function|\(|async)|interface |type \w+\s*=|async function )',
        'block_end': r'^}',
        'description': 'TypeScript function/class/interface definitions'
    },
    '.jsx': {
        'pattern': r'^(?:function |class |export (?:default )?(?:function |class |const |let |var )|const \w+\s*=\s*(?:function|\(|async)|let \w+\s*=\s*(?:function|\(|async)|async function )',
        'block_end': r'^}',
        'description': 'JSX component/function definitions'
    },
    '.tsx': {
        'pattern': r'^(?:function |class |export (?:default )?(?:function |class |const |let |var |interface |type )|const \w+\s*=\s*(?:function|\(|async)|interface |type \w+\s*=|async function )',
        'block_end': r'^}',
        'description': 'TSX component/function/interface definitions'
    },
    '.java': {
        'pattern': r'^(?:(?:public |private |protected |static |final |abstract )*(?:class |interface |enum |void |int |String |boolean |long |double |float |\w+(?:<[^>]+>)?\s+)\w+\s*(?:\([^)]*\)|{))',
        'block_end': r'^}',
        'description': 'Java class/method definitions'
    },
    '.go': {
        'pattern': r'^(?:func |type \w+ (?:struct|interface))',
        'block_end': r'^}',
        'description': 'Go function/type definitions'
    },
    '.rs': {
        'pattern': r'^(?:fn |pub fn |impl |struct |enum |trait |mod )',
        'block_end': r'^}',
        'description': 'Rust function/impl/struct definitions'
    },
    '.rb': {
        'pattern': r'^(?:def |class |module |private|protected|public)',
        'block_end': r'^end\b',
        'description': 'Ruby method/class/module definitions'
    },
    '.c': {
        'pattern': r'^(?:(?:static |extern |inline )?(?:void |int |char |long |double |float |unsigned |signed |\w+\s*\*?\s+)\w+\s*\([^;]*$)',
        'block_end': r'^}',
        'description': 'C function definitions'
    },
    '.cpp': {
        'pattern': r'^(?:(?:class |struct |namespace |template\s*<|(?:static |extern |inline |virtual )?(?:void |int |char |long |double |float |unsigned |signed |bool |auto |\w+(?:<[^>]+>)?\s*\*?\s*&?\s+)\w+\s*\([^;]*$))',
        'block_end': r'^}',
        'description': 'C++ class/function definitions'
    },
    '.h': {
        'pattern': r'^(?:(?:class |struct |namespace |template\s*<|(?:static |extern |inline |virtual )?(?:void |int |char |long |double |float |unsigned |signed |bool |auto |\w+(?:<[^>]+>)?\s*\*?\s*&?\s+)\w+\s*\([^;]*$))',
        'block_end': r'^}',
        'description': 'C/C++ header definitions'
    },
}


def chunk_code_aware(
    content: str,
    file_ext: str,
    max_tokens_per_chunk: int = 4000,
    overlap_tokens: int = 200
) -> List[Dict]:
    """
    Split code into logical chunks at function/class boundaries.

    This function intelligently splits code files at semantic boundaries
    (functions, classes, methods) rather than arbitrary character positions.
    Each chunk includes metadata about what it contains.

    Args:
        content: Code content to chunk
        file_ext: File extension (e.g., ".py", ".js") for language detection
        max_tokens_per_chunk: Maximum tokens per chunk (default 4000)
        overlap_tokens: Tokens to overlap between chunks for context (default 200)

    Returns:
        List of chunk dicts with keys:
        - content: The chunk text
        - start_line: Starting line number (1-indexed)
        - end_line: Ending line number
        - tokens: Token count
        - boundary_type: Type of boundary used ("function", "class", "generic")
        - definitions: List of function/class names found in chunk
    """
    if not content.strip():
        return []

    # Get language-specific patterns
    lang_config = CODE_BOUNDARY_PATTERNS.get(file_ext.lower())

    if not lang_config:
        # Fall back to generic chunking for unknown languages
        return _chunk_generic(content, max_tokens_per_chunk, overlap_tokens)

    lines = content.split('\n')
    chunks = []
    current_chunk_lines = []
    current_chunk_start = 1
    current_tokens = 0
    definitions_in_chunk = []

    boundary_pattern = re.compile(lang_config['pattern'], re.MULTILINE)

    i = 0
    while i < len(lines):
        line = lines[i]
        line_tokens = count_tokens(line + '\n')

        # Check if this line starts a new definition
        is_boundary = bool(boundary_pattern.match(line.lstrip()))

        # Extract definition name if it's a boundary
        if is_boundary:
            def_name = _extract_definition_name(line, file_ext)
            if def_name:
                definitions_in_chunk.append(def_name)

        # Check if adding this line would exceed limit
        if current_tokens + line_tokens > max_tokens_per_chunk and current_chunk_lines:
            # We need to split - try to find a good boundary
            if is_boundary:
                # Perfect - split right here before the new definition
                chunk_content = '\n'.join(current_chunk_lines)
                chunks.append({
                    'content': chunk_content,
                    'start_line': current_chunk_start,
                    'end_line': current_chunk_start + len(current_chunk_lines) - 1,
                    'tokens': current_tokens,
                    'boundary_type': 'definition',
                    'definitions': definitions_in_chunk[:-1] if definitions_in_chunk else []
                })

                # Start new chunk with overlap
                overlap_lines = _get_overlap_lines(current_chunk_lines, overlap_tokens)
                current_chunk_lines = overlap_lines + [line]
                current_chunk_start = current_chunk_start + len(current_chunk_lines) - len(overlap_lines) - 1
                current_tokens = count_tokens('\n'.join(current_chunk_lines))
                definitions_in_chunk = [def_name] if def_name else []
            else:
                # Not at a boundary - look backwards for one
                split_point = _find_code_split_point(current_chunk_lines, lang_config)

                if split_point > 0:
                    # Found a good split point
                    chunk_content = '\n'.join(current_chunk_lines[:split_point])
                    chunks.append({
                        'content': chunk_content,
                        'start_line': current_chunk_start,
                        'end_line': current_chunk_start + split_point - 1,
                        'tokens': count_tokens(chunk_content),
                        'boundary_type': 'definition',
                        'definitions': _extract_definitions_from_lines(current_chunk_lines[:split_point], file_ext)
                    })

                    # Start new chunk from split point
                    remaining_lines = current_chunk_lines[split_point:]
                    current_chunk_lines = remaining_lines + [line]
                    current_chunk_start = current_chunk_start + split_point
                    current_tokens = count_tokens('\n'.join(current_chunk_lines))
                    definitions_in_chunk = _extract_definitions_from_lines(current_chunk_lines, file_ext)
                else:
                    # No good boundary found - force split
                    chunk_content = '\n'.join(current_chunk_lines)
                    chunks.append({
                        'content': chunk_content,
                        'start_line': current_chunk_start,
                        'end_line': current_chunk_start + len(current_chunk_lines) - 1,
                        'tokens': current_tokens,
                        'boundary_type': 'forced',
                        'definitions': definitions_in_chunk
                    })

                    # Start new chunk with overlap
                    overlap_lines = _get_overlap_lines(current_chunk_lines, overlap_tokens)
                    current_chunk_lines = overlap_lines + [line]
                    current_chunk_start = current_chunk_start + len(current_chunk_lines) - len(overlap_lines) - 1
                    current_tokens = count_tokens('\n'.join(current_chunk_lines))
                    definitions_in_chunk = []
        else:
            current_chunk_lines.append(line)
            current_tokens += line_tokens

        i += 1

    # Don't forget the last chunk
    if current_chunk_lines:
        chunk_content = '\n'.join(current_chunk_lines)
        chunks.append({
            'content': chunk_content,
            'start_line': current_chunk_start,
            'end_line': current_chunk_start + len(current_chunk_lines) - 1,
            'tokens': count_tokens(chunk_content),
            'boundary_type': 'end_of_file',
            'definitions': definitions_in_chunk
        })

    return chunks


def _extract_definition_name(line: str, file_ext: str) -> Optional[str]:
    """Extract the name of a function/class from a definition line."""
    line = line.strip()

    # Python
    if file_ext == '.py':
        match = re.match(r'^(?:async\s+)?(?:def|class)\s+(\w+)', line)
        if match:
            return match.group(1)

    # JavaScript/TypeScript
    elif file_ext in {'.js', '.ts', '.jsx', '.tsx'}:
        # function name() or async function name()
        match = re.match(r'^(?:async\s+)?function\s+(\w+)', line)
        if match:
            return match.group(1)
        # class Name
        match = re.match(r'^class\s+(\w+)', line)
        if match:
            return match.group(1)
        # const/let/var name =
        match = re.match(r'^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=', line)
        if match:
            return match.group(1)
        # interface/type Name
        match = re.match(r'^(?:export\s+)?(?:interface|type)\s+(\w+)', line)
        if match:
            return match.group(1)

    # Go
    elif file_ext == '.go':
        match = re.match(r'^func\s+(?:\([^)]+\)\s+)?(\w+)', line)
        if match:
            return match.group(1)
        match = re.match(r'^type\s+(\w+)', line)
        if match:
            return match.group(1)

    # Rust
    elif file_ext == '.rs':
        match = re.match(r'^(?:pub\s+)?fn\s+(\w+)', line)
        if match:
            return match.group(1)
        match = re.match(r'^(?:pub\s+)?(?:struct|enum|trait|impl)\s+(\w+)', line)
        if match:
            return match.group(1)

    # Ruby
    elif file_ext == '.rb':
        match = re.match(r'^(?:def|class|module)\s+(\w+)', line)
        if match:
            return match.group(1)

    # Java
    elif file_ext == '.java':
        match = re.match(r'^(?:public|private|protected)?\s*(?:static\s+)?(?:class|interface|enum)\s+(\w+)', line)
        if match:
            return match.group(1)

    # C/C++
    elif file_ext in {'.c', '.cpp', '.h'}:
        # Look for function-like patterns
        match = re.match(r'^(?:\w+\s+)+(\w+)\s*\(', line)
        if match:
            return match.group(1)

    return None


def _extract_definitions_from_lines(lines: List[str], file_ext: str) -> List[str]:
    """Extract all definition names from a list of lines."""
    definitions = []
    for line in lines:
        name = _extract_definition_name(line, file_ext)
        if name:
            definitions.append(name)
    return definitions


def _find_code_split_point(lines: List[str], lang_config: Dict) -> int:
    """
    Find a good split point in code lines, looking backwards for a definition boundary.

    Returns the index to split at (0 if no good boundary found).
    """
    boundary_pattern = re.compile(lang_config['pattern'], re.MULTILINE)

    # Look backwards through lines for a boundary
    for i in range(len(lines) - 1, max(0, len(lines) - 50), -1):
        if boundary_pattern.match(lines[i].lstrip()):
            return i

    return 0


def _get_overlap_lines(lines: List[str], overlap_tokens: int) -> List[str]:
    """Get lines from the end of a chunk to use as overlap for context."""
    if not lines or overlap_tokens <= 0:
        return []

    overlap_lines = []
    current_tokens = 0

    for line in reversed(lines):
        line_tokens = count_tokens(line + '\n')
        if current_tokens + line_tokens > overlap_tokens:
            break
        overlap_lines.insert(0, line)
        current_tokens += line_tokens

    return overlap_lines


def _chunk_generic(
    content: str,
    max_tokens_per_chunk: int,
    overlap_tokens: int
) -> List[Dict]:
    """
    Generic chunking for unknown file types - splits at paragraph/line boundaries.

    Args:
        content: Text content to chunk
        max_tokens_per_chunk: Maximum tokens per chunk
        overlap_tokens: Tokens to overlap between chunks

    Returns:
        List of chunk dicts
    """
    lines = content.split('\n')
    chunks = []
    current_chunk_lines = []
    current_chunk_start = 1
    current_tokens = 0

    for i, line in enumerate(lines):
        line_tokens = count_tokens(line + '\n')

        if current_tokens + line_tokens > max_tokens_per_chunk and current_chunk_lines:
            # Need to split
            chunk_content = '\n'.join(current_chunk_lines)
            chunks.append({
                'content': chunk_content,
                'start_line': current_chunk_start,
                'end_line': current_chunk_start + len(current_chunk_lines) - 1,
                'tokens': current_tokens,
                'boundary_type': 'line',
                'definitions': []
            })

            # Start new chunk with overlap
            overlap_lines = _get_overlap_lines(current_chunk_lines, overlap_tokens)
            current_chunk_lines = overlap_lines + [line]
            current_chunk_start = i + 1 - len(overlap_lines)
            current_tokens = count_tokens('\n'.join(current_chunk_lines))
        else:
            current_chunk_lines.append(line)
            current_tokens += line_tokens

    # Final chunk
    if current_chunk_lines:
        chunk_content = '\n'.join(current_chunk_lines)
        chunks.append({
            'content': chunk_content,
            'start_line': current_chunk_start,
            'end_line': current_chunk_start + len(current_chunk_lines) - 1,
            'tokens': count_tokens(chunk_content),
            'boundary_type': 'end_of_file',
            'definitions': []
        })

    return chunks


def chunk_file(
    conversation_id: str,
    filename: str,
    max_tokens_per_chunk: int = 4000,
    overlap_tokens: int = 200
) -> List[Dict]:
    """
    Chunk a file from conversation storage using appropriate strategy.

    For code files, uses code-aware chunking at function/class boundaries.
    For other files, uses generic paragraph/line-based chunking.

    Args:
        conversation_id: Unique conversation identifier
        filename: Name of the file to chunk
        max_tokens_per_chunk: Maximum tokens per chunk
        overlap_tokens: Tokens to overlap between chunks

    Returns:
        List of chunk dicts with content, line numbers, tokens, and metadata

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    content = get_file_content(conversation_id, filename)
    file_ext = os.path.splitext(filename)[1].lower()

    # Use code-aware chunking for supported languages
    if file_ext in CODE_BOUNDARY_PATTERNS:
        chunks = chunk_code_aware(content, file_ext, max_tokens_per_chunk, overlap_tokens)
    else:
        chunks = _chunk_generic(content, max_tokens_per_chunk, overlap_tokens)

    # Add filename to each chunk
    for chunk in chunks:
        chunk['filename'] = filename

    return chunks
