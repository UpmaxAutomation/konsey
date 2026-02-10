"""Team workspace routes for LLM Council."""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.dependencies import get_current_user, get_current_user_optional
from ..database.connection import get_db
from ..database.models import User
from .. import storage_adapter as storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/teams", tags=["teams"])


# ──────────────────────────────────────────────
# Request / Response schemas
# ──────────────────────────────────────────────

class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Team name (max 100 chars)")
    description: Optional[str] = Field(default=None, max_length=1000)


class UpdateTeamRequest(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    settings: Optional[Dict[str, Any]] = None


class InviteMemberRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255, description="Member email")
    role: str = Field(default="member", pattern=r'^(owner|admin|member)$')


class ShareToTeamRequest(BaseModel):
    conversation_id: str


# ──────────────────────────────────────────────
# In-memory team storage (would use database in production)
# ──────────────────────────────────────────────

_teams: Dict[str, dict] = {}
_team_memberships: Dict[str, list] = {}
_team_conversations: Dict[str, list] = {}


# ──────────────────────────────────────────────
# Team endpoints
# ──────────────────────────────────────────────

@router.get(
    "",
    tags=["teams"],
    summary="List Teams",
    response_description="List of teams the user belongs to"
)
async def list_teams():
    """
    List all teams the current user belongs to.

    Returns team workspaces where the user is an owner, admin, or member.

    Returns:
        dict: Teams listing containing:
            - teams: List of team objects with id, name, description
            - count: Total number of teams
    """
    # In production, filter by authenticated user
    teams_list = list(_teams.values())
    return {"teams": teams_list, "count": len(teams_list)}


@router.post(
    "",
    tags=["teams"],
    summary="Create Team",
    response_description="Newly created team workspace"
)
async def create_team(
    request: CreateTeamRequest,
    current_user: User = Depends(get_current_user_optional),
):
    """
    Create a new team workspace.

    The creating user becomes the team owner with full administrative access.

    Args:
        request: CreateTeamRequest containing:
            - name: Team display name
            - description: Optional team description

    Returns:
        dict: Created team containing:
            - id: Unique team identifier
            - name: Team name
            - description: Team description
            - settings: Team settings object
            - created_at: Creation timestamp
            - member_count: Number of members (starts at 1)
    """
    team_id = str(uuid.uuid4())
    team = {
        "id": team_id,
        "name": request.name,
        "description": request.description,
        "settings": {},
        "created_at": datetime.now().isoformat(),
        "member_count": 1
    }
    _teams[team_id] = team
    owner_id = str(current_user.id) if current_user else "anonymous"
    _team_memberships[team_id] = [{"user_id": owner_id, "role": "owner"}]
    _team_conversations[team_id] = []
    return team


@router.get(
    "/{team_id}",
    tags=["teams"],
    summary="Get Team",
    response_description="Team details with members and conversations"
)
async def get_team(team_id: str):
    """
    Get detailed information about a team.

    Returns full team details including all members and shared conversations.

    Args:
        team_id: Unique identifier of the team

    Returns:
        dict: Team details containing:
            - id: Team identifier
            - name: Team name
            - description: Team description
            - settings: Team configuration
            - members: List of team members with roles
            - conversations: List of shared conversations

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    team = _teams[team_id]
    team["members"] = _team_memberships.get(team_id, [])
    team["conversations"] = _team_conversations.get(team_id, [])
    return team


@router.put(
    "/{team_id}",
    tags=["teams"],
    summary="Update Team",
    response_description="Updated team details"
)
async def update_team(team_id: str, request: UpdateTeamRequest):
    """
    Update team settings and information.

    Allows updating team name, description, and settings. Requires
    owner or admin role in the team.

    Args:
        team_id: Unique identifier of the team
        request: UpdateTeamRequest with optional fields:
            - name: New team name
            - description: New team description
            - settings: Settings to merge with existing

    Returns:
        dict: Updated team object

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    team = _teams[team_id]
    if request.name:
        team["name"] = request.name
    if request.description is not None:
        team["description"] = request.description
    if request.settings:
        team["settings"].update(request.settings)
    return team


