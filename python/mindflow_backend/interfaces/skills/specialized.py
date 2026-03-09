"""Specialized skill interfaces."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from mindflow_backend.interfaces.skills.base import SkillInterface
from mindflow_backend.schemas.skills.base import SkillInput, SkillOutput
from mindflow_backend.schemas.skills.core import (
    AnalysisSkillConfig,
    CodingSkillConfig,
    ResearchSkillConfig
)
from mindflow_backend.schemas.skills.specialized import (
    SecuritySkillConfig,
    ArchitectureSkillConfig,
    TestingSkillConfig,
    DocumentationSkillConfig
)


class CoreSkillInterface(SkillInterface):
    """Base interface for core skills."""
    
    @abstractmethod
    def get_core_type(self) -> str:
        """Get core skill type.
        
        Returns:
            str: Core skill type
        """
        pass
    
    @abstractmethod
    def is_fundamental(self) -> bool:
        """Check if skill is fundamental.
        
        Returns:
            bool: True if fundamental skill
        """
        pass


class AnalysisSkillInterface(CoreSkillInterface):
    """Interface for analysis skills."""
    
    @abstractmethod
    async def analyze_code(
        self, 
        code: str,
        language: str,
        options: Optional[Dict[str, Any]] = None
    ) -> SkillOutput:
        """Analyze code structure and properties.
        
        Args:
            code: Code to analyze
            language: Programming language
            options: Analysis options
            
        Returns:
            SkillOutput: Analysis results
        """
        pass
    
    @abstractmethod
    async def analyze_dependencies(
        self, 
        file_path: str,
        depth: int = 1
    ) -> SkillOutput:
        """Analyze code dependencies.
        
        Args:
            file_path: Path to file to analyze
            depth: Analysis depth
            
        Returns:
            SkillOutput: Dependency analysis results
        """
        pass
    
    @abstractmethod
    async def analyze_complexity(
        self, 
        code: str,
        metrics: List[str] = None
    ) -> SkillOutput:
        """Analyze code complexity.
        
        Args:
            code: Code to analyze
            metrics: Complexity metrics to calculate
            
        Returns:
            SkillOutput: Complexity analysis results
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> AnalysisSkillConfig:
        """Get analysis skill configuration.
        
        Returns:
            AnalysisSkillConfig: Current configuration
        """
        pass


class CodingSkillInterface(CoreSkillInterface):
    """Interface for coding skills."""
    
    @abstractmethod
    async def generate_code(
        self, 
        specification: str,
        language: str,
        context: Optional[Dict[str, Any]] = None
    ) -> SkillOutput:
        """Generate code from specification.
        
        Args:
            specification: Code specification
            language: Target programming language
            context: Optional context
            
        Returns:
            SkillOutput: Generated code
        """
        pass
    
    @abstractmethod
    async def modify_code(
        self, 
        original_code: str,
        modifications: List[str],
        language: str
    ) -> SkillOutput:
        """Modify existing code.
        
        Args:
            original_code: Original code
            modifications: List of modifications
            language: Programming language
            
        Returns:
            SkillOutput: Modified code
        """
        pass
    
    @abstractmethod
    async def refactor_code(
        self, 
        code: str,
        refactor_type: str,
        language: str
    ) -> SkillOutput:
        """Refactor code.
        
        Args:
            code: Code to refactor
            refactor_type: Type of refactoring
            language: Programming language
            
        Returns:
            SkillOutput: Refactored code
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> CodingSkillConfig:
        """Get coding skill configuration.
        
        Returns:
            CodingSkillConfig: Current configuration
        """
        pass


class ResearchSkillInterface(CoreSkillInterface):
    """Interface for research skills."""
    
    @abstractmethod
    async def research_topic(
        self, 
        topic: str,
        sources: List[str] = None,
        depth: str = "standard"
    ) -> SkillOutput:
        """Research a specific topic.
        
        Args:
            topic: Topic to research
            sources: Sources to search
            depth: Research depth
            
        Returns:
            SkillOutput: Research results
        """
        pass
    
    @abstractmethod
    async def find_documentation(
        self, 
        query: str,
        libraries: List[str] = None
    ) -> SkillOutput:
        """Find relevant documentation.
        
        Args:
            query: Search query
            libraries: Specific libraries to search
            
        Returns:
            SkillOutput: Documentation results
        """
        pass
    
    @abstractmethod
    async def synthesize_information(
        self, 
        sources: List[Dict[str, Any]],
        objective: str
    ) -> SkillOutput:
        """Synthesize information from multiple sources.
        
        Args:
            sources: List of information sources
            objective: Synthesis objective
            
        Returns:
            SkillOutput: Synthesized information
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> ResearchSkillConfig:
        """Get research skill configuration.
        
        Returns:
            ResearchSkillConfig: Current configuration
        """
        pass


