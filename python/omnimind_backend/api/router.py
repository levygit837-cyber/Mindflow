from fastapi import APIRouter

from omnimind_backend.api.v1.agent import router as agent_router

router = APIRouter(prefix="/v1")
router.include_router(agent_router)
