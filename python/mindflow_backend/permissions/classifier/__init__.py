"""Auto Mode Transcript Classifier.

Classifies tool invocations to determine if they can be auto-approved.
Based on Claude Code's transcript classifier.

Classification levels:
- SAFE: Auto-approve (read-only, no side effects)
- MODERATE: May require approval based on context
- DANGEROUS: Always require approval (destructive operations)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from dataclasses import dataclass, field
import logging

_logger = logging.getLogger(__name__)


class SafetyLevel(StrEnum):
    """Safety classification for tool invocations."""
    SAFE = "safe"           # Auto-approve
    MODERATE = "moderate"   # Context-dependent
    DANGEROUS = "dangerous" # Always ask


@dataclass
class ClassificationResult:
    """Result of transcript classification."""
    safety_level: SafetyLevel
    confidence: float  # 0.0 to 1.0
    reasons: list[str] = field(default_factory=list)
    auto_approvable: bool = False
    risk_factors: list[str] = field(default_factory=list)


# Safe tools that can be auto-approved
SAFE_TOOLS: frozenset[str] = frozenset({
    "read_file",
    "search_files",
    "glob",
    "list_files",
    "codebase_search",
    "codebase_graph_query",
    "codebase_status",
    "codebase_context",
})

# Moderate tools that may require context-dependent approval
MODERATE_TOOLS: frozenset[str] = frozenset({
    "write_to_file",
    "replace_in_file",
})

# Dangerous tools that always require approval
DANGEROUS_TOOLS: frozenset[str] = frozenset({
    "execute_command",
    "bash",
})

# Safe bash patterns
SAFE_BASH_PATTERNS: list[str] = [
    r"^git\s+(status|log|diff|show|branch|remote)",
    r"^ls\s",
    r"^cat\s",
    r"^grep\s",
    r"^find\s.*-name",
    r"^pwd$",
    r"^echo\s",
    r"^head\s",
    r"^tail\s",
    r"^wc\s",
    r"^sort\s",
    r"^uniq\s",
    r"^awk\s",
    r"^sed\s.*p",  # Only print operations
]


class TranscriptClassifier:
    """Classifies tool invocations for auto-mode approval.
    
    Evaluation criteria:
    1. Tool type (read-only vs destructive)
    2. Target paths (safe vs dangerous)
    3. Command patterns (safe vs dangerous)
    4. Context (previous actions, user intent)
    """
    
    def __init__(self) -> None:
        import re
        self._safe_patterns = [re.compile(p) for p in SAFE_BASH_PATTERNS]
    
    async def classify(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ClassificationResult:
        """Classify a tool invocation for auto-approval.
        
        Returns classification with safety level and auto-approvability.
        """
        # 1. Check tool type
        tool_safety = self._classify_tool_type(tool_name)
        
        # 2. Check target paths
        path_safety = self._classify_paths(tool_name, tool_input)
        
        # 3. Check command patterns (for Bash)
        pattern_safety = self._classify_patterns(tool_name, tool_input)
        
        # 4. Combine classifications
        combined = self._combine_classifications(
            tool_safety, path_safety, pattern_safety
        )
        
        _logger.debug(
            "transcript_classified",
            tool_name=tool_name,
            tool_safety=tool_safety.value,
            path_safety=path_safety.value,
            pattern_safety=pattern_safety.value,
            final_level=combined.safety_level.value,
            auto_approvable=combined.auto_approvable,
        )
        
        return combined
    
    def _classify_tool_type(self, tool_name: str) -> SafetyLevel:
        """Classify based on tool type."""
        if tool_name in SAFE_TOOLS:
            return SafetyLevel.SAFE
        elif tool_name in MODERATE_TOOLS:
            return SafetyLevel.MODERATE
        elif tool_name in DANGEROUS_TOOLS:
            return SafetyLevel.DANGEROUS
        else:
            # Unknown tools are treated as moderate
            return SafetyLevel.MODERATE
    
    def _classify_paths(
        self, 
        tool_name: str, 
        tool_input: dict[str, Any]
    ) -> SafetyLevel:
        """Classify based on target file paths."""
        from mindflow_backend.permissions.policies.default import (
            DANGEROUS_FILES,
            DANGEROUS_DIRECTORIES,
        )
        
        # Extract path from tool input
        path = tool_input.get("path") or tool_input.get("file_path")
        if not path:
            return SafetyLevel.SAFE
        
        # Check against dangerous files
        import os
        filename = os.path.basename(path)
        if filename in DANGEROUS_FILES:
            _logger.debug(f"Dangerous file detected: {filename}")
            return SafetyLevel.DANGEROUS
        
        # Check against dangerous directories
        for dangerous_dir in DANGEROUS_DIRECTORIES:
            if dangerous_dir in path:
                _logger.debug(f"Dangerous directory detected: {dangerous_dir} in {path}")
                return SafetyLevel.DANGEROUS
        
        return SafetyLevel.SAFE
    
    def _classify_patterns(
        self, 
        tool_name: str, 
        tool_input: dict[str, Any]
    ) -> SafetyLevel:
        """Classify based on command patterns (Bash)."""
        if tool_name not in ("execute_command", "bash"):
            return SafetyLevel.SAFE
        
        command = tool_input.get("command", "")
        if not command:
            return SafetyLevel.SAFE
        
        # Check for safe patterns FIRST (before dangerous patterns)
        for pattern in self._safe_patterns:
            if pattern.match(command):
                return SafetyLevel.SAFE
        
        # Then check against dangerous patterns
        from mindflow_backend.permissions.policies.default import (
            DANGEROUS_BASH_PATTERNS,
        )
        
        import re
        for pattern in DANGEROUS_BASH_PATTERNS:
            if re.search(pattern, command):
                _logger.debug(f"Dangerous pattern detected: {pattern} in {command}")
                return SafetyLevel.DANGEROUS
        
        # Default to moderate for unknown patterns
        return SafetyLevel.MODERATE
    
    def _combine_classifications(
        self,
        tool_safety: SafetyLevel,
        path_safety: SafetyLevel,
        pattern_safety: SafetyLevel,
    ) -> ClassificationResult:
        """Combine multiple safety classifications.
        
        Special case: If tool is DANGEROUS but pattern is SAFE,
        the safe pattern overrides the tool classification.
        This allows safe bash commands like 'git status' to be auto-approved
        even though 'execute_command' is normally dangerous.
        """
        # Special override: safe pattern can reduce danger level
        if tool_safety == SafetyLevel.DANGEROUS and pattern_safety == SafetyLevel.SAFE:
            # Safe bash pattern overrides dangerous tool classification
            final_level = SafetyLevel.SAFE
            auto_approvable = True
            reasons = ["Command pattern verified as safe"]
            risk_factors = []
            confidence = 0.9  # High confidence when pattern is explicitly safe
        else:
            # Use worst-case (most restrictive) for other combinations
            levels = [tool_safety, path_safety, pattern_safety]
            
            if SafetyLevel.DANGEROUS in levels:
                final_level = SafetyLevel.DANGEROUS
            elif SafetyLevel.MODERATE in levels:
                final_level = SafetyLevel.MODERATE
            else:
                final_level = SafetyLevel.SAFE
            
            auto_approvable = final_level == SafetyLevel.SAFE
            
            # Build reasons
            reasons = []
            risk_factors = []
            
            if tool_safety != SafetyLevel.SAFE:
                reasons.append(f"Tool type: {tool_safety.value}")
            if path_safety != SafetyLevel.SAFE:
                reasons.append(f"Path safety: {path_safety.value}")
                risk_factors.append("Target path is potentially dangerous")
            if pattern_safety != SafetyLevel.SAFE:
                reasons.append(f"Pattern safety: {pattern_safety.value}")
                risk_factors.append("Command pattern is potentially dangerous")
            
            # Calculate confidence based on agreement between classifiers
            agreement_count = sum(1 for l in levels if l == final_level)
            confidence = agreement_count / len(levels)
        
        return ClassificationResult(
            safety_level=final_level,
            confidence=confidence,
            reasons=reasons,
            auto_approvable=auto_approvable,
            risk_factors=risk_factors,
        )
