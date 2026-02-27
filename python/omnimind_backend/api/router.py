from fastapi import APIRouter

from omnimind_backend.api.v1.agent import router as agent_router
from omnimind_backend.api.v1.mind import router as mind_router
from omnimind_backend.api.v1.sessions import router as sessions_router

router = APIRouter(prefix="/v1")
router.include_router(agent_router)
router.include_router(sessions_router)
router.include_router(mind_router)
