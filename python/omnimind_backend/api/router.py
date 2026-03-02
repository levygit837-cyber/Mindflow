from fastapi import APIRouter

from omnimind_backend.api.v1.agent import router as agent_router
from omnimind_backend.api.v1.chat import router as chat_router

router = APIRouter(prefix="/v1")
router.include_router(agent_router)
router.include_router(chat_router)
