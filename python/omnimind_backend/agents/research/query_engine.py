"""Research query engine with intent analysis and query planning.

Analyzes user questions, determines research strategy, and generates
multiple contextualized queries for parallel browser execution.
"""

from __future__ import annotations

import re
from typing import Any

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.schemas.agents.research import (
    QuestionType,
    QueryIntent,
    QueryPlan,
    SourceType,
)

_logger = get_logger(__name__)


class ResearchQueryEngine:
    """Engine for analyzing research intent and planning queries."""
    
    def __init__(self) -> None:
        """Initialize research query engine."""
        self.question_patterns = self._initialize_question_patterns()
        self.complexity_indicators = self._initialize_complexity_indicators()
        
    def analyze_intent(self, query: str) -> QueryIntent:
        """Analyze user query to determine research intent and strategy.
        
        Args:
            query: User research question
            
        Returns:
            QueryIntent with classification and strategy
        """
        # Clean and normalize query
        clean_query = self._clean_query(query)
        
        # Classify question type
        question_type = self._classify_question_type(clean_query)
        
        # Determine complexity level
        complexity_level = self._determine_complexity(clean_query, question_type)
        
        # Calculate browser count based on complexity
        browser_count = self._calculate_browser_count(complexity_level)
        
        # Identify target sources based on question type
        target_sources = self._identify_target_sources(question_type, clean_query)
        
        # Determine if deep navigation is needed
        requires_deep_navigation = self._requires_deep_navigation(question_type, complexity_level)
        
        # Estimate duration
        estimated_duration = self._estimate_duration(complexity_level, browser_count)
        
        intent = QueryIntent(
            question_type=question_type,
            complexity_level=complexity_level,
            browser_count=browser_count,
            target_sources=target_sources,
            requires_deep_navigation=requires_deep_navigation,
            estimated_duration_seconds=estimated_duration,
        )
        
        _logger.info(
            "query_intent_analyzed",
            original_query=query,
            question_type=question_type.value,
            complexity_level=complexity_level,
            browser_count=browser_count,
            target_sources=[source.value for source in target_sources],
        )
        
        return intent
        
    def plan_queries(self, intent: QueryIntent, original_query: str) -> QueryPlan:
        """Generate multiple contextualized queries based on intent.
        
        Args:
            intent: Analyzed query intent
            original_query: Original user query
            
        Returns:
            QueryPlan with multiple query variants
        """
        base_query = self._clean_query(original_query)
        
        # Generate query variants based on question type and complexity
        queries = self._generate_query_variants(base_query, intent)
        
        # Select appropriate search engines
        search_engines = self._select_search_engines(intent)
        
        # Determine max results per browser
        max_results_per_browser = self._determine_max_results(intent)
        
        plan = QueryPlan(
            intent=intent,
            queries=queries,
            search_engines=search_engines,
            max_results_per_browser=max_results_per_browser,
            parallel_execution=True,
        )
        
        _logger.info(
            "query_plan_created",
            question_type=intent.question_type.value,
            complexity_level=intent.complexity_level,
            queries_count=len(queries),
            search_engines=search_engines,
            max_results_per_browser=max_results_per_browser,
        )
        
        return plan
        
    def _clean_query(self, query: str) -> str:
        """Clean and normalize query text.
        
        Args:
            query: Original query text
            
        Returns:
            Cleaned query text
        """
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', query.strip())
        
        # Remove common question prefixes
        prefixes_to_remove = [
            "what is", "what are", "how do", "how can", "why does", "why do",
            "when should", "where can", "which is", "who is", "can you",
            "could you", "would you", "please", "tell me", "explain"
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                # Remove trailing question words
                if cleaned.lower().startswith(("is", "are", "does", "do", "can", "could")):
                    cleaned = cleaned[2:].strip() if len(cleaned) > 2 else cleaned
                break
                
        return cleaned
        
    def _classify_question_type(self, query: str) -> QuestionType:
        """Classify the type of research question.
        
        Args:
            query: Cleaned query text
            
        Returns:
            QuestionType classification
        """
        query_lower = query.lower()
        
        # Check patterns for each question type
        for question_type, patterns in self.question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return question_type
                    
        # Default to general if no pattern matches
        return QuestionType.GENERAL
        
    def _determine_complexity(self, query: str, question_type: QuestionType) -> str:
        """Determine complexity level of the query.
        
        Args:
            query: Cleaned query text
            question_type: Classified question type
            
        Returns:
            Complexity level string
        """
        complexity_score = 0
        
        # Base complexity by question type
        type_scores = {
            QuestionType.DEFINITION: 1,
            QuestionType.TUTORIAL: 2,
            QuestionType.DOCUMENTATION: 1,
            QuestionType.INFORMATIONAL_DATA: 2,
            QuestionType.COMPARISON: 3,
            QuestionType.CURRENT_STATE: 3,
            QuestionType.DEBUG: 4,
            QuestionType.GENERAL: 2,
        }
        
        complexity_score = type_scores.get(question_type, 2)
        
        # Add complexity based on indicators
        for indicator, score in self.complexity_indicators.items():
            if re.search(indicator, query.lower()):
                complexity_score += score
                
        # Map score to complexity level
        if complexity_score <= 2:
            return "simple"
        elif complexity_score <= 4:
            return "moderate"
        elif complexity_score <= 6:
            return "complex"
        else:
            return "deep"
            
    def _calculate_browser_count(self, complexity_level: str) -> int:
        """Calculate number of browsers needed based on complexity.
        
        Args:
            complexity_level: Complexity classification
            
        Returns:
            Number of browsers to use
        """
        browser_counts = {
            "simple": 1,
            "moderate": 2,
            "complex": 4,
            "deep": 6,
        }
        
        return browser_counts.get(complexity_level, 2)
        
    def _identify_target_sources(self, question_type: QuestionType, query: str) -> list[SourceType]:
        """Identify preferred source types for the question.
        
        Args:
            question_type: Classified question type
            query: Cleaned query text
            
        Returns:
            List of preferred source types
        """
        # Base source preferences by question type
        type_preferences = {
            QuestionType.DEFINITION: [SourceType.OFFICIAL, SourceType.ACADEMIC],
            QuestionType.TUTORIAL: [SourceType.OFFICIAL, SourceType.REPUTABLE_COMMUNITY],
            QuestionType.DOCUMENTATION: [SourceType.OFFICIAL],
            QuestionType.INFORMATIONAL_DATA: [SourceType.OFFICIAL, SourceType.ACADEMIC],
            QuestionType.COMPARISON: [SourceType.OFFICIAL, SourceType.TECH_PUBLICATION, SourceType.REPUTABLE_COMMUNITY],
            QuestionType.CURRENT_STATE: [SourceType.OFFICIAL, SourceType.TECH_PUBLICATION],
            QuestionType.DEBUG: [SourceType.REPUTABLE_COMMUNITY, SourceType.OFFICIAL],
            QuestionType.GENERAL: [SourceType.OFFICIAL, SourceType.ACADEMIC, SourceType.REPUTABLE_COMMUNITY],
        }
        
        return type_preferences.get(question_type, [SourceType.OFFICIAL, SourceType.REPUTABLE_COMMUNITY])
        
    def _requires_deep_navigation(self, question_type: QuestionType, complexity_level: str) -> bool:
        """Determine if deep navigation through sites is needed.
        
        Args:
            question_type: Classified question type
            complexity_level: Complexity classification
            
        Returns:
            True if deep navigation is required
        """
        # Tutorial and debug questions often require deep navigation
        if question_type in [QuestionType.TUTORIAL, QuestionType.DEBUG]:
            return True
            
        # Complex and deep research requires more thorough exploration
        if complexity_level in ["complex", "deep"]:
            return True
            
        return False
        
    def _estimate_duration(self, complexity_level: str, browser_count: int) -> int:
        """Estimate research duration in seconds.
        
        Args:
            complexity_level: Complexity classification
            browser_count: Number of browsers being used
            
        Returns:
            Estimated duration in seconds
        """
        # Base durations by complexity
        base_durations = {
            "simple": 30,
            "moderate": 60,
            "complex": 120,
            "deep": 180,
        }
        
        base_duration = base_durations.get(complexity_level, 60)
        
        # Adjust based on browser count (parallel execution reduces time)
        parallel_factor = min(browser_count, 4) / 4  # Diminishing returns after 4 browsers
        adjusted_duration = int(base_duration * (1.5 - 0.5 * parallel_factor))
        
        return max(30, adjusted_duration)  # Minimum 30 seconds
        
    def _generate_query_variants(self, base_query: str, intent: QueryIntent) -> list[str]:
        """Generate multiple query variants for different angles.
        
        Args:
            base_query: Cleaned base query
            intent: Query intent analysis
            
        Returns:
            List of query variants
        """
        queries = [base_query]  # Start with the original query
        
        # Generate variants based on question type
        if intent.question_type == QuestionType.DEFINITION:
            queries.extend([
                f"{base_query} definition official documentation",
                f"what is {base_query} explained",
                f"{base_query} meaning technical",
            ])
            
        elif intent.question_type == QuestionType.TUTORIAL:
            queries.extend([
                f"how to {base_query} tutorial step by step",
                f"{base_query} guide examples",
                f"{base_query} best practices",
            ])
            
        elif intent.question_type == QuestionType.COMPARISON:
            queries.extend([
                f"{base_query} comparison pros and cons",
                f"{base_query} vs alternatives benchmark",
                f"{base_query} differences features",
            ])
            
        elif intent.question_type == QuestionType.CURRENT_STATE:
            queries.extend([
                f"{base_query} latest updates 2024",
                f"{base_query} current status news",
                f"{base_query} recent changes changelog",
            ])
            
        elif intent.question_type == QuestionType.DEBUG:
            queries.extend([
                f"{base_query} error solution fix",
                f"{base_query} troubleshooting guide",
                f"{base_query} common issues stackoverflow",
            ])
            
        elif intent.question_type == QuestionType.INFORMATIONAL_DATA:
            queries.extend([
                f"{base_query} statistics data 2024",
                f"{base_query} metrics analysis report",
                f"{base_query} research findings",
            ])
            
        elif intent.question_type == QuestionType.DOCUMENTATION:
            queries.extend([
                f"{base_query} API documentation",
                f"{base_query} reference manual",
                f"{base_query} official docs site:docs.python.org",
            ])
            
        else:  # GENERAL
            queries.extend([
                f"{base_query} overview guide",
                f"{base_query} information resources",
                f"{base_query} examples tutorial",
            ])
            
        # Limit to browser count
        return queries[:intent.browser_count]
        
    def _select_search_engines(self, intent: QueryIntent) -> list[str]:
        """Select appropriate search engines for the query.
        
        Args:
            intent: Query intent analysis
            
        Returns:
            List of search engine URLs
        """
        # Base search engines
        engines = ["google.com", "duckduckgo.com"]
        
        # Add specialized engines based on question type
        if intent.question_type == QuestionType.DEBUG:
            engines.append("stackoverflow.com")
        elif intent.question_type == QuestionType.DOCUMENTATION:
            engines.append("github.com")
        elif intent.question_type == QuestionType.INFORMATIONAL_DATA:
            engines.append("scholar.google.com")
            
        return engines
        
    def _determine_max_results(self, intent: QueryIntent) -> int:
        """Determine maximum results per browser.
        
        Args:
            intent: Query intent analysis
            
        Returns:
            Maximum number of results to extract per browser
        """
        # More results for complex research
        if intent.complexity_level in ["complex", "deep"]:
            return 5
        elif intent.complexity_level == "moderate":
            return 3
        else:
            return 2
            
    def _initialize_question_patterns(self) -> dict[QuestionType, list[str]]:
        """Initialize regex patterns for question classification.
        
        Returns:
            Dictionary mapping question types to regex patterns
        """
        return {
            QuestionType.DEFINITION: [
                r'\b(what is|what are|define|definition|meaning of)\b',
                r'\b(explain|overview|introduction to)\b',
                r'\b(what does|what do)\b.*\b(mean)\b',
            ],
            QuestionType.TUTORIAL: [
                r'\b(how to|how do|how can|tutorial|guide|step by step)\b',
                r'\b(learn|implement|create|build|setup)\b',
                r'\b(instructions|walkthrough|getting started)\b',
            ],
            QuestionType.COMPARISON: [
                r'\b(compare|comparison|vs|versus|difference|differences)\b',
                r'\b(which is better|pros and cons|advantages disadvantages)\b',
                r'\b(alternative to|alternative for|instead of)\b',
            ],
            QuestionType.CURRENT_STATE: [
                r'\b(latest|current|recent|new|updated|status)\b',
                r'\b(what is the latest|what is new|what is current)\b',
                r'\b(2024|2023|recently|currently)\b',
            ],
            QuestionType.DEBUG: [
                r'\b(why does|why do|error|issue|problem|bug|fix)\b',
                r'\b(troubleshooting|debugging|not working|failed)\b',
                r'\b(solve|resolve|fix error)\b',
            ],
            QuestionType.INFORMATIONAL_DATA: [
                r'\b(statistics|data|metrics|numbers|figures)\b',
                r'\b(how many|how much|what percentage|what proportion)\b',
                r'\b(research|study|survey|report|analysis)\b',
            ],
            QuestionType.DOCUMENTATION: [
                r'\b(api|documentation|docs|reference|manual)\b',
                r'\b(syntax|parameters|arguments|methods|functions)\b',
                r'\b(official docs|site:docs\.|site:developer\.)\b',
            ],
        }
        
    def _initialize_complexity_indicators(self) -> dict[str, int]:
        """Initialize complexity indicators and their scores.
        
        Returns:
            Dictionary mapping regex patterns to complexity scores
        """
        return {
            r'\b(multiple|various|different|several)\b': 1,
            r'\b(compare|comparison|vs|versus)\b': 1,
            r'\b(analysis|analyze|research|study)\b': 1,
            r'\b(complex|complicated|advanced)\b': 2,
            r'\b(integration|integrate|architecture|design)\b': 2,
            r'\b(performance|optimization|scalability)\b': 2,
            r'\b(security|authentication|authorization)\b': 2,
            r'\b(troubleshooting|debug|error|issue)\b': 2,
            r'\b(best practices|recommendations|guidelines)\b': 1,
            r'\b(step by step|detailed|comprehensive)\b': 1,
            r'\b(real world|practical|production)\b': 1,
        }


# Global query engine instance
_query_engine: ResearchQueryEngine | None = None


def get_research_query_engine() -> ResearchQueryEngine:
    """Get or create the global research query engine instance."""
    global _query_engine
    if _query_engine is None:
        _query_engine = ResearchQueryEngine()
    return _query_engine
