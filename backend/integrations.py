"""
External Integrations Module for LLM Council.

Provides integrations with:
- Google Drive: File storage, sharing, and import
- Slack: Notifications and channel messaging
- GitHub: Repository access, issues, PRs
"""

import asyncio
import aiohttp
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

# API Keys and Tokens
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


class IntegrationType(str, Enum):
    GOOGLE_DRIVE = "google_drive"
    SLACK = "slack"
    GITHUB = "github"


class IntegrationStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class IntegrationConfig:
    """Configuration for an external integration."""
    type: IntegrationType
    enabled: bool = False
    status: IntegrationStatus = IntegrationStatus.DISCONNECTED
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    settings: Dict[str, Any] = field(default_factory=dict)
    last_sync: Optional[str] = None
    error: Optional[str] = None


# Store integration configs
_integrations: Dict[str, IntegrationConfig] = {}


# ============ GOOGLE DRIVE INTEGRATION ============

async def gdrive_list_files(
    access_token: str,
    folder_id: Optional[str] = None,
    page_size: int = 20,
    page_token: Optional[str] = None
) -> Dict[str, Any]:
    """List files in Google Drive."""
    try:
        query = "trashed = false"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        params = {
            "pageSize": page_size,
            "fields": "nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)",
            "q": query
        }
        if page_token:
            params["pageToken"] = page_token

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.googleapis.com/drive/v3/files",
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error = await response.json()
                    return {"error": error.get("error", {}).get("message", "Failed to list files")}

                return await response.json()

    except Exception as e:
        return {"error": str(e)}


async def gdrive_get_file_content(
    access_token: str,
    file_id: str
) -> Dict[str, Any]:
    """Download file content from Google Drive."""
    try:
        async with aiohttp.ClientSession() as session:
            # Get file metadata first
            async with session.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "id, name, mimeType, size"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as meta_response:
                if meta_response.status != 200:
                    return {"error": "File not found"}
                metadata = await meta_response.json()

            # Download content
            async with session.get(
                f"https://www.googleapis.com/drive/v3/files/{file_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"alt": "media"},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as content_response:
                if content_response.status != 200:
                    return {"error": "Failed to download file"}

                content = await content_response.read()

                # Try to decode as text if it's a text file
                if metadata.get("mimeType", "").startswith("text/"):
                    try:
                        content = content.decode("utf-8")
                    except (UnicodeDecodeError, AttributeError):
                        content = content.decode("latin-1")
                else:
                    import base64
                    content = base64.b64encode(content).decode("utf-8")

                return {
                    "id": metadata["id"],
                    "name": metadata["name"],
                    "mimeType": metadata["mimeType"],
                    "content": content
                }

    except Exception as e:
        return {"error": str(e)}


async def gdrive_upload_file(
    access_token: str,
    name: str,
    content: str,
    mime_type: str = "text/plain",
    folder_id: Optional[str] = None
) -> Dict[str, Any]:
    """Upload a file to Google Drive."""
    try:
        metadata = {"name": name, "mimeType": mime_type}
        if folder_id:
            metadata["parents"] = [folder_id]

        async with aiohttp.ClientSession() as session:
            # Create file with metadata
            async with session.post(
                "https://www.googleapis.com/upload/drive/v3/files",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={"uploadType": "multipart"},
                json=metadata,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    error = await response.json()
                    return {"error": error.get("error", {}).get("message", "Upload failed")}

                return await response.json()

    except Exception as e:
        return {"error": str(e)}


# ============ SLACK INTEGRATION ============

async def slack_send_message(
    channel: str,
    text: str,
    blocks: Optional[List[Dict]] = None,
    thread_ts: Optional[str] = None
) -> Dict[str, Any]:
    """Send a message to a Slack channel."""
    if not SLACK_BOT_TOKEN:
        return {"error": "Slack bot token not configured"}

    try:
        payload = {
            "channel": channel,
            "text": text
        }
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://slack.com/api/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                data = await response.json()

                if not data.get("ok"):
                    return {"error": data.get("error", "Failed to send message")}

                return {
                    "success": True,
                    "channel": data.get("channel"),
                    "ts": data.get("ts"),
                    "message": data.get("message")
                }

    except Exception as e:
        return {"error": str(e)}


async def slack_send_webhook(
    text: str,
    username: Optional[str] = "LLM Council",
    icon_emoji: Optional[str] = ":robot_face:",
    attachments: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """Send a message via Slack webhook."""
    if not SLACK_WEBHOOK_URL:
        return {"error": "Slack webhook URL not configured"}

    try:
        payload = {
            "text": text,
            "username": username,
            "icon_emoji": icon_emoji
        }
        if attachments:
            payload["attachments"] = attachments

        async with aiohttp.ClientSession() as session:
            async with session.post(
                SLACK_WEBHOOK_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    return {"error": f"Webhook failed: {response.status}"}

                return {"success": True}

    except Exception as e:
        return {"error": str(e)}


async def slack_list_channels() -> Dict[str, Any]:
    """List Slack channels."""
    if not SLACK_BOT_TOKEN:
        return {"error": "Slack bot token not configured"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://slack.com/api/conversations.list",
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
                params={"types": "public_channel,private_channel", "limit": 100},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                data = await response.json()

                if not data.get("ok"):
                    return {"error": data.get("error", "Failed to list channels")}

                return {
                    "channels": [
                        {
                            "id": ch["id"],
                            "name": ch["name"],
                            "is_private": ch.get("is_private", False),
                            "num_members": ch.get("num_members", 0)
                        }
                        for ch in data.get("channels", [])
                    ]
                }

    except Exception as e:
        return {"error": str(e)}


# ============ GITHUB INTEGRATION ============

async def github_list_repos(
    username: Optional[str] = None,
    org: Optional[str] = None,
    per_page: int = 30
) -> Dict[str, Any]:
    """List GitHub repositories."""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}

    try:
        if org:
            url = f"https://api.github.com/orgs/{org}/repos"
        elif username:
            url = f"https://api.github.com/users/{username}/repos"
        else:
            url = "https://api.github.com/user/repos"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"per_page": per_page, "sort": "updated"},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error = await response.json()
                    return {"error": error.get("message", "Failed to list repos")}

                repos = await response.json()
                return {
                    "repos": [
                        {
                            "id": repo["id"],
                            "name": repo["name"],
                            "full_name": repo["full_name"],
                            "description": repo.get("description"),
                            "html_url": repo["html_url"],
                            "language": repo.get("language"),
                            "stars": repo.get("stargazers_count", 0),
                            "forks": repo.get("forks_count", 0),
                            "updated_at": repo.get("updated_at"),
                            "private": repo.get("private", False)
                        }
                        for repo in repos
                    ]
                }

    except Exception as e:
        return {"error": str(e)}


async def github_get_file(
    owner: str,
    repo: str,
    path: str,
    ref: str = "main"
) -> Dict[str, Any]:
    """Get file content from GitHub repository."""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"ref": ref},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error = await response.json()
                    return {"error": error.get("message", "File not found")}

                data = await response.json()

                import base64
                content = base64.b64decode(data.get("content", "")).decode("utf-8")

                return {
                    "name": data["name"],
                    "path": data["path"],
                    "sha": data["sha"],
                    "size": data["size"],
                    "content": content,
                    "html_url": data.get("html_url")
                }

    except Exception as e:
        return {"error": str(e)}


async def github_list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30
) -> Dict[str, Any]:
    """List issues in a GitHub repository."""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"state": state, "per_page": per_page},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error = await response.json()
                    return {"error": error.get("message", "Failed to list issues")}

                issues = await response.json()
                return {
                    "issues": [
                        {
                            "number": issue["number"],
                            "title": issue["title"],
                            "state": issue["state"],
                            "html_url": issue["html_url"],
                            "user": issue["user"]["login"],
                            "labels": [l["name"] for l in issue.get("labels", [])],
                            "created_at": issue["created_at"],
                            "updated_at": issue["updated_at"],
                            "is_pr": "pull_request" in issue
                        }
                        for issue in issues
                    ]
                }

    except Exception as e:
        return {"error": str(e)}


