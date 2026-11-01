"""Routes package init."""

from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.hints import router as hints_router
from app.routes.mastery import router as mastery_router
from app.routes.problems import router as problems_router
from app.routes.submissions import router as submissions_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(problems_router)
api_router.include_router(submissions_router)
# AGENTS.md constraint #4: hints router is NOT included in contest-mode prefix.
# It is only registered here for the standard practice endpoint.
api_router.include_router(hints_router)
api_router.include_router(mastery_router)
