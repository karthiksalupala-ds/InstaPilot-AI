from fastapi import APIRouter

from app.api.v1.agents import router as agents_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.automation import router as automation_router
from app.api.v1.crm import router as crm_router
from app.api.v1.events import router as events_router
from app.api.v1.health import router as health_router
from app.api.v1.inbox import router as inbox_router
from app.api.v1.instagram import router as instagram_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.workspaces import router as workspaces_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(instagram_router)
api_router.include_router(agents_router)
api_router.include_router(knowledge_router)
api_router.include_router(inbox_router)
api_router.include_router(crm_router)
api_router.include_router(automation_router)
api_router.include_router(analytics_router)
api_router.include_router(webhooks_router)
api_router.include_router(events_router)
