from mindflow_backend.agents.tools.integration.integration_tools import (
    DockerTool,
    GitTool,
)
from mindflow_backend.agents.tools.specialist.common.integration import (
    DockerTool as SpecialistDockerTool,
)
from mindflow_backend.agents.tools.specialist.common.integration import (
    GitTool as SpecialistGitTool,
)
from mindflow_backend.agents.tools.specialist.common.integration.integration_tools import (
    DockerTool as SpecialistModuleDockerTool,
)
from mindflow_backend.agents.tools.specialist.common.integration.integration_tools import (
    GitTool as SpecialistModuleGitTool,
)


def test_specialist_integration_exports_reuse_canonical_classes() -> None:
    assert SpecialistGitTool is GitTool
    assert SpecialistDockerTool is DockerTool


def test_specialist_integration_module_reuses_canonical_classes() -> None:
    assert SpecialistModuleGitTool is GitTool
    assert SpecialistModuleDockerTool is DockerTool
