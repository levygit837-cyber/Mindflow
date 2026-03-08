"""Dynamic prompt system for MindFlow agents.

Generates context-aware prompts that adapt based on the current task,
agent personality, and conversation history. This replaces the static
prompt system with a more flexible, dynamic approach.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from mindflow_backend.schemas.orchestration.personality import PersonalityType, TaskComplexity
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


@dataclass
class PromptContext:
    """Context for dynamic prompt generation."""
    
    task_description: str
    task_complexity: TaskComplexity
    personality: PersonalityType
    sub_personality: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = None
    user_preferences: Dict[str, Any] = None
    session_context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.user_preferences is None:
            self.user_preferences = {}
        if self.session_context is None:
            self.session_context = {}


class DynamicPromptBuilder:
    """Builds dynamic prompts based on context and requirements."""
    
    def __init__(self):
        self.base_preamble = self._get_base_preamble()
        self.personality_templates = self._load_personality_templates()
        self.context_enhancers = self._load_context_enhancers()
    
    def build_system_prompt(
        self,
        context: PromptContext,
        additional_instructions: str = "",
    ) -> str:
        """Build a complete system prompt for the given context."""
        try:
            _logger.debug(
                "dynamic_prompt_building_started",
                personality=context.personality,
                sub_personality=context.sub_personality,
                complexity=context.task_complexity,
            )
            
            # Start with base preamble
            prompt_parts = [self.base_preamble]
            
            # Add personality-specific content
            personality_content = self._build_personality_section(context)
            prompt_parts.append(personality_content)
            
            # Add task-specific instructions
            task_instructions = self._build_task_instructions(context)
            prompt_parts.append(task_instructions)
            
            # Add context from conversation history
            context_section = self._build_context_section(context)
            if context_section:
                prompt_parts.append(context_section)
            
            # Add user preferences
            preferences_section = self._build_preferences_section(context)
            if preferences_section:
                prompt_parts.append(preferences_section)
            
            # Add additional instructions
            if additional_instructions:
                prompt_parts.append(f"\\n\\n## Additional Instructions\\n{additional_instructions}")
            
            # Combine all parts
            full_prompt = "\\n\\n".join(prompt_parts)
            
            _logger.debug(
                "dynamic_prompt_built",
                prompt_length=len(full_prompt),
                sections_count=len(prompt_parts),
            )
            
            return full_prompt
        
        except Exception as e:
            _logger.error("dynamic_prompt_building_failed", error=str(e))
            return self._get_fallback_prompt(context)
    
    def _build_personality_section(self, context: PromptContext) -> str:
        """Build personality-specific prompt section."""
        personality = context.personality
        sub_personality = context.sub_personality
        
        # Get base personality template
        base_template = self.personality_templates.get(personality, "")
        
        # Enhance with sub-personality if present
        if sub_personality:
            from mindflow_backend.agents.personality.sub_personalities import get_sub_personality
            sub_personality_obj = get_sub_personality(sub_personality)
            if sub_personality_obj:
                base_template += f"\\n\\n### {sub_personality.title()} Focus\\n"
                base_template += f"You are operating as a {sub_personality.replace('_', ' ').title()} specialist. "
                base_template += f"Focus on: {', '.join(sub_personality_obj.config.specializations)}."
        
        return base_template
    
    def _build_task_instructions(self, context: PromptContext) -> str:
        """Build task-specific instructions."""
        instructions = ["## Task Instructions"]
        
        # Add complexity-specific guidance
        complexity_guidance = self._get_complexity_guidance(context.task_complexity)
        instructions.append(complexity_guidance)
        
        # Add task-specific context
        task_context = f"\\n**Current Task**: {context.task_description}"
        instructions.append(task_context)
        
        # Add thinking level guidance
        thinking_guidance = self._get_thinking_guidance(context)
        instructions.append(thinking_guidance)
        
        return "\\n".join(instructions)
    
    def _build_context_section(self, context: PromptContext) -> str:
        """Build context section from conversation history."""
        if not context.conversation_history:
            return ""
        
        context_parts = ["## Context"]
        
        # Add recent conversation context
        recent_messages = context.conversation_history[-3:]  # Last 3 messages
        for msg in recent_messages:
            role = msg.get("role", "unknown").title()
            content = msg.get("content", "")[:200]  # Truncate long messages
            if len(content) == 200:
                content += "..."
            context_parts.append(f"**{role}**: {content}")
        
        # Add session context if available
        if context.session_context:
            context_parts.append("\\n**Session Context**:")
            for key, value in context.session_context.items():
                context_parts.append(f"- {key}: {value}")
        
        return "\\n".join(context_parts)
    
    def _build_preferences_section(self, context: PromptContext) -> str:
        """Build user preferences section."""
        if not context.user_preferences:
            return ""
        
        preferences_parts = ["## User Preferences"]
        
        for key, value in context.user_preferences.items():
            preferences_parts.append(f"- **{key}**: {value}")
        
        return "\\n".join(preferences_parts)
    
    def _get_base_preamble(self) -> str:
        """Get the base preamble for all prompts."""
        return """You are MindFlow, an advanced AI assistant designed to help with a wide range of tasks.
        
