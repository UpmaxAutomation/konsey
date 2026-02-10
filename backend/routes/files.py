"""File upload and management routes for LLM Council."""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_optional
from ..database.connection import get_db
from ..database.models import User
from .. import storage_adapter as storage, files

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["files"])


# ──────────────────────────────────────────────
# File endpoints
# ──────────────────────────────────────────────

@router.post(
    "/conversations/{conversation_id}/upload",
    tags=["files"],
    summary="Upload File to Conversation",
    response_description="Upload confirmation with file metadata"
)
async def upload_file(
    conversation_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a file to a conversation.

    Files can be attached to messages for analysis by the council.
    Supported formats include text files, code files, PDFs, and images.

    Args:
        conversation_id: The conversation to upload to
        file: The file to upload (multipart/form-data)

    Returns:
        dict: Upload confirmation with file metadata (id, size, type)

    Raises:
        HTTPException 404: If conversation not found
        HTTPException 400: If file type not supported
        HTTPException 500: If upload fails
    """
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        content = await file.read()
        metadata = files.save_file(conversation_id, file.filename, content)
        return {"status": "success", "message": f"File '{file.filename}' uploaded successfully", **metadata}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get(
    "/conversations/{conversation_id}/files",
    tags=["files"],
    summary="List Conversation Files",
    response_description="List of uploaded files"
)
async def list_conversation_files(
    conversation_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    List all files uploaded to a conversation.

    Returns metadata for all files including name, size, and upload time.

    Args:
        conversation_id: The conversation to list files for

    Returns:
        dict: Object with files list and count

    Raises:
        HTTPException 404: If conversation not found
    """
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    file_list = files.list_files(conversation_id)
    return {"conversation_id": conversation_id, "files": file_list, "count": len(file_list)}


@router.get(
    "/conversations/{conversation_id}/files/context-size",
    tags=["files"],
    summary="Get Context Size",
    response_description="File context size analysis"
)
async def get_context_size(
    conversation_id: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate the total context size of attached files.

    Returns token estimates for all files and warns if context is too large.
    Useful for determining if files will fit within LLM context limits.

    Args:
        conversation_id: The conversation to analyze

    Returns:
        dict: Context size analysis with total tokens, per-file breakdown,
              and warning/error flags if context is too large

    Raises:
        HTTPException 404: If conversation not found
    """
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    context_info = files.calculate_context_size(conversation_id)
    return {"conversation_id": conversation_id, **context_info}


@router.get(
    "/conversations/{conversation_id}/files/{filename}",
    tags=["files"],
    summary="Download File",
    response_description="File content as download"
)
async def download_file(
    conversation_id: str,
    filename: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Download a file from a conversation.

    Returns the file content as a binary download.

    Args:
        conversation_id: The conversation containing the file
        filename: The name of the file to download

    Returns:
        FileResponse: The file content for download

    Raises:
        HTTPException 404: If conversation or file not found
        HTTPException 500: If download fails
    """
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        file_info = files.get_file_info(conversation_id, filename)
        if file_info is None:
            raise HTTPException(status_code=404, detail="File not found")

        file_path = os.path.join(files.UPLOAD_DIR, conversation_id, filename)
        return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@router.delete(
    "/conversations/{conversation_id}/files/{filename}",
    tags=["files"],
    summary="Delete Conversation File",
    response_description="Deletion confirmation"
)
async def delete_conversation_file(
    conversation_id: str,
    filename: str,
    current_user: User = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a file from a conversation's file storage.

    Permanently removes a file that was previously uploaded to the conversation.
    This action cannot be undone.

    Args:
        conversation_id: The conversation ID containing the file
        filename: The name of the file to delete

    Returns:
        dict: Deletion confirmation containing:
            - status: "success"
            - message: Confirmation message with filename

    Raises:
        HTTPException 404: If conversation or file not found
    """
    user_id = current_user.id if current_user else None
    conversation = await storage.get_conversation(conversation_id, user_id=user_id, db=db)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    deleted = files.delete_file(conversation_id, filename)
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    return {"status": "success", "message": f"File '{filename}' deleted successfully"}
