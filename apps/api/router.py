from fastapi import APIRouter
from apps.api.endpoints import ai

api_router = APIRouter()

api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["ai"]
)