async def github_create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str,
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Create an issue in a GitHub repository."""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}

    try:
        payload = {
            "title": title,
            "body": body
        }
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 201:
                    error = await response.json()
                    return {"error": error.get("message", "Failed to create issue")}

                issue = await response.json()
                return {
                    "number": issue["number"],
                    "title": issue["title"],
                    "html_url": issue["html_url"],
                    "state": issue["state"]
                }

    except Exception as e:
        return {"error": str(e)}


async def github_list_prs(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30
) -> Dict[str, Any]:
    """List pull requests in a GitHub repository."""
    if not GITHUB_TOKEN:
        return {"error": "GitHub token not configured"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers={
                    "Authorization": f"token {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"state": state, "per_page": per_page},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error = await response.json()
                    return {"error": error.get("message", "Failed to list PRs")}

                prs = await response.json()
                return {
                    "pull_requests": [
                        {
                            "number": pr["number"],
                            "title": pr["title"],
                            "state": pr["state"],
                            "html_url": pr["html_url"],
                            "user": pr["user"]["login"],
                            "head": pr["head"]["ref"],
                            "base": pr["base"]["ref"],
                            "created_at": pr["created_at"],
                            "updated_at": pr["updated_at"],
                            "mergeable": pr.get("mergeable"),
                            "draft": pr.get("draft", False)
                        }
                        for pr in prs
                    ]
                }

    except Exception as e:
        return {"error": str(e)}


# ============ INTEGRATION STATUS ============

def get_integration_status() -> Dict[str, Any]:
    """Get status of all integrations."""
    return {
        "google_drive": {
            "available": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
            "features": ["File storage", "Import/Export", "Sharing"]
        },
        "slack": {
            "available": bool(SLACK_BOT_TOKEN or SLACK_WEBHOOK_URL),
            "features": ["Channel notifications", "Direct messages", "Webhooks"]
        },
        "github": {
            "available": bool(GITHUB_TOKEN),
            "features": ["Repository access", "Issues", "Pull requests", "File content"]
        }
    }


def get_integration_config(integration_type: str) -> Optional[IntegrationConfig]:
    """Get configuration for a specific integration."""
    return _integrations.get(integration_type)


def set_integration_config(
    integration_type: str,
    enabled: bool = True,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None
) -> IntegrationConfig:
    """Set configuration for an integration."""
    config = IntegrationConfig(
        type=IntegrationType(integration_type),
        enabled=enabled,
        status=IntegrationStatus.CONNECTED if enabled else IntegrationStatus.DISCONNECTED,
        access_token=access_token,
        refresh_token=refresh_token,
        settings=settings or {}
    )
    _integrations[integration_type] = config
    return config
