from fastapi import APIRouter

from mindflow_backend.api.v1.agent import router as agent_router
from mindflow_backend.api.v1.chat import router as chat_router
from mindflow_backend.api.v1.orchestration import router as orchestration_router
from mindflow_backend.api.v1.providers import router as providers_router
from mindflow_backend.api.v1.memory import router as memory_router
from mindflow_backend.api.v1.metrics import router as metrics_router
from mindflow_backend.api.v1.legacy import router as legacy_router

router = APIRouter(prefix="/v1")
router.include_router(agent_router)
router.include_router(chat_router)
router.include_router(orchestration_router)
router.include_router(providers_router)
router.include_router(memory_router)
router.include_router(metrics_router)
router.include_router(legacy_router)