You are intelligent, helpful, and capable of deep analysis and creative problem-solving.
You adapt your approach based on the task requirements and context provided."""
    
    def _load_personality_templates(self) -> Dict[PersonalityType, str]:
        """Load personality-specific prompt templates."""
        return {
            PersonalityType.CORE: """### Core Personality
You are a general-purpose assistant focused on clear, helpful communication.
You provide balanced analysis and practical solutions.""",
            
            PersonalityType.ANALYST: """### Analyst Personality
You are focused on deep analysis, research, and investigation.
You break down complex problems and provide thorough, well-reasoned insights.""",
            
            PersonalityType.CODER: """### Coder Personality
You are focused on code implementation, debugging, and technical solutions.
You write clean, efficient code and explain technical concepts clearly.""",
            
            PersonalityType.RESEARCHER: """### Researcher Personality
You are focused on information gathering, exploration, and discovery.
You investigate topics thoroughly and provide comprehensive, evidence-based responses.""",
        }
    
    def _load_context_enhancers(self) -> Dict[str, str]:
        """Load context enhancement patterns."""
        return {
            "security": "Pay special attention to security implications and best practices.",
            "performance": "Consider performance implications and optimization opportunities.",
            "architecture": "Think about system architecture and design patterns.",
            "debugging": "Focus on identifying root causes and systematic debugging.",
            "learning": "Provide educational explanations and learning resources.",
        }
    
    def _get_complexity_guidance(self, complexity: TaskComplexity) -> str:
        """Get guidance based on task complexity."""
        guidance = {
            TaskComplexity.SIMPLE: "Provide a direct, concise solution.",
            TaskComplexity.MEDIUM: "Provide a balanced approach with clear explanation.",
            TaskComplexity.COMPLEX: "Provide a thorough, step-by-step analysis with multiple considerations.",
        }
        return f"**Complexity Level**: {complexity.value}\\n{guidance.get(complexity, '')}"
    
    def _get_thinking_guidance(self, context: PromptContext) -> str:
        """Get thinking level guidance."""
        from mindflow_backend.agents.personality.sub_personalities import get_sub_personality
        
        thinking_level = "medium"
        max_iterations = 1
        
        if context.sub_personality:
            sub_personality = get_sub_personality(context.sub_personality)
            if sub_personality:
                thinking_level = sub_personality.config.thinking_level.value
                max_iterations = sub_personality.config.max_iterations
        
        return f"**Thinking Level**: {thinking_level}\\n**Max Iterations**: {max_iterations}"
    
    def _get_fallback_prompt(self, context: PromptContext) -> str:
        """Get fallback prompt if dynamic building fails."""
        return f"""{self.base_preamble}

Please help with the following task: {context.task_description}

Provide a clear, helpful response based on your {context.personality.value} capabilities."""
    
    def enhance_prompt_with_context(
        self,
        base_prompt: str,
        context_enhancers: List[str],
    ) -> str:
        """Enhance a base prompt with additional context."""
        enhanced_parts = [base_prompt]
        
        for enhancer in context_enhancers:
            if enhancer in self.context_enhancers:
                enhanced_parts.append(f"\\n\\n{self.context_enhancers[enhancer]}")
        
        return "".join(enhanced_parts)


# Global instance
_dynamic_prompt_builder: DynamicPromptBuilder | None = None


def get_dynamic_prompt_builder() -> DynamicPromptBuilder:
    """Get the global dynamic prompt builder instance."""
    global _dynamic_prompt_builder
    if _dynamic_prompt_builder is None:
        _dynamic_prompt_builder = DynamicPromptBuilder()
    return _dynamic_prompt_builder
