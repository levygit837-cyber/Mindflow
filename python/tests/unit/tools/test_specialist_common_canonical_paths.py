from mindflow_backend.agents.tools.ai.model_tools import (
    EmbeddingTool,
    LocalModelTool,
)
from mindflow_backend.agents.tools.data.data_tools import (
    CSVProcessorTool,
    DatabaseTool,
)
from mindflow_backend.agents.tools.specialist.common.ai import (
    EmbeddingTool as SpecialistEmbeddingTool,
)
from mindflow_backend.agents.tools.specialist.common.ai import (
    LocalModelTool as SpecialistLocalModelTool,
)
from mindflow_backend.agents.tools.specialist.common.data import (
    CSVProcessorTool as SpecialistCSVProcessorTool,
)
from mindflow_backend.agents.tools.specialist.common.data import (
    DatabaseTool as SpecialistDatabaseTool,
)


def test_specialist_common_ai_exports_reuse_canonical_classes() -> None:
    assert SpecialistLocalModelTool is LocalModelTool
    assert SpecialistEmbeddingTool is EmbeddingTool


def test_specialist_common_data_exports_reuse_canonical_classes() -> None:
    assert SpecialistDatabaseTool is DatabaseTool
    assert SpecialistCSVProcessorTool is CSVProcessorTool
