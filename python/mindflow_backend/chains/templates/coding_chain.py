"""Coding Chain Template - Pre-configured chain for coding tasks.

This template provides a standardized coding workflow with steps for:
1. Requirements analysis and specification
2. Architecture and design planning
3. Code implementation and development
4. Code review and validation
5. Testing and quality assurance
6. Documentation generation
"""

from __future__ import annotations

from typing import Any

from mindflow_backend.chains.base.chain import BaseChain
from mindflow_backend.chains.base.step import StepType
from mindflow_backend.chains.builders.sequential_builder import SequentialChainBuilder


class CodingChain:
    """Pre-configured chain for coding tasks."""
    
    def __init__(
        self,
        chain_id: str = "coding_chain",
        programming_language: str = "python",
        code_style: str = "clean_code",  # clean_code, functional, oop, functional_programming
        include_tests: bool = True,
        include_documentation: bool = True,
        enable_linting: bool = True
    ) -> None:
        self.chain_id = chain_id
        self.programming_language = programming_language
        self.code_style = code_style
        self.include_tests = include_tests
        self.include_documentation = include_documentation
        self.enable_linting = enable_linting
        
        # Initialize the chain builder
        self.builder = SequentialChainBuilder(chain_id)
        self._setup_coding_steps()
    
    def _setup_coding_steps(self) -> None:
        """Setup the standard coding workflow steps."""
        
        # Step 1: Requirements Analysis
        self.builder.add_step(
            step_id="analyze_requirements",
            step_function=self._analyze_coding_requirements,
            step_type=StepType.PROCESSING,
            description="Analyze coding requirements and specifications"
        )
        
        # Step 2: Architecture Design
        self.builder.add_step(
            step_id="design_architecture",
            step_function=self._design_solution_architecture,
            step_type=StepType.PROCESSING,
            description="Design solution architecture and structure"
        )
        
        # Step 3: Code Implementation
        self.builder.add_step(
            step_id="implement_code",
            step_function=self._implement_solution_code,
            step_type=StepType.PROCESSING,
            description=f"Implement solution in {self.programming_language}"
        )
        
        # Step 4: Code Review
        self.builder.add_step(
            step_id="review_code",
            step_function=self._review_and_validate_code,
            step_type=StepType.VALIDATION,
            description="Review code for quality and best practices"
        )
        
        # Step 5: Testing (optional)
        if self.include_tests:
            self.builder.add_step(
                step_id="generate_tests",
                step_function=self._generate_unit_tests,
                step_type=StepType.PROCESSING,
                description="Generate unit tests for the implementation"
            )
        
        # Step 6: Linting (optional)
        if self.enable_linting:
            self.builder.add_step(
                step_id="lint_code",
                step_function=self._lint_and_format_code,
                step_type=StepType.VALIDATION,
                description="Lint and format code according to standards"
            )
        
        # Step 7: Documentation (optional)
        if self.include_documentation:
            self.builder.add_step(
                step_id="generate_documentation",
                step_function=self._generate_code_documentation,
                step_type=StepType.PROCESSING,
                description="Generate comprehensive documentation"
            )
    
    async def _analyze_coding_requirements(self, context: dict[str, Any]) -> dict[str, Any]:
        """Analyze coding requirements and specifications."""
        requirements = context.get("input", {}).get("requirements", "")
        
        # Parse requirements
        parsed_requirements = self._parse_requirements(requirements)
        
        # Identify functional requirements
        functional_reqs = self._extract_functional_requirements(parsed_requirements)
        
        # Identify non-functional requirements
        non_functional_reqs = self._extract_non_functional_requirements(parsed_requirements)
        
        # Determine complexity and scope
        complexity = self._assess_coding_complexity(parsed_requirements)
        scope = self._determine_project_scope(parsed_requirements)
        
        return {
            "output": {
                "original_requirements": requirements,
                "parsed_requirements": parsed_requirements,
                "functional_requirements": functional_reqs,
                "non_functional_requirements": non_functional_reqs,
                "technical_specifications": {
                    "programming_language": self.programming_language,
                    "complexity": complexity,
                    "scope": scope,
                    "estimated_components": self._estimate_components(parsed_requirements),
                    "dependencies": self._identify_dependencies(parsed_requirements)
                }
            }
        }
    
    async def _design_solution_architecture(self, context: dict[str, Any]) -> dict[str, Any]:
        """Design solution architecture and structure."""
        requirements = context.get("input", {})
        
        # Design system architecture
        architecture = self._design_system_architecture(requirements)
        
        # Design component structure
        components = self._design_component_structure(requirements)
        
        # Design data flow
        data_flow = self._design_data_flow(requirements)
        
        # Design API/interface
        interfaces = self._design_interfaces(requirements)
        
        return {
            "output": {
                "architecture_design": architecture,
                "component_structure": components,
                "data_flow": data_flow,
                "interfaces": interfaces,
                "design_patterns": self._select_design_patterns(requirements),
                "technology_stack": self._define_technology_stack(requirements)
            }
        }
    
    async def _implement_solution_code(self, context: dict[str, Any]) -> dict[str, Any]:
        """Implement the solution code."""
        design = context.get("input", {})
        
        # Generate code structure
        code_structure = self._generate_code_structure(design)
        
        # Implement core logic
        core_implementation = self._implement_core_logic(design)
        
        # Implement utilities/helpers
        utilities = self._implement_utilities(design)
        
        # Combine all code
        complete_code = self._assemble_complete_code(
            code_structure, core_implementation, utilities
        )
        
        return {
            "output": {
                "implementation": complete_code,
                "code_structure": code_structure,
                "files_created": self._list_created_files(complete_code),
                "implementation_notes": self._generate_implementation_notes(design)
            }
        }
    
    async def _review_and_validate_code(self, context: dict[str, Any]) -> dict[str, Any]:
        """Review code for quality and best practices."""
        implementation = context.get("input", {})
        
        # Code quality analysis
        quality_analysis = self._analyze_code_quality(implementation)
        
        # Best practices review
        practices_review = self._review_best_practices(implementation)
        
        # Security review
        security_review = self._review_security_practices(implementation)
        
        # Performance considerations
        performance_review = self._review_performance_considerations(implementation)
        
        return {
            "output": {
                "quality_analysis": quality_analysis,
                "practices_review": practices_review,
                "security_review": security_review,
                "performance_review": performance_review,
                "overall_score": self._calculate_overall_quality_score([
                    quality_analysis, practices_review, security_review, performance_review
                ]),
                "recommendations": self._generate_improvement_recommendations([
                    quality_analysis, practices_review, security_review, performance_review
                ])
            }
        }
    
    async def _generate_unit_tests(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate unit tests for the implementation."""
        implementation = context.get("input", {})
        
        # Identify testable components
        testable_components = self._identify_testable_components(implementation)
        
        # Generate test cases
        test_cases = []
        for component in testable_components:
            cases = self._generate_test_cases_for_component(component)
            test_cases.extend(cases)
        
        # Generate test code
        test_code = self._generate_test_code(test_cases, implementation)
        
        # Generate test documentation
        test_documentation = self._generate_test_documentation(test_cases)
        
        return {
            "output": {
                "test_cases": test_cases,
                "test_code": test_code,
                "test_documentation": test_documentation,
                "test_coverage": self._calculate_test_coverage(test_cases, implementation),
                "testing_framework": self._select_testing_framework()
            }
        }
    
    async def _lint_and_format_code(self, context: dict[str, Any]) -> dict[str, Any]:
        """Lint and format code according to standards."""
        implementation = context.get("input", {})
        
        # Run linting analysis
        linting_results = self._run_linting_analysis(implementation)
        
        # Format code
        formatted_code = self._format_code(implementation)
        
        # Check style compliance
        style_compliance = self._check_style_compliance(formatted_code)
        
        return {
            "output": {
                "linting_results": linting_results,
                "formatted_code": formatted_code,
                "style_compliance": style_compliance,
                "formatting_changes": self._identify_formatting_changes(
                    implementation.get("implementation", ""), formatted_code
                )
            }
        }
    
    async def _generate_code_documentation(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate comprehensive documentation."""
        implementation = context.get("input", {})
        
        # Generate API documentation
        api_docs = self._generate_api_documentation(implementation)
        
        # Generate code documentation
        code_docs = self._generate_code_comments(implementation)
        
        # Generate user documentation
        user_docs = self._generate_user_documentation(implementation)
        
        # Generate developer documentation
        developer_docs = self._generate_developer_documentation(implementation)
        
        return {
            "output": {
                "api_documentation": api_docs,
                "code_documentation": code_docs,
                "user_documentation": user_docs,
                "developer_documentation": developer_docs,
                "documentation_structure": self._define_documentation_structure()
            }
        }
    
    def build(self) -> BaseChain:
        """Build the coding chain.
        
        Returns:
            Configured SequentialChain instance
        """
        return self.builder.build()
    
    # Helper methods (simplified implementations for demonstration)
    
    def _parse_requirements(self, requirements: str) -> dict[str, Any]:
        """Parse and structure requirements."""
        return {
            "raw_text": requirements,
            "features": self._extract_features(requirements),
            "constraints": self._extract_constraints(requirements),
            "assumptions": self._extract_assumptions(requirements)
        }
    
    def _extract_features(self, requirements: str) -> list[str]:
        """Extract feature requirements from text."""
        # Simple pattern matching (would use NLP in production)
        feature_patterns = ["should", "must", "will", "shall", "needs to"]
        features = []
        
        sentences = requirements.split('.')
        for sentence in sentences:
            if any(pattern in sentence.lower() for pattern in feature_patterns):
                features.append(sentence.strip())
        
        return features
    
    def _extract_constraints(self, requirements: str) -> list[str]:
        """Extract constraints from requirements."""
        constraint_patterns = ["limit", "restrict", "must not", "cannot", "within"]
        constraints = []
        
        sentences = requirements.split('.')
        for sentence in sentences:
            if any(pattern in sentence.lower() for pattern in constraint_patterns):
                constraints.append(sentence.strip())
        
        return constraints
    
    def _extract_assumptions(self, requirements: str) -> list[str]:
        """Extract assumptions from requirements."""
        assumption_patterns = ["assume", "assuming", "given that"]
        assumptions = []
        
        sentences = requirements.split('.')
        for sentence in sentences:
            if any(pattern in sentence.lower() for pattern in assumption_patterns):
                assumptions.append(sentence.strip())
        
        return assumptions
    
    def _extract_functional_requirements(self, parsed_reqs: dict[str, Any]) -> list[str]:
        """Extract functional requirements."""
        return parsed_reqs.get("features", [])
    
    def _extract_non_functional_requirements(self, parsed_reqs: dict[str, Any]) -> dict[str, list[str]]:
        """Extract non-functional requirements."""
        return {
            "performance": self._extract_performance_requirements(parsed_reqs),
            "security": self._extract_security_requirements(parsed_reqs),
            "usability": self._extract_usability_requirements(parsed_reqs),
            "scalability": self._extract_scalability_requirements(parsed_reqs)
        }
    
    def _assess_coding_complexity(self, parsed_reqs: dict[str, Any]) -> str:
        """Assess the complexity of coding requirements."""
        feature_count = len(parsed_reqs.get("features", []))
        constraint_count = len(parsed_reqs.get("constraints", []))
        
        if feature_count > 10 or constraint_count > 5:
            return "high"
        elif feature_count > 5 or constraint_count > 2:
            return "medium"
        else:
            return "low"
    
    def _determine_project_scope(self, parsed_reqs: dict[str, Any]) -> str:
        """Determine the scope of the project."""
        feature_count = len(parsed_reqs.get("features", []))
        
        if feature_count > 15:
            return "enterprise"
        elif feature_count > 8:
            return "application"
        elif feature_count > 3:
            return "component"
        else:
            return "utility"
    
    def _estimate_components(self, parsed_reqs: dict[str, Any]) -> list[str]:
        """Estimate required components."""
        features = parsed_reqs.get("features", [])
        
        # Simple component estimation based on features
        components = ["main.py"]
        if any("api" in f.lower() for f in features):
            components.append("api.py")
        if any("database" in f.lower() or "data" in f.lower() for f in features):
            components.append("database.py")
        if any("ui" in f.lower() or "interface" in f.lower() for f in features):
            components.append("ui.py")
        
        return components
    
    def _identify_dependencies(self, parsed_reqs: dict[str, Any]) -> list[str]:
        """Identify potential dependencies."""
        features = parsed_reqs.get("features", [])
        dependencies = []
        
        # Simple dependency identification
        if any("web" in f.lower() for f in features):
            dependencies.extend(["flask", "fastapi", "django"])
        if any("database" in f.lower() for f in features):
            dependencies.extend(["sqlalchemy", "psycopg2", "mongodb"])
        if any("test" in f.lower() for f in features):
            dependencies.extend(["pytest", "unittest"])
        
        return list(set(dependencies))
    
    def _design_system_architecture(self, requirements: dict[str, Any]) -> dict[str, Any]:
        """Design the overall system architecture."""
        return {
            "pattern": "layered_architecture",
            "layers": ["presentation", "business", "data"],
            "components": requirements.get("technical_specifications", {}).get("estimated_components", []),
            "communication": "rest_api" if self.programming_language == "python" else "rpc"
        }
    
    def _design_component_structure(self, requirements: dict[str, Any]) -> dict[str, Any]:
        """Design the component structure."""
        return {
            "main_module": "main.py",
            "utility_modules": ["utils.py", "helpers.py"],
            "business_logic": ["services.py", "models.py"],
            "data_layer": ["database.py", "repositories.py"],
            "api_layer": ["endpoints.py", "schemas.py"]
        }
    
    def _design_data_flow(self, requirements: dict[str, Any]) -> dict[str, Any]:
        """Design the data flow architecture."""
        return {
            "flow_pattern": "request_response",
            "data_transformations": ["validation", "processing", "formatting"],
            "storage_points": ["database", "cache", "logs"]
        }
    
    def _design_interfaces(self, requirements: dict[str, Any]) -> dict[str, Any]:
        """Design APIs and interfaces."""
        return {
            "rest_endpoints": ["/api/v1/resource"],
            "data_schemas": ["ResourceSchema", "ResponseSchema"],
            "authentication": "jwt_based",
            "error_handling": "standardized_errors"
        }
    
    def _select_design_patterns(self, requirements: dict[str, Any]) -> list[str]:
        """Select appropriate design patterns."""
        patterns = ["singleton", "factory", "observer"]
        
        if requirements.get("technical_specifications", {}).get("scope") == "enterprise":
            patterns.extend(["repository", "unit_of_work", "dependency_injection"])
        
        return patterns
    
    def _define_technology_stack(self, requirements: dict[str, Any]) -> dict[str, str]:
        """Define the technology stack."""
        return {
            "language": self.programming_language,
            "framework": "flask" if self.programming_language == "python" else "express",
            "database": "postgresql",
            "testing": "pytest",
            "documentation": "sphinx"
        }
    
    def _generate_code_structure(self, design: dict[str, Any]) -> dict[str, str]:
        """Generate the basic code structure."""
        structure = {}
        
        for component in design.get("component_structure", {}).values():
            if isinstance(component, list):
                for comp in component:
                    structure[comp] = f"# {comp} implementation\\n\\n"
            else:
                structure[component] = f"# {component} implementation\\n\\n"
        
        return structure
    
    def _implement_core_logic(self, design: dict[str, Any]) -> dict[str, str]:
        """Implement the core business logic."""
        return {
            "main.py": '''
def main():
    """Main application entry point."""
    print("Hello, World!")

if __name__ == "__main__":
    main()
''',
            "services.py": '''
class Service:
    """Base service class."""
    
    def __init__(self):
        pass
    
    def process(self, data):
        """Process data."""
        return data
'''
        }
    
    def _implement_utilities(self, design: dict[str, Any]) -> dict[str, str]:
        """Implement utility functions."""
        return {
            "utils.py": '''
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def validate_data(data: Dict[str, Any]) -> bool:
    """Validate input data."""
    return isinstance(data, dict)

def format_response(data: Any) -> Dict[str, Any]:
    """Format response data."""
    return {"status": "success", "data": data}
''',
            "helpers.py": '''
from datetime import datetime
from typing import Any

def get_timestamp() -> str:
    """Get current timestamp."""
    return datetime.now().isoformat()

def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary."""
    return data.get(key, default)
'''
        }
    
    def _assemble_complete_code(self, structure: dict, core: dict, utilities: dict) -> dict[str, str]:
        """Assemble complete code from all parts."""
        complete_code = {}
        complete_code.update(structure)
        complete_code.update(core)
        complete_code.update(utilities)
        return complete_code
    
    def _list_created_files(self, code: dict[str, str]) -> list[str]:
        """List all created files."""
        return list(code.keys())
    
    def _generate_implementation_notes(self, design: dict[str, Any]) -> list[str]:
        """Generate implementation notes."""
        return [
            f"Implemented using {design.get('technology_stack', {}).get('language', 'python')}",
            f"Architecture pattern: {design.get('system_architecture', {}).get('pattern', 'unknown')}",
            "Code follows clean code principles",
            "Error handling implemented where appropriate"
        ]
    
    def _analyze_code_quality(self, implementation: dict[str, Any]) -> dict[str, Any]:
        """Analyze code quality metrics."""
        code = implementation.get("implementation", {})
        
        # Simple quality metrics
        total_lines = sum(code.count('\\n') for code in code.values())
        function_count = sum(code.count('def ') for code in code.values())
        class_count = sum(code.count('class ') for code in code.values())
        
        return {
            "total_lines": total_lines,
            "function_count": function_count,
            "class_count": class_count,
            "complexity_score": "medium",
            "maintainability_index": 0.8
        }
    
    def _review_best_practices(self, implementation: dict[str, Any]) -> dict[str, Any]:
        """Review code against best practices."""
        return {
            "naming_conventions": "compliant",
            "error_handling": "adequate",
            "code_organization": "good",
            "documentation": "present",
            "testing": "included" if self.include_tests else "not_included"
        }
    
    def _review_security_practices(self, implementation: dict[str, Any]) -> dict[str, Any]:
        """Review security practices."""
        return {
            "input_validation": "implemented",
            "sql_injection_protection": "adequate",
            "authentication": "configured",
            "data_encryption": "recommended"
        }
    
    def _review_performance_considerations(self, implementation: dict[str, Any]) -> dict[str, Any]:
        """Review performance considerations."""
        return {
            "algorithmic_complexity": "acceptable",
            "memory_usage": "optimized",
            "database_queries": "efficient",
            "caching": "recommended"
        }
    
    def _calculate_overall_quality_score(self, reviews: list[dict]) -> float:
        """Calculate overall quality score from reviews."""
        # Simple scoring algorithm
        scores = []
        for review in reviews:
            # Convert qualitative scores to numbers
            score = 0.8  # Default good score
            scores.append(score)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _generate_improvement_recommendations(self, reviews: list[dict]) -> list[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        for review in reviews:
            if "security" in review:
                recommendations.extend(review["security"].get("recommendations", []))
            if "performance" in review:
                recommendations.extend(review["performance"].get("recommendations", []))
        
        return list(set(recommendations))
    
    def _identify_testable_components(self, implementation: dict[str, Any]) -> list[str]:
        """Identify components that should be tested."""
        files = implementation.get("files_created", [])
        testable = []
        
        for file in files:
            if file.endswith(".py") and not file.startswith("test_"):
                testable.append(file)
        
        return testable
    
    def _generate_test_cases_for_component(self, component: str) -> list[dict[str, Any]]:
        """Generate test cases for a specific component."""
        return [
            {
                "name": f"test_{component}_basic",
                "description": f"Basic functionality test for {component}",
                "type": "unit",
                "assertions": ["assert result is not None", "assert type matches expected"]
            },
            {
                "name": f"test_{component}_edge_cases",
                "description": f"Edge case tests for {component}",
                "type": "unit",
                "assertions": ["test with empty input", "test with invalid input"]
            }
        ]
    
    def _generate_test_code(self, test_cases: list[dict], implementation: dict) -> str:
        """Generate test code from test cases."""
        test_code = '''
import pytest
from unittest.mock import patch, MagicMock

class TestImplementation:
    """Test suite for the implementation."""
'''
        
        for case in test_cases:
            test_code += f'''
    def {case["name"]}(self):
        """{case["description"]}"""
        # TODO: Implement test logic
        pass
'''
        
        return test_code
    
    def _generate_test_documentation(self, test_cases: list[dict]) -> str:
        """Generate documentation for tests."""
        docs = "# Test Documentation\\n\\n"
        
        for case in test_cases:
            docs += f"## {case['name']}\\n"
            docs += f"**Description**: {case['description']}\\n"
            docs += f"**Type**: {case['type']}\\n"
            docs += f"**Assertions**: {', '.join(case['assertions'])}\\n\\n"
        
        return docs
    
    def _calculate_test_coverage(self, test_cases: list[dict], implementation: dict) -> dict[str, float]:
        """Calculate test coverage metrics."""
        components = implementation.get("files_created", [])
        tested_components = set()
        
        for case in test_cases:
            # Extract component name from test case name
            component = case["name"].replace("test_", "").split("_")[0]
            tested_components.add(component)
        
        coverage = len(tested_components) / len(components) if components else 0.0
        
        return {
            "component_coverage": coverage,
            "test_case_count": len(test_cases),
            "total_components": len(components)
        }
    
    def _select_testing_framework(self) -> str:
        """Select appropriate testing framework."""
        framework_map = {
            "python": "pytest",
            "javascript": "jest",
            "java": "junit",
            "go": "go test"
        }
        return framework_map.get(self.programming_language, "pytest")
    
    def _run_linting_analysis(self, implementation: dict[str, Any]) -> dict[str, Any]:
        """Run linting analysis on the code."""
        # Mock linting results
        return {
            "errors": [],
            "warnings": ["Consider adding type hints", "Document public methods"],
            "suggestions": ["Use f-strings for string formatting"],
            "score": 9.2
        }
    
    def _format_code(self, implementation: dict[str, Any]) -> dict[str, str]:
        """Format code according to style guidelines."""
        # Simple formatting (would use actual formatter in production)
        formatted = {}
        
        for filename, code in implementation.get("implementation", {}).items():
            # Basic formatting rules
            formatted_code = code.strip()
            if not formatted_code.endswith('\\n'):
                formatted_code += '\\n'
            
            formatted[filename] = formatted_code
        
        return formatted
    
    def _check_style_compliance(self, formatted_code: dict[str, str]) -> dict[str, Any]:
        """Check code style compliance."""
        return {
            "compliant": True,
            "style_guide": "PEP8" if self.programming_language == "python" else "Standard",
            "violations": [],
            "score": 10.0
        }
    
    def _identify_formatting_changes(self, original: str, formatted: str) -> list[str]:
        """Identify changes made during formatting."""
        changes = []
        
        if original != formatted:
            if original.strip() != formatted.strip():
                changes.append("Added trailing newline")
            if original.count(' ') != formatted.count(' '):
                changes.append("Adjusted whitespace")
        
        return changes
    
    def _generate_api_documentation(self, implementation: dict[str, Any]) -> str:
        """Generate API documentation."""
        return '''
# API Documentation

## Endpoints

### GET /api/v1/resource
Retrieve all resources.

**Parameters**: None
**Returns**: List of resources

### POST /api/v1/resource
Create a new resource.

**Parameters**: Resource data
**Returns**: Created resource
'''
    
    def _generate_code_comments(self, implementation: dict[str, Any]) -> str:
        """Generate inline code documentation."""
        return '''
## Code Documentation

### Main Module
Contains the main application logic and entry point.

### Service Module
Contains business logic and service classes.

### Utility Module
Contains helper functions and utilities.
'''
    
    def _generate_user_documentation(self, implementation: dict[str, Any]) -> str:
        """Generate user-facing documentation."""
        return '''
# User Guide

## Getting Started
1. Install dependencies
2. Configure environment
3. Run the application

## Usage Examples
Basic usage examples and tutorials.
'''
    
    def _generate_developer_documentation(self, implementation: dict[str, Any]) -> str:
        """Generate developer documentation."""
        return '''
# Developer Guide

## Architecture
System architecture and design patterns.

## Development Setup
Setting up development environment.

## Contributing
Guidelines for contributing to the project.
'''
    
    def _define_documentation_structure(self) -> dict[str, str]:
        """Define the documentation structure."""
        return {
            "readme": "README.md",
            "api_docs": "docs/api.md",
            "user_guide": "docs/user_guide.md",
            "developer_guide": "docs/developer_guide.md",
            "examples": "examples/"
        }
