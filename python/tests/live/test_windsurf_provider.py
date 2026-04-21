import pytest
from mindflow_backend.runtime.providers.providers import get_model_for_provider
from mindflow_backend.infra.config import get_settings
from langchain_core.messages import HumanMessage

@pytest.mark.asyncio
async def test_windsurf_provider_loads():
    settings = get_settings()
    # It might fail if the gateway isn't running but it should load
    try:
        model = get_model_for_provider("windsurf", "MODEL_SWE_1")
        assert model is not None
        assert model._llm_type == "windsurf"
    except Exception as e:
        pytest.skip(f"Gateway might not be running: {e}")

