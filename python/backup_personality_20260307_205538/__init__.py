"""🚨 DEPRECATED - Personality System

This module is deprecated and will be removed in version 2.0.0.
Please use the new specialists system instead.

MIGRATION GUIDE:
    OLD: from mindflow_backend.agents.personality import get_personality_selector
    NEW: from mindflow_backend.agents.specialists import get_specialist_selector

For detailed migration instructions, see:
    docs/migration-personality-to-specialists.md

Questions? Contact: dev-team@omnimind.com
"""

from __future__ import annotations

import warnings
import sys
import inspect
from typing import Any

# Metadata depreciação
__deprecated_version__ = "1.5.0"
__removal_version__ = "2.0.0"
__replacement_module__ = "mindflow_backend.agents.specialists"
__migration_guide__ = "docs/migration-personality-to-specialists.md"


def _deprecation_warning(feature_name: str = "personality module", stack_level: int = 3) -> None:
    """Emit standardized deprecation warning."""
    warnings.warn(
        f"The '{feature_name}' is deprecated since v{__deprecated_version__} "
        f"and will be removed in v{__removal_version__}. "
        f"Replace with: from {__replacement_module__} import [...]. "
        f"See migration guide: {__migration_guide__}",
        DeprecationWarning,
        stacklevel=stack_level,
    )


def _log_usage(func_name: str) -> None:
    """Log usage of deprecated features for monitoring."""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        frame = inspect.currentframe().f_back
        caller_info = {
            "function": func_name,
            "caller_file": frame.f_code.co_filename if frame else "unknown",
            "caller_line": frame.f_lineno if frame else "unknown",
            "timestamp": "2024-01-01",  # Would use real timestamp
        }
        
        logger.warning("Deprecated personality usage detected", caller_info)
    except Exception:
        # Never let logging errors break the code
        pass


# Emit warning on import
_deprecation_warning("personality module", stack_level=2)

# Re-export do novo sistema com avisos
try:
    from ..specialists import (
        get_specialist_selector as get_personality_selector,
        get_specialist_config_builder as get_personality_config_builder,
        get_delegation_task_builder,
        get_specialist_rule_engine as get_personality_rule_engine,
        get_specialist_cache as get_personality_cache,
        get_dynamic_prompt_builder,
        DynamicPromptBuilder,
        SpecialistSelector as PersonalitySelector,
        SpecialistRuleEngine as PersonalityRuleEngine,
        SpecialistConfigurationBuilder as PersonalityConfigurationBuilder,
        SpecialistCache as PersonalityCache,
        SecuritySpecialist as SecurityGuardPersonality,
        ReviewSpecialist as CriticPersonality,
        CreativeSpecialist as CreativePersonality,
        ArchitectureSpecialist as ArchTechPersonality,
        BrainstormSpecialist as BrainstormPersonality,
        DeepAnalysisSpecialist as DeepIterationPersonality,
    )
    
    # Re-exportar schemas com aliases
    from ..schemas.orchestration.specialists import (
        SpecialistType as PersonalityType,
        SpecialistSelection as PersonalitySelection,
        SpecialistSwitchContext as PersonalitySwitchContext,
        SpecialistConfiguration as PersonalityConfiguration,
        SpecialistDecisionResult as PersonalityDecisionResult,
        SpecialistSelectionRule as PersonalitySelectionRule,
        SpecialistCacheEntry as PersonalityCacheEntry,
    )
    
    # Wrap functions with warnings
    def _wrap_with_warning(func: Any, old_name: str, new_name: str) -> Any:
        """Wrap function with deprecation warning."""
        def wrapper(*args, **kwargs):
            _log_usage(old_name)
            _deprecation_warning(old_name, stack_level=3)
            return func(*args, **kwargs)
        wrapper.__name__ = old_name
        wrapper.__doc__ = f"DEPRECATED: Use {new_name} instead"
        return wrapper
    
    # Aplicar wrappers às funções principais
    get_personality_selector = _wrap_with_warning(
        get_personality_selector, 
        "get_personality_selector", 
        "get_specialist_selector"
    )
    
    get_personality_config_builder = _wrap_with_warning(
        get_personality_config_builder,
        "get_personality_config_builder", 
        "get_specialist_config_builder"
    )
    
    get_personality_rule_engine = _wrap_with_warning(
        get_personality_rule_engine,
        "get_personality_rule_engine",
        "get_specialist_rule_engine"
    )
    
    # Exportar com aliases depreciados
    __all__ = [
        # Legacy names (deprecated)
        "get_personality_selector",
        "get_personality_config_builder", 
        "get_delegation_task_builder",
        "get_personality_rule_engine",
        "get_personality_cache",
        "get_dynamic_prompt_builder",
        "DynamicPromptBuilder",
        "PersonalitySelector",
        "PersonalityRuleEngine",
        "PersonalityConfigurationBuilder",
        "PersonalityCache",
        "SecurityGuardPersonality",
        "CriticPersonality",
        "CreativePersonality",
        "ArchTechPersonality",
        "BrainstormPersonality",
        "DeepIterationPersonality",
        "PersonalityType",
        "PersonalitySelection",
        "PersonalitySwitchContext",
        "PersonalityConfiguration",
        "PersonalityDecisionResult",
        "PersonalitySelectionRule",
        "PersonalityCacheEntry",
        # Metadata
        "__deprecated_version__",
        "__removal_version__",
        "__replacement_module__",
        "__migration_guide__",
    ]

except ImportError as e:
    raise ImportError(
        f"Failed to import replacement module '{__replacement_module__}'. "
        f"The personality system is deprecated. Please update your imports. "
        f"Error: {e}"
    ) from e


# Classe de ajuda para migração
class MigrationHelper:
    """Helper class to assist with migration from personality to specialists."""
    
    @staticmethod
    def check_usage() -> dict[str, Any]:
        """Check if deprecated personality features are being used."""
        frame = sys._getframe(1)
        caller_file = frame.f_code.co_filename
        
        return {
            "uses_old_imports": "personality" in caller_file,
            "uses_old_classes": any(
                name in frame.f_locals 
                for name in ["PersonalitySelector", "PersonalityType"]
            ),
            "caller_file": caller_file,
            "deprecated_version": __deprecated_version__,
            "removal_version": __removal_version__,
        }
    
    @staticmethod
    def suggest_replacements() -> dict[str, str]:
        """Get suggested replacements for deprecated features."""
        return {
            "PersonalitySelector": "SpecialistSelector",
            "PersonalityType": "SpecialistType", 
            "get_personality_selector": "get_specialist_selector",
            "SecurityGuardPersonality": "SecuritySpecialist",
            "CriticPersonality": "ReviewSpecialist",
            "ArchTechPersonality": "ArchitectureSpecialist",
            "BrainstormPersonality": "BrainstormSpecialist",
            "DeepIterationPersonality": "DeepAnalysisSpecialist",
            "from mindflow_backend.agents.personality": "from mindflow_backend.agents.specialists",
            "/select-personality": "/select-specialist",
            "PersonalitySelectionRequest": "SpecialistSelectionRequest",
            "PersonalitySelectionResponse": "SpecialistSelectionResponse",
        }


# Adicionar helper ao namespace
MigrationHelper = MigrationHelper
