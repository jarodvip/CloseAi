"""统一注册所有 API 路由端点。"""

from fastapi import APIRouter
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.customers import router as customers_router
from app.api.v1.routes.briefing import router as briefing_router
from app.api.v1.routes.interactions import router as interactions_router
from app.api.v1.routes.knowledge import router as knowledge_router
from app.api.v1.routes.chat import router as chat_router
from app.api.v1.routes.analyze import router as analyze_router
from app.api.v1.routes.dashboard import router as dashboard_router
from app.api.v1.routes.research import router as research_router
from app.api.v1.routes.research import customer_router as research_customer_router


main_router = APIRouter()

# 注册所有子路由
main_router.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
main_router.include_router(customers_router, prefix="/api/v1/customers", tags=["customers"])
main_router.include_router(briefing_router, prefix="/api/v1/customers", tags=["briefing"])
main_router.include_router(interactions_router, prefix="/api/v1/customers", tags=["interactions"])
main_router.include_router(knowledge_router, prefix="/api/v1/knowledge", tags=["knowledge"])
main_router.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
main_router.include_router(analyze_router, prefix="/api/v1", tags=["analyze"])
main_router.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["dashboard"])
main_router.include_router(research_router, prefix="/api/v1/research", tags=["research"])
main_router.include_router(research_customer_router, prefix="/api/v1/customers", tags=["research"])