class SecuritySkillInterface(SkillInterface):
    """Interface for security skills."""
    
    @abstractmethod
    async def scan_vulnerabilities(
        self, 
        code: str,
        language: str,
        scan_types: List[str] = None
    ) -> SkillOutput:
        """Scan for security vulnerabilities.
        
        Args:
            code: Code to scan
            language: Programming language
            scan_types: Types of scans to perform
            
        Returns:
            SkillOutput: Vulnerability scan results
        """
        pass
    
    @abstractmethod
    async def check_compliance(
        self, 
        code: str,
        standards: List[str] = None
    ) -> SkillOutput:
        """Check compliance with security standards.
        
        Args:
            code: Code to check
            standards: Security standards to check against
            
        Returns:
            SkillOutput: Compliance check results
        """
        pass
    
    @abstractmethod
    async def analyze_security_risks(
        self, 
        system_description: str
    ) -> SkillOutput:
        """Analyze security risks.
        
        Args:
            system_description: Description of system to analyze
            
        Returns:
            SkillOutput: Risk analysis results
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> SecuritySkillConfig:
        """Get security skill configuration.
        
        Returns:
            SecuritySkillConfig: Current configuration
        """
        pass


class ArchitectureSkillInterface(SkillInterface):
    """Interface for architecture skills."""
    
    @abstractmethod
    async def analyze_architecture(
        self, 
        codebase_path: str,
        scope: str = "full_system"
    ) -> SkillOutput:
        """Analyze system architecture.
        
        Args:
            codebase_path: Path to codebase
            scope: Analysis scope
            
        Returns:
            SkillOutput: Architecture analysis results
        """
        pass
    
    @abstractmethod
    async def design_architecture(
        self, 
        requirements: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> SkillOutput:
        """Design system architecture.
        
        Args:
            requirements: System requirements
            constraints: Design constraints
            
        Returns:
            SkillOutput: Architecture design
        """
        pass
    
    @abstractmethod
    async def evaluate_patterns(
        self, 
        code: str,
        patterns: List[str] = None
    ) -> SkillOutput:
        """Evaluate design patterns usage.
        
        Args:
            code: Code to evaluate
            patterns: Patterns to check for
            
        Returns:
            SkillOutput: Pattern evaluation results
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> ArchitectureSkillConfig:
        """Get architecture skill configuration.
        
        Returns:
            ArchitectureSkillConfig: Current configuration
        """
        pass


class TestingSkillInterface(SkillInterface):
    """Interface for testing skills."""
    
    @abstractmethod
    async def generate_tests(
        self, 
        code: str,
        test_types: List[str] = None,
        framework: str = "pytest"
    ) -> SkillOutput:
        """Generate tests for code.
        
        Args:
            code: Code to generate tests for
            test_types: Types of tests to generate
            framework: Testing framework
            
        Returns:
            SkillOutput: Generated tests
        """
        pass
    
    @abstractmethod
    async def analyze_coverage(
        self, 
        test_results: Dict[str, Any],
        code_path: str
    ) -> SkillOutput:
        """Analyze test coverage.
        
        Args:
            test_results: Test execution results
            code_path: Path to source code
            
        Returns:
            SkillOutput: Coverage analysis results
        """
        pass
    
    @abstractmethod
    async def optimize_tests(
        self, 
        tests: str,
        optimization_goal: str = "performance"
    ) -> SkillOutput:
        """Optimize existing tests.
        
        Args:
            tests: Test code to optimize
            optimization_goal: Optimization objective
            
        Returns:
            SkillOutput: Optimized tests
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> TestingSkillConfig:
        """Get testing skill configuration.
        
        Returns:
            TestingSkillConfig: Current configuration
        """
        pass


class DocumentationSkillInterface(SkillInterface):
    """Interface for documentation skills."""
    
    @abstractmethod
    async def generate_documentation(
        self, 
        code: str,
        doc_types: List[str] = None,
        format: str = "markdown"
    ) -> SkillOutput:
        """Generate documentation for code.
        
        Args:
            code: Code to document
            doc_types: Types of documentation to generate
            format: Output format
            
        Returns:
            SkillOutput: Generated documentation
        """
        pass
    
    @abstractmethod
    async def analyze_documentation(
        self, 
        documentation: str,
        quality_criteria: List[str] = None
    ) -> SkillOutput:
        """Analyze documentation quality.
        
        Args:
            documentation: Documentation to analyze
            quality_criteria: Quality criteria to check
            
        Returns:
            SkillOutput: Documentation analysis results
        """
        pass
    
    @abstractmethod
    async def update_documentation(
        self, 
        code_changes: Dict[str, Any],
        existing_docs: str
    ) -> SkillOutput:
        """Update documentation based on code changes.
        
        Args:
            code_changes: Description of code changes
            existing_docs: Existing documentation
            
        Returns:
            SkillOutput: Updated documentation
        """
        pass
    
    @abstractmethod
    def get_configuration(self) -> DocumentationSkillConfig:
        """Get documentation skill configuration.
        
        Returns:
            DocumentationSkillConfig: Current configuration
        """
        pass
