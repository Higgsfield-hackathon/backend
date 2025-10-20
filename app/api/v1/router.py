from fastapi import APIRouter
from .health import router as health_router
from .generate import router as generate_router
from .jobs import router as jobs_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(generate_router, tags=["generate"])
router.include_router(jobs_router, tags=["jobs"])
