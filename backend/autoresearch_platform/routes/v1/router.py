"""API router assembly."""

from fastapi import APIRouter

from autoresearch_platform.routes.v1.api import router as api_router

router = APIRouter()
router.include_router(api_router)

