"""Integration and Persona routes for LLM Council."""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..config import (
    get_personas, get_model_persona, set_model_persona, create_custom_persona,
)
from ..integrations import (
    gdrive_list_files, gdrive_get_file_content, gdrive_upload_file,
    slack_send_message, slack_send_webhook, slack_list_channels,
    github_list_repos, github_get_file, github_list_issues,
    github_create_issue, github_list_prs, get_integration_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["integrations"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class GDriveListRequest(BaseModel):
    access_token: str
    folder_id: Optional[str] = None
    page_size: int = 20
    page_token: Optional[str] = None


class GDriveFileRequest(BaseModel):
    access_token: str
    file_id: str


class GDriveUploadRequest(BaseModel):
    access_token: str
    name: str
    content: str
    mime_type: str = "text/plain"
    folder_id: Optional[str] = None


class SlackMessageRequest(BaseModel):
    channel: str
    text: str
    thread_ts: Optional[str] = None


class SlackWebhookRequest(BaseModel):
    text: str
    username: Optional[str] = "LLM Council"


class GitHubFileRequest(BaseModel):
    owner: str
    repo: str
    path: str
    ref: str = "main"


class GitHubIssueRequest(BaseModel):
    owner: str
    repo: str
    title: str
    body: str
    labels: Optional[List[str]] = None
    assignees: Optional[List[str]] = None


class SetPersonaRequest(BaseModel):
    model_id: str
    persona_key: str  # Can be a default persona key, custom persona ID, or empty string


class CreatePersonaRequest(BaseModel):
    persona_id: str
    persona_text: str


# ──────────────────────────────────────────────
# Integration Status
# ──────────────────────────────────────────────

@router.get(
    "/integrations/status",
    tags=["integrations"],
    summary="Get Integration Status",
    response_description="Status of all configured integrations"
)
async def get_integrations_status():
    """
    Get status of all available external integrations.

    Returns the connection status and configuration state of all
    supported integrations (Google Drive, Slack, GitHub, etc.).

    Returns:
        dict: Integration status containing:
            - gdrive: Google Drive connection status
            - slack: Slack connection status
            - github: GitHub connection status
            - Each with: configured, connected, error fields
    """
    return get_integration_status()


# ──────────────────────────────────────────────
# Google Drive
# ──────────────────────────────────────────────

@router.post(
    "/integrations/gdrive/list",
    tags=["integrations"],
    summary="List Google Drive Files",
    response_description="List of files in Google Drive"
)
async def gdrive_list(request: GDriveListRequest):
    """
    List files in Google Drive.

    Retrieves files and folders from Google Drive with pagination support.

    Args:
        request: GDriveListRequest containing:
            - access_token: OAuth2 access token
            - folder_id: Optional folder ID to list (root if not specified)
            - page_size: Number of results per page (default: 20)
            - page_token: Token for next page of results

    Returns:
        dict: File listing containing:
            - files: List of file metadata (id, name, mimeType, etc.)
            - nextPageToken: Token for pagination (if more results)

    Raises:
        HTTPException 400: If Google Drive API returns an error
    """
    result = await gdrive_list_files(
        access_token=request.access_token,
        folder_id=request.folder_id,
        page_size=request.page_size,
        page_token=request.page_token
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post(
    "/integrations/gdrive/file",
    tags=["integrations"],
    summary="Get Google Drive File",
    response_description="File content from Google Drive"
)
async def gdrive_get_file(request: GDriveFileRequest):
    """
    Get file content from Google Drive.

    Downloads and returns the content of a file from Google Drive.

    Args:
        request: GDriveFileRequest containing:
            - access_token: OAuth2 access token
            - file_id: Google Drive file ID

    Returns:
        dict: File content containing:
            - content: File content (text or base64 for binary)
            - mimeType: File MIME type
            - name: File name

    Raises:
        HTTPException 400: If file cannot be retrieved
    """
    result = await gdrive_get_file_content(
        access_token=request.access_token,
        file_id=request.file_id
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post(
    "/integrations/gdrive/upload",
    tags=["integrations"],
    summary="Upload to Google Drive",
    response_description="Uploaded file metadata"
)
async def gdrive_upload(request: GDriveUploadRequest):
    """
    Upload a file to Google Drive.

    Creates a new file in Google Drive with the specified content.

    Args:
        request: GDriveUploadRequest containing:
            - access_token: OAuth2 access token
            - name: File name
            - content: File content (text or base64)
            - mime_type: MIME type (default: "text/plain")
            - folder_id: Optional destination folder ID

    Returns:
        dict: Upload result containing:
            - id: Created file ID
            - name: File name
            - webViewLink: URL to view file in browser

    Raises:
        HTTPException 400: If upload fails
    """
    result = await gdrive_upload_file(
        access_token=request.access_token,
        name=request.name,
        content=request.content,
        mime_type=request.mime_type,
        folder_id=request.folder_id
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ──────────────────────────────────────────────
# Slack
# ──────────────────────────────────────────────

@router.post(
    "/integrations/slack/message",
    tags=["integrations"],
    summary="Send Slack Message",
    response_description="Message send confirmation"
)
async def slack_message(request: SlackMessageRequest):
    """
    Send a message to a Slack channel.

    Posts a message to the specified Slack channel using the Bot API.

    Args:
        request: SlackMessageRequest containing:
            - channel: Channel ID or name
            - text: Message text (supports Slack markdown)
            - thread_ts: Optional thread timestamp to reply to

    Returns:
        dict: Send result containing:
            - ok: Boolean success status
            - ts: Message timestamp
            - channel: Channel where message was posted

    Raises:
        HTTPException 400: If message fails to send
    """
    result = await slack_send_message(
        channel=request.channel,
        text=request.text,
        thread_ts=request.thread_ts
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post(
    "/integrations/slack/webhook",
    tags=["integrations"],
    summary="Send Slack Webhook",
    response_description="Webhook send confirmation"
)
async def slack_webhook(request: SlackWebhookRequest):
    """
    Send a message via Slack incoming webhook.

    Posts a message using a configured webhook URL (no Bot token required).

    Args:
        request: SlackWebhookRequest containing:
            - text: Message text
            - username: Display name (default: "LLM Council")

    Returns:
        dict: Send result containing:
            - ok: Boolean success status

    Raises:
        HTTPException 400: If webhook send fails
    """
    result = await slack_send_webhook(
        text=request.text,
        username=request.username
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get(
    "/integrations/slack/channels",
    tags=["integrations"],
    summary="List Slack Channels",
    response_description="Available Slack channels"
)
async def slack_channels():
    """
    List available Slack channels.

    Retrieves channels accessible to the configured Slack bot.

    Returns:
        dict: Channel list containing:
            - channels: List of channel objects with id, name, is_private

    Raises:
        HTTPException 400: If channel list fails
    """
    result = await slack_list_channels()
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ──────────────────────────────────────────────
# GitHub
# ──────────────────────────────────────────────

@router.get(
    "/integrations/github/repos",
    tags=["integrations"],
    summary="List GitHub Repositories",
    response_description="GitHub repository list"
)
async def github_repos(username: Optional[str] = None, org: Optional[str] = None):
    """
    List GitHub repositories.

    Retrieves repositories for a user or organization.

    Args:
        username: GitHub username to list repos for (optional)
        org: GitHub organization to list repos for (optional)
        If neither specified, lists authenticated user's repos.

    Returns:
        dict: Repository list containing:
            - repos: List of repo objects with name, full_name, description, url

    Raises:
        HTTPException 400: If GitHub API returns an error
    """
    result = await github_list_repos(username=username, org=org)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post(
    "/integrations/github/file",
    tags=["integrations"],
    summary="Get GitHub File",
    response_description="File content from GitHub repository"
)
async def github_file(request: GitHubFileRequest):
    """
    Get file content from a GitHub repository.

    Retrieves the content of a file from a GitHub repository.

    Args:
        request: GitHubFileRequest containing:
            - owner: Repository owner (user or org)
            - repo: Repository name
            - path: File path within repository
            - ref: Branch, tag, or commit (default: "main")

    Returns:
        dict: File content containing:
            - content: Decoded file content
            - sha: File SHA
            - path: File path

    Raises:
        HTTPException 400: If file cannot be retrieved
    """
    result = await github_get_file(
        owner=request.owner,
        repo=request.repo,
        path=request.path,
        ref=request.ref
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get(
    "/integrations/github/issues/{owner}/{repo}",
    tags=["integrations"],
    summary="List GitHub Issues",
    response_description="Repository issues"
)
async def github_issues(owner: str, repo: str, state: str = "open"):
    """
    List issues in a GitHub repository.

    Retrieves issues from a GitHub repository with state filter.

    Args:
        owner: Repository owner (user or org)
        repo: Repository name
        state: Issue state filter: "open", "closed", or "all" (default: "open")

    Returns:
        dict: Issue list containing:
            - issues: List of issue objects with number, title, state, labels

    Raises:
        HTTPException 400: If issues cannot be retrieved
    """
    result = await github_list_issues(owner=owner, repo=repo, state=state)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post(
    "/integrations/github/issues",
    tags=["integrations"],
    summary="Create GitHub Issue",
    response_description="Created issue details"
)
async def github_create(request: GitHubIssueRequest):
    """
    Create an issue in a GitHub repository.

    Creates a new issue with the specified details.

    Args:
        request: GitHubIssueRequest containing:
            - owner: Repository owner
            - repo: Repository name
            - title: Issue title
            - body: Issue body (markdown supported)
            - labels: Optional list of label names
            - assignees: Optional list of assignee usernames

    Returns:
        dict: Created issue containing:
            - number: Issue number
            - html_url: URL to view issue
            - title: Issue title

    Raises:
        HTTPException 400: If issue creation fails
    """
    result = await github_create_issue(
        owner=request.owner,
        repo=request.repo,
        title=request.title,
        body=request.body,
        labels=request.labels,
        assignees=request.assignees
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get(
    "/integrations/github/pulls/{owner}/{repo}",
    tags=["integrations"],
    summary="List GitHub Pull Requests",
    response_description="Repository pull requests"
)
async def github_pulls(owner: str, repo: str, state: str = "open"):
    """
    List pull requests in a GitHub repository.

    Retrieves pull requests from a GitHub repository with state filter.

    Args:
        owner: Repository owner (user or org)
        repo: Repository name
        state: PR state filter: "open", "closed", or "all" (default: "open")

    Returns:
        dict: Pull request list containing:
            - pulls: List of PR objects with number, title, state, head, base

    Raises:
        HTTPException 400: If pull requests cannot be retrieved
    """
    result = await github_list_prs(owner=owner, repo=repo, state=state)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# ──────────────────────────────────────────────
# Personas
# ──────────────────────────────────────────────

@router.get(
    "/personas",
    tags=["personas"],
    summary="List All Personas",
    response_description="Available personas including defaults and custom"
)
async def get_all_personas():
    """
    Get all available personas (default + custom).

    Personas customize how models respond by prepending system prompts.
    This returns both built-in default personas and user-created custom personas.

    Returns:
        dict: Persona collections containing:
            - default_personas: Built-in persona options (e.g., concise, detailed, creative)
            - custom_personas: User-created custom personas
            - model_assignments: Current persona assignments per model
    """
    return get_personas()


@router.post(
    "/personas",
    tags=["personas"],
    summary="Assign Persona to Model",
    response_description="Updated persona assignment"
)
async def set_persona(request: SetPersonaRequest):
    """
    Assign a persona to a specific model.

    Associates a persona with a model so that persona's system prompt
    is included when querying that model.

    Args:
        request: SetPersonaRequest containing:
            - model_id: The model identifier to assign persona to
            - persona_key: Persona key (default key, custom ID, or empty to clear)

    Returns:
        dict: Assignment result containing:
            - model_id: The model that was updated
            - persona_key: The assigned persona key
            - persona_text: The full persona text now active
    """
    set_model_persona(request.model_id, request.persona_key)
    return {
        "model_id": request.model_id,
        "persona_key": request.persona_key,
        "persona_text": get_model_persona(request.model_id)
    }


@router.post(
    "/personas/custom",
    tags=["personas"],
    summary="Create Custom Persona",
    response_description="Created custom persona"
)
async def create_persona(request: CreatePersonaRequest):
    """
    Create a custom persona with user-defined system prompt.

    Custom personas allow defining specialized behavior for models
    beyond the built-in default personas.

    Args:
        request: CreatePersonaRequest containing:
            - persona_id: Unique identifier for the persona
            - persona_text: The system prompt text for this persona

    Returns:
        dict: Created persona containing:
            - persona_id: The ID of the created persona
            - persona_text: The persona system prompt text

    Example:
        ```json
        {
            "persona_id": "code_reviewer",
            "persona_text": "You are an expert code reviewer. Focus on..."
        }
        ```
    """
    persona_id = create_custom_persona(request.persona_id, request.persona_text)
    return {
        "persona_id": persona_id,
        "persona_text": request.persona_text
    }
