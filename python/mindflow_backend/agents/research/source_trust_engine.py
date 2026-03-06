"""Advanced source trust evaluation engine.

Provides dynamic trust scoring, cross-reference validation,
bias detection, and content freshness verification.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.agents.research import (
    SourceClassification,
    SourceType,
    ConfidenceLevel,
)

_logger = get_logger(__name__)


class TrustSignal:
    """Individual trust signal for a source."""
    
    def __init__(
        self,
        signal_type: str,
        weight: float,
        value: float,
        description: str,
    ) -> None:
        """Initialize trust signal.
        
        Args:
            signal_type: Type of signal (domain_authority, freshness, etc.)
            weight: Weight of this signal in overall score (0.0-1.0)
            value: Signal value (0.0-1.0)
            description: Human-readable description
        """
        self.signal_type = signal_type
        self.weight = weight
        self.value = value
        self.description = description
        self.timestamp = datetime.now(UTC)
        
    def get_weighted_score(self) -> float:
        """Calculate weighted score for this signal.
        
        Returns:
            Weighted score value
        """
        return self.weight * self.value


class DomainAuthority:
    """Domain authority calculation and caching."""
    
    # Pre-computed domain authorities (simplified version)
    DOMAIN_AUTHORITIES = {
        # Official docs (highest authority)
        "docs.python.org": 0.95,
        "developer.mozilla.org": 0.94,
        "learn.microsoft.com": 0.93,
        "cloud.google.com": 0.92,
        "docs.aws.amazon.com": 0.91,
        "reactjs.org": 0.90,
        "vuejs.org": 0.89,
        "angular.io": 0.88,
        "fastapi.tiangolo.com": 0.87,
        "docs.djangoproject.com": 0.86,
        "kubernetes.io": 0.85,
        "docs.docker.com": 0.84,
        
        # Academic sources
        "arxiv.org": 0.88,
        "scholar.google.com": 0.87,
        "ieee.org": 0.86,
        "acm.org": 0.85,
        "researchgate.net": 0.75,
        
        # Reputable community
        "stackoverflow.com": 0.82,
        "github.com": 0.80,
        "devdocs.io": 0.78,
        
        # Tech publications
        "medium.com": 0.65,
        "dev.to": 0.63,
        "css-tricks.com": 0.70,
        "hackernoon.com": 0.64,
        "towardsdatascience.com": 0.68,
        
        # News aggregators
        "news.ycombinator.com": 0.60,
        "reddit.com": 0.55,
    }
    
    @classmethod
    def get_authority(cls, url: str) -> float:
        """Get domain authority score for a URL.
        
        Args:
            url: Source URL
            
        Returns:
            Domain authority score (0.0-1.0)
        """
        try:
            domain = urlparse(url).netloc.lower().removeprefix("www.")
        except Exception:
            return 0.1  # Very low authority for invalid URLs
            
        # Direct lookup
        if domain in cls.DOMAIN_AUTHORITIES:
            return cls.DOMAIN_AUTHORITIES[domain]
            
        # Check for official subdomains
        if domain.startswith("docs.") or domain.startswith("api."):
            return 0.85  # High authority for official subdomains
            
        # Check for academic domains
        if domain.endswith(".edu") or domain.endswith(".gov"):
            return 0.90  # Very high authority for educational/government
            
        # Check for common TLDs
        if any(domain.endswith(tld) for tld in [".org", ".io", ".dev"]):
            return 0.60  # Medium authority for these TLDs
            
        # Default low authority for unknown domains
        return 0.30


class ContentFreshness:
    """Content freshness evaluation."""
    
    @staticmethod
    def extract_freshness_indicators(content: str) -> Dict[str, any]:
        """Extract freshness indicators from content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Dictionary with freshness metrics
        """
        current_year = datetime.now(UTC).year
        
        # Year mentions
        year_pattern = r'\b(20(1[5-9]|2[0-6])\b'
        years = re.findall(year_pattern, content)
        recent_years = [int(year) for year in years if int(year) >= current_year - 2]
        
        # Freshness keywords
        freshness_keywords = [
            "latest", "new", "updated", "recent", "current",
            "2026", "2025", "v2", "v3", "modern"
        ]
        keyword_count = sum(
            1 for keyword in freshness_keywords 
            if keyword.lower() in content.lower()
        )
        
        # Outdated indicators
        outdated_keywords = [
            "legacy", "deprecated", "old", "ancient", "obsolete",
            "2010", "2011", "2012", "2013", "2014", "2015"
        ]
        outdated_count = sum(
            1 for keyword in outdated_keywords 
            if keyword.lower() in content.lower()
        )
        
        return {
            "recent_years": recent_years,
            "max_recent_year": max(recent_years) if recent_years else None,
            "freshness_keywords": keyword_count,
            "outdated_keywords": outdated_count,
            "has_recent_content": len(recent_years) > 0 or keyword_count > 0,
            "seems_outdated": outdated_count > keyword_count + 1,
        }
        
    @staticmethod
    def calculate_freshness_score(indicators: Dict[str, any]) -> float:
        """Calculate freshness score from indicators.
        
        Args:
            indicators: Freshness indicators from extract_freshness_indicators
            
        Returns:
            Freshness score (0.0-1.0)
        """
        score = 0.5  # Base score
        
        # Boost for recent years
        if indicators["recent_years"]:
            latest_year = indicators["max_recent_year"]
            current_year = datetime.now(UTC).year
            year_freshness = 1.0 - (current_year - latest_year) * 0.1
            score += year_freshness * 0.3
            
        # Boost for freshness keywords
        if indicators["freshness_keywords"] > 0:
            score += min(indicators["freshness_keywords"] * 0.1, 0.3)
            
        # Penalty for outdated indicators
        if indicators["outdated_keywords"] > 0:
            score -= indicators["outdated_keywords"] * 0.15
            
        return max(0.0, min(1.0, score))


class BiasDetector:
    """Detect potential bias in source content."""
    
    # Bias indicators
    BIAS_PATTERNS = {
        "promotional": [
            r"buy now", r"limited time", r"exclusive offer", r"best price",
            r"guaranteed", r"risk.?free", r"instant results"
        ],
        "clickbait": [
            r"you won't believe", r"shocking", r"unbelievable", r"mind.?blowing",
            r"the secret", r"they don't want you to know", r"one weird trick"
        ],
        "sensationalist": [
            r"amazing", r"incredible", r"revolutionary", r"game.?changer",
            r"life.?changing", r"unprecedented", r"historic"
        ],
        "opinion": [
            r"i think", r"in my opinion", r"personally", r"i believe",
            r"from my experience", r"i feel that"
        ]
    }
    
    @classmethod
    def detect_bias(cls, content: str) -> Dict[str, float]:
        """Detect bias indicators in content.
        
        Args:
            content: Text content to analyze
            
        Returns:
            Dictionary with bias scores by type
        """
        content_lower = content.lower()
        bias_scores = {}
        
        for bias_type, patterns in cls.BIAS_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower))
                score += matches * 0.2  # Each match adds 0.2 to bias score
                
            bias_scores[bias_type] = min(score, 1.0)  # Cap at 1.0
            
        return bias_scores
        
    @classmethod
    def calculate_bias_penalty(cls, bias_scores: Dict[str, float]) -> float:
        """Calculate overall bias penalty.
        
        Args:
            bias_scores: Bias scores by type
            
        Returns:
            Overall bias penalty (0.0-1.0)
        """
        # Weight different bias types differently
        weights = {
            "promotional": 0.8,  # High penalty for promotional content
            "clickbait": 0.9,     # Very high penalty for clickbait
            "sensationalist": 0.7,  # High penalty for sensationalism
            "opinion": 0.4,          # Moderate penalty for opinion content
        }
        
        total_penalty = 0.0
        total_weight = 0.0
        
        for bias_type, score in bias_scores.items():
            weight = weights.get(bias_type, 0.5)
            total_penalty += score * weight
            total_weight += weight
            
        return total_penalty / total_weight if total_weight > 0 else 0.0


class CrossReferenceValidator:
    """Validates information across multiple sources."""
    
    def __init__(self) -> None:
        """Initialize cross-reference validator."""
        self._source_facts: Dict[str, Set[str]] = {}
        
    def add_source_facts(self, source_url: str, facts: List[str]) -> None:
        """Add facts from a source for cross-reference validation.
        
        Args:
            source_url: URL of the source
            facts: List of factual claims from the source
        """
        normalized_facts = set(fact.lower().strip() for fact in facts)
        self._source_facts[source_url] = normalized_facts
        
    def calculate_cross_reference_score(self, source_url: str) -> float:
        """Calculate cross-reference validation score for a source.
        
        Args:
            source_url: URL to validate
            
        Returns:
            Cross-reference score (0.0-1.0)
        """
        if source_url not in self._source_facts:
            return 0.0  # No facts to validate
            
        source_facts = self._source_facts[source_url]
        if not source_facts:
            return 0.5  # Neutral score for empty facts
            
        # Count corroborating sources
        corroborating_sources = 0
        total_other_sources = len(self._source_facts) - 1
        
        for other_url, other_facts in self._source_facts.items():
            if other_url == source_url:
                continue
                
            # Calculate overlap
            overlap = len(source_facts.intersection(other_facts))
            if overlap > 0:
                corroborating_sources += 1
                
        # Calculate validation score
        if total_other_sources == 0:
            return 0.5  # Neutral if only one source
            
        validation_ratio = corroborating_sources / total_other_sources
        return min(validation_ratio, 1.0)
        
    def find_conflicts(self, source_url: str) -> List[str]:
        """Find conflicting facts across sources.
        
        Args:
            source_url: URL to check for conflicts
            
        Returns:
            List of conflicting fact descriptions
        """
        if source_url not in self._source_facts:
            return []
            
        conflicts = []
        source_facts = self._source_facts[source_url]
        
        for other_url, other_facts in self._source_facts.items():
            if other_url == source_url:
                continue
                
            # Find contradictions (simplified)
            for fact in source_facts:
                if any(
                    self._are_contradictory(fact, other_fact)
                    for other_fact in other_facts
                ):
                    conflicts.append(f"Contradicts {other_url}: '{fact}' vs '{other_fact}'")
                    
        return conflicts
        
    def _are_contradictory(self, fact1: str, fact2: str) -> bool:
        """Check if two facts are contradictory.
        
        Args:
            fact1: First fact
            fact2: Second fact
            
        Returns:
            True if facts contradict each other
        """
        # Simple contradiction patterns
        contradictions = [
            ("supported", "not supported"),
            ("required", "optional"),
            ("enabled", "disabled"),
            ("available", "unavailable"),
            ("compatible", "incompatible"),
            ("secure", "insecure"),
            ("fast", "slow"),
            ("easy", "difficult"),
        ]
        
        fact1_lower = fact1.lower()
        fact2_lower = fact2.lower()
        
        for pos, neg in contradictions:
            if (pos in fact1_lower and neg in fact2_lower) or \
               (neg in fact1_lower and pos in fact2_lower):
                return True
                
        return False


class SourceTrustEngine:
    """Advanced source trust evaluation engine."""
    
    def __init__(self) -> None:
        """Initialize source trust engine."""
        self.domain_authority = DomainAuthority()
        self.content_freshness = ContentFreshness()
        self.bias_detector = BiasDetector()
        self.cross_validator = CrossReferenceValidator()
        
    def evaluate_source(
        self,
        url: str,
        content: str,
        title: str = "",
        existing_sources: List[str] = None,
    ) -> SourceClassification:
        """Comprehensive source trust evaluation.
        
        Args:
            url: Source URL
            content: Page content
            title: Page title (optional)
            existing_sources: List of other source URLs for cross-reference
            
        Returns:
            SourceClassification with trust metrics
        """
        # Base source type classification
        source_type = self._classify_source_type(url)
        
        # Collect trust signals
        signals = []
        
        # 1. Domain Authority Signal
        domain_score = DomainAuthority.get_authority(url)
        signals.append(TrustSignal(
            signal_type="domain_authority",
            weight=0.4,
            value=domain_score,
            description=f"Domain authority: {domain_score:.2f}"
        ))
        
        # 2. Content Freshness Signal
        freshness_indicators = ContentFreshness.extract_freshness_indicators(content)
        freshness_score = ContentFreshness.calculate_freshness_score(freshness_indicators)
        signals.append(TrustSignal(
            signal_type="content_freshness",
            weight=0.2,
            value=freshness_score,
            description=f"Content freshness: {freshness_score:.2f}"
        ))
        
        # 3. Bias Detection Signal
        bias_scores = BiasDetector.detect_bias(content)
        bias_penalty = BiasDetector.calculate_bias_penalty(bias_scores)
        bias_score = max(0.0, 1.0 - bias_penalty)  # Convert penalty to score
        signals.append(TrustSignal(
            signal_type="bias_score",
            weight=0.2,
            value=bias_score,
            description=f"Bias score: {bias_score:.2f}"
        ))
        
        # 4. Cross-Reference Signal (if other sources available)
        if existing_sources:
            # Extract facts from content (simplified)
            facts = self._extract_facts(content)
            self.cross_validator.add_source_facts(url, facts)
            
            cross_ref_score = self.cross_validator.calculate_cross_reference_score(url)
            signals.append(TrustSignal(
                signal_type="cross_reference",
                weight=0.2,
                value=cross_ref_score,
                description=f"Cross-reference validation: {cross_ref_score:.2f}"
            ))
        else:
            cross_ref_score = 0.5  # Neutral when no cross-reference available
            
        # Calculate overall trust score
        overall_score = sum(signal.get_weighted_score() for signal in signals)
        
        # Determine confidence level
        confidence_level = self._determine_confidence_level(overall_score)
        
        # Check for conflicts
        conflicts = self.cross_validator.find_conflicts(url) if existing_sources else []
        
        classification = SourceClassification(
            url=url,
            source_type=source_type,
            trust_level=confidence_level,
            domain_authority=domain_score,
            content_type=self._detect_content_type(content, title),
            last_updated=self._extract_last_updated(content),
        )
        
        _logger.info(
            "source_trust_evaluated",
            url=url[:100],
            source_type=source_type.value,
            trust_score=overall_score,
            confidence_level=confidence_level.value,
            cross_ref_sources=len(existing_sources) if existing_sources else 0,
        )
        
        return classification
        
    def _classify_source_type(self, url: str) -> SourceType:
        """Classify source type based on URL patterns.
        
        Args:
            url: Source URL
            
        Returns:
            SourceType enum value
        """
        try:
            domain = urlparse(url).netloc.lower().removeprefix("www.")
        except Exception:
            return SourceType.UNKNOWN_BLOG
            
        # Official sources
        if any(official in domain for official in [
            "docs.", "api.", "developer.", ".gov", ".edu"
        ]):
            return SourceType.OFFICIAL
            
        # Academic sources
        if any(academic in domain for academic in [
            "arxiv", "scholar", "research.", ".edu"
        ]):
            return SourceType.ACADEMIC
            
        # Reputable community
        if any(community in domain for community in [
            "stackoverflow", "github", "reddit", "devdocs"
        ]):
            return SourceType.REPUTABLE_COMMUNITY
            
        # Tech publications
        if any(tech in domain for tech in [
            "medium.com", "dev.to", "css-tricks", "hackernoon",
            "towardsdatascience.com"
        ]):
            return SourceType.TECH_PUBLICATION
            
        # Social media
        if any(social in domain for social in [
            "twitter.com", "x.com", "facebook.com", "linkedin.com"
        ]):
            return SourceType.SOCIAL
            
        return SourceType.UNKNOWN_BLOG
        
    def _detect_content_type(self, content: str, title: str) -> str:
        """Detect the type of content.
        
        Args:
            content: Page content
            title: Page title
            
        Returns:
            Content type description
        """
        content_lower = content.lower()
        title_lower = title.lower()
        
        # API documentation
        if any(api in content_lower for api in [
            "api reference", "endpoint", "request", "response", "authentication"
        ]):
            return "api_documentation"
            
        # Tutorial/How-to
        if any(tutorial in content_lower for tutorial in [
            "step by step", "how to", "tutorial", "guide", "example"
        ]):
            return "tutorial"
            
        # News/Article
        if any(news in content_lower for news in [
            "news", "announcement", "release", "update", "published"
        ]):
            return "news_article"
            
        # Documentation
        if any(doc in content_lower for doc in [
            "documentation", "docs", "manual", "reference"
        ]):
            return "documentation"
            
        return "general_content"
        
    def _extract_last_updated(self, content: str) -> str | None:
        """Extract last updated date from content.
        
        Args:
            content: Page content
            
        Returns:
            Last updated date string or None
        """
        # Common date patterns
        date_patterns = [
            r'last updated?:?\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'updated?:?\s*(\d{4}-\d{2}-\d{2})',
            r'modified?:?\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{4}-\d{2}-\d{2})',  # ISO dates
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
                
        return None
        
    def _extract_facts(self, content: str) -> List[str]:
        """Extract factual claims from content (simplified).
        
        Args:
            content: Page content
            
        Returns:
            List of factual claims
        """
        facts = []
        
        # Pattern for factual statements (simplified)
        fact_patterns = [
            r'(\w+\s+is\s+\w+)',  # X is Y
            r'(\w+\s+supports?\s+\w+)',  # X supports Y
            r'(\w+\s+requires?\s+\w+)',  # X requires Y
            r'(\w+\s+version\s+\d+\.?\d*)',  # X version Y
        ]
        
        for pattern in fact_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            facts.extend(matches[:3])  # Limit to avoid noise
            
        return facts
        
    def _determine_confidence_level(self, trust_score: float) -> ConfidenceLevel:
        """Determine confidence level from trust score.
        
        Args:
            trust_score: Overall trust score (0.0-1.0)
            
        Returns:
            ConfidenceLevel enum value
        """
        if trust_score >= 0.8:
            return ConfidenceLevel.HIGH
        elif trust_score >= 0.6:
            return ConfidenceLevel.MEDIUM
        elif trust_score >= 0.4:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.UNKNOWN


# Global trust engine instance
_source_trust_engine: SourceTrustEngine | None = None


def get_source_trust_engine() -> SourceTrustEngine:
    """Get or create global source trust engine instance.
    
    Returns:
        SourceTrustEngine singleton instance
    """
    global _source_trust_engine
    if _source_trust_engine is None:
        _source_trust_engine = SourceTrustEngine()
    return _source_trust_engine
