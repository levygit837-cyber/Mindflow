from fastapi import APIRouter

from mindflow_backend.api.v1.agent import router as agent_router
from mindflow_backend.api.v1.autocomplete import router as autocomplete_router
from mindflow_backend.api.v1.chains import router as chains_router
from mindflow_backend.api.v1.chat import router as chat_router
from mindflow_backend.api.v1.config import router as config_router
from mindflow_backend.api.v1.feature_flags import router as feature_flags_router
from mindflow_backend.api.v1.health import router as health_router
from mindflow_backend.api.v1.metrics import router as metrics_router
from mindflow_backend.api.v1.mode_controller import router as modes_router
from mindflow_backend.api.v1.monitoring import router as monitoring_router
from mindflow_backend.api.v1.output_styles import router as output_styles_router
from mindflow_backend.api.v1.performance import router as performance_router
from mindflow_backend.api.v1.providers import router as providers_router
from mindflow_backend.api.v1.resilience import router as resilience_router
from mindflow_backend.api.v1.tasks import router as tasks_router
from mindflow_backend.memory.api.routes import router as memory_router
from mindflow_backend.api.v1.a2a import router as a2a_router
from mindflow_backend.api.v1.filesystem import router as filesystem_router

router = APIRouter(prefix="/v1")
router.include_router(agent_router)
router.include_router(chat_router)
router.include_router(providers_router)
router.include_router(metrics_router)
router.include_router(config_router)
router.include_router(performance_router)
router.include_router(resilience_router)
router.include_router(monitoring_router)
router.include_router(health_router)
router.include_router(chains_router)
router.include_router(tasks_router)
router.include_router(memory_router)
router.include_router(modes_router)
router.include_router(autocomplete_router)
router.include_router(feature_flags_router)
router.include_router(output_styles_router)

# A2A endpoints are usually in /v1/a2a logic or direct /a2a. Since we defined them in the router:
router.include_router(a2a_router)
router.include_router(filesystem_router)