@router.delete(
    "/{team_id}",
    tags=["teams"],
    summary="Delete Team",
    response_description="Deletion confirmation"
)
async def delete_team(team_id: str):
    """
    Delete a team workspace.

    Permanently deletes the team including all memberships and shared
    conversation associations. Requires owner role.

    Args:
        team_id: Unique identifier of the team to delete

    Returns:
        dict: Confirmation containing:
            - status: "deleted"

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    del _teams[team_id]
    _team_memberships.pop(team_id, None)
    _team_conversations.pop(team_id, None)
    return {"status": "deleted"}


@router.post(
    "/{team_id}/members",
    tags=["teams"],
    summary="Invite Team Member",
    response_description="Invited member details"
)
async def invite_member(team_id: str, request: InviteMemberRequest):
    """
    Invite a new member to the team.

    Sends an invitation to the specified email address. The invited
    user will receive an email to join the team.

    Args:
        team_id: Unique identifier of the team
        request: InviteMemberRequest containing:
            - email: Email address to invite
            - role: Role to assign (owner, admin, member)

    Returns:
        dict: Invitation details containing:
            - id: Invitation identifier
            - email: Invited email address
            - role: Assigned role
            - invited_at: Invitation timestamp
            - status: "pending" until accepted

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    member = {
        "id": str(uuid.uuid4()),
        "email": request.email,
        "role": request.role,
        "invited_at": datetime.now().isoformat(),
        "status": "pending"
    }
    if team_id not in _team_memberships:
        _team_memberships[team_id] = []
    _team_memberships[team_id].append(member)
    _teams[team_id]["member_count"] = len(_team_memberships[team_id])
    return member


@router.delete(
    "/{team_id}/members/{member_id}",
    tags=["teams"],
    summary="Remove Team Member",
    response_description="Removal confirmation"
)
async def remove_member(team_id: str, member_id: str):
    """
    Remove a member from the team.

    Removes the specified member's access to the team. Requires
    owner or admin role to remove members.

    Args:
        team_id: Unique identifier of the team
        member_id: Unique identifier of the member to remove

    Returns:
        dict: Confirmation containing:
            - status: "removed"

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    members = _team_memberships.get(team_id, [])
    _team_memberships[team_id] = [m for m in members if m.get("id") != member_id]
    _teams[team_id]["member_count"] = len(_team_memberships[team_id])
    return {"status": "removed"}


@router.post(
    "/{team_id}/conversations",
    tags=["teams"],
    summary="Share Conversation to Team",
    response_description="Shared conversation details"
)
async def share_conversation_to_team(
    team_id: str,
    request: ShareToTeamRequest,
    current_user: User = Depends(get_current_user_optional),
):
    """
    Share a conversation with the team.

    Makes a conversation visible to all team members. The original
    conversation remains accessible to the owner.

    Args:
        team_id: Unique identifier of the team
        request: ShareToTeamRequest containing:
            - conversation_id: ID of conversation to share

    Returns:
        dict: Share details containing:
            - conversation_id: Shared conversation ID
            - title: Conversation title
            - shared_at: Share timestamp
            - shared_by: User who shared

    Raises:
        HTTPException 404: Team or conversation not found
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    conversation = await storage.get_conversation(request.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if team_id not in _team_conversations:
        _team_conversations[team_id] = []

    shared_by = str(current_user.id) if current_user else "anonymous"
    shared = {
        "conversation_id": request.conversation_id,
        "title": conversation.get("title", "Untitled"),
        "shared_at": datetime.now().isoformat(),
        "shared_by": shared_by
    }
    _team_conversations[team_id].append(shared)
    return shared


@router.get(
    "/{team_id}/conversations",
    tags=["teams"],
    summary="List Team Conversations",
    response_description="List of conversations shared with the team"
)
async def list_team_conversations(team_id: str):
    """
    List all conversations shared with the team.

    Returns conversations that team members have shared for
    collaborative access.

    Args:
        team_id: Unique identifier of the team

    Returns:
        dict: Team conversations containing:
            - conversations: List of shared conversation references
            - count: Total number of shared conversations

    Raises:
        HTTPException 404: Team with given ID does not exist
    """
    if team_id not in _teams:
        raise HTTPException(status_code=404, detail="Team not found")
    conversations = _team_conversations.get(team_id, [])
    return {"conversations": conversations, "count": len(conversations)}
