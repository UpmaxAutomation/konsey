"""API routes for LLM Council."""

from .auth import router as auth_router
from .boards import router as boards_router
from .conversations import router as conversations_router
from .council import router as council_router
from .projects import router as projects_router
from .config import router as config_router
from .api_keys import router as api_keys_router
from .analytics import router as analytics_router
from .files import router as files_router
from .tools import router as tools_router
from .teams import router as teams_router
from .integrations import router as integrations_router
from .features import router as features_router
from .misc import router as misc_router
from .workflows import router as workflows_router
from .workflows import templates_router as workflow_templates_router
from .agents import router as agents_router

__all__ = [
    "auth_router",
    "boards_router",
    "conversations_router",
    "council_router",
    "projects_router",
    "config_router",
    "api_keys_router",
    "analytics_router",
    "files_router",
    "tools_router",
    "teams_router",
    "integrations_router",
    "features_router",
    "misc_router",
    "workflows_router",
    "workflow_templates_router",
    "agents_router",
]
