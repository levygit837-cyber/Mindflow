"""Tests for Transcript Classifier."""

import pytest
from mindflow_backend.permissions.classifier import (
    TranscriptClassifier,
    SafetyLevel,
    ClassificationResult,
    SAFE_TOOLS,
    MODERATE_TOOLS,
    DANGEROUS_TOOLS,
)


class TestTranscriptClassifier:
    """Test suite for TranscriptClassifier."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.classifier = TranscriptClassifier()
    
    @pytest.mark.asyncio
    async def test_classify_safe_tool_read_file(self):
        """Test classification of read_file tool."""
        result = await self.classifier.classify(
            tool_name="read_file",
            tool_input={"path": "src/main.py"},
        )
        assert result.safety_level == SafetyLevel.SAFE
        assert result.auto_approvable is True
        assert result.confidence == 1.0
    
    @pytest.mark.asyncio
    async def test_classify_safe_tool_search_files(self):
        """Test classification of search_files tool."""
        result = await self.classifier.classify(
            tool_name="search_files",
            tool_input={"query": "test"},
        )
        assert result.safety_level == SafetyLevel.SAFE
        assert result.auto_approvable is True
    
    @pytest.mark.asyncio
    async def test_classify_moderate_tool_write_to_file(self):
        """Test classification of write_to_file tool."""
        result = await self.classifier.classify(
            tool_name="write_to_file",
            tool_input={"path": "src/new_file.py", "content": "test"},
        )
        assert result.safety_level == SafetyLevel.MODERATE
        assert result.auto_approvable is False
    
    @pytest.mark.asyncio
    async def test_classify_dangerous_tool_execute_command(self):
        """Test classification of execute_command tool with safe pattern."""
        result = await self.classifier.classify(
            tool_name="execute_command",
            tool_input={"command": "ls -la"},
        )
        assert result.safety_level == SafetyLevel.SAFE  # ls is a safe pattern
        assert result.auto_approvable is True
    
    @pytest.mark.asyncio
    async def test_classify_dangerous_command_rm_rf(self):
        """Test classification of dangerous rm -rf command."""
        result = await self.classifier.classify(
            tool_name="execute_command",
            tool_input={"command": "rm -rf /"},
        )
        assert result.safety_level == SafetyLevel.DANGEROUS
        assert result.auto_approvable is False
        assert len(result.risk_factors) > 0
    
    @pytest.mark.asyncio
    async def test_classify_dangerous_file_gitconfig(self):
        """Test classification of dangerous file path."""
        result = await self.classifier.classify(
            tool_name="write_to_file",
            tool_input={"path": ".git/config"},
        )
        assert result.safety_level == SafetyLevel.DANGEROUS
        assert result.auto_approvable is False
    
    @pytest.mark.asyncio
    async def test_classify_dangerous_directory_ssh(self):
        """Test classification of dangerous directory."""
        result = await self.classifier.classify(
            tool_name="read_file",
            tool_input={"path": ".ssh/id_rsa"},
        )
        assert result.safety_level == SafetyLevel.DANGEROUS
        assert result.auto_approvable is False
    
    @pytest.mark.asyncio
    async def test_classify_safe_bash_pattern_git_status(self):
        """Test classification of safe git status command."""
        result = await self.classifier.classify(
            tool_name="execute_command",
            tool_input={"command": "git status"},
        )
        assert result.safety_level == SafetyLevel.SAFE
        assert result.auto_approvable is True
    
    @pytest.mark.asyncio
    async def test_classify_safe_bash_pattern_ls(self):
        """Test classification of safe ls command."""
        result = await self.classifier.classify(
            tool_name="execute_command",
            tool_input={"command": "ls -la"},
        )
        assert result.safety_level == SafetyLevel.SAFE
        assert result.auto_approvable is True
    
    @pytest.mark.asyncio
    async def test_classify_safe_bash_pattern_cat(self):
        """Test classification of safe cat command."""
        result = await self.classifier.classify(
            tool_name="execute_command",
            tool_input={"command": "cat file.txt"},
        )
        assert result.safety_level == SafetyLevel.SAFE
        assert result.auto_approvable is True
    
    @pytest.mark.asyncio
    async def test_classify_unknown_tool(self):
        """Test classification of unknown tool."""
        result = await self.classifier.classify(
            tool_name="unknown_tool",
            tool_input={},
        )
        assert result.safety_level == SafetyLevel.MODERATE
        assert result.auto_approvable is False
    
    @pytest.mark.asyncio
    async def test_classify_with_context(self):
        """Test classification with context."""
        result = await self.classifier.classify(
            tool_name="read_file",
            tool_input={"path": "src/main.py"},
            context={"session_id": "test-session"},
        )
        assert result.safety_level == SafetyLevel.SAFE
        assert result.auto_approvable is True
    
    def test_safe_tools_set(self):
        """Test SAFE_TOOLS constant."""
        assert "read_file" in SAFE_TOOLS
        assert "search_files" in SAFE_TOOLS
        assert "glob" in SAFE_TOOLS
        assert "list_files" in SAFE_TOOLS
    
    def test_moderate_tools_set(self):
        """Test MODERATE_TOOLS constant."""
        assert "write_to_file" in MODERATE_TOOLS
        assert "replace_in_file" in MODERATE_TOOLS
    
    def test_dangerous_tools_set(self):
        """Test DANGEROUS_TOOLS constant."""
        assert "execute_command" in DANGEROUS_TOOLS
        assert "bash" in DANGEROUS_TOOLS