"""Intelligent result synthesis with conflict resolution.

Provides conflict detection, confidence-weighted synthesis,
automatic citation formatting, and gap identification.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from mindflow_backend.infra.logging import get_logger
from mindflow_backend.schemas.agents.research import (
    ResearchFinding,
    SourceType,
)

_logger = get_logger(__name__)


class ConflictDetector:
    """Detects and resolves conflicts between sources."""
    
    def __init__(self) -> None:
        """Initialize conflict detector."""
        pass
        
    def find_conflicts(self, findings: list[ResearchFinding]) -> list[dict[str, any]]:
        """Find conflicts between research findings.
        
        Args:
            findings: List of research findings to analyze
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        # Check for numerical contradictions
        numerical_conflicts = self._find_numerical_conflicts(findings)
        conflicts.extend(numerical_conflicts)
        
        # Check for factual contradictions
        factual_conflicts = self._find_factual_conflicts(findings)
        conflicts.extend(factual_conflicts)
        
        # Check for temporal contradictions
        temporal_conflicts = self._find_temporal_conflicts(findings)
        conflicts.extend(temporal_conflicts)
        
        # Check for recommendation conflicts
        recommendation_conflicts = self._find_recommendation_conflicts(findings)
        conflicts.extend(recommendation_conflicts)
        
        return conflicts
        
    def _find_numerical_conflicts(self, findings: list[ResearchFinding]) -> list[dict[str, any]]:
        """Find contradictions in numerical data.
        
        Args:
            findings: List of research findings
            
        Returns:
            List of numerical conflict descriptions
        """
        conflicts = []
        
        # Extract numerical values
        numerical_data = {}
        for finding in findings:
            numbers = self._extract_numbers(finding.content_summary)
            for number, context in numbers:
                key = self._normalize_numerical_key(context)
                if key not in numerical_data:
                    numerical_data[key] = []
                numerical_data[key].append({
                    "value": number,
                    "source": finding.source_url,
                    "confidence": finding.confidence_score,
                    "context": context,
                })
                
        # Find conflicts in each numerical category
        for key, values in numerical_data.items():
            if len(values) < 2:
                continue
                
            # Check for significant differences (>20% variance)
            numeric_values = [v["value"] for v in values]
            if max(numeric_values) > 0:
                variance = (max(numeric_values) - min(numeric_values)) / max(numeric_values)
                if variance > 0.2:  # 20% variance threshold
                    conflicts.append({
                        "type": "numerical_contradiction",
                        "key": key,
                        "values": values,
                        "variance_percent": variance * 100,
                        "description": f"Significant variance in {key}: {min(numeric_values)} vs {max(numeric_values)}",
                    })
                    
        return conflicts
        
    def _find_factual_conflicts(self, findings: list[ResearchFinding]) -> list[dict[str, any]]:
        """Find contradictions in factual statements.
        
        Args:
            findings: List of research findings
            
        Returns:
            List of factual conflict descriptions
        """
        conflicts = []
        
        # Extract factual statements
        factual_statements = {}
        for finding in findings:
            statements = self._extract_factual_statements(finding.content_summary)
            for statement in statements:
                key = self._normalize_factual_key(statement)
                if key not in factual_statements:
                    factual_statements[key] = []
                factual_statements[key].append({
                    "statement": statement,
                    "source": finding.source_url,
                    "confidence": finding.confidence_score,
                })
                
        # Find contradictory statements
        for key, statements in factual_statements.items():
            if len(statements) < 2:
                continue
                
            # Check for direct contradictions
            for i, stmt1 in enumerate(statements):
                for stmt2 in statements[i+1:]:
                    if self._are_contradictory_statements(stmt1["statement"], stmt2["statement"]):
                        conflicts.append({
                            "type": "factual_contradiction",
                            "key": key,
                            "statements": [stmt1, stmt2],
                            "description": f"Contradictory statements about {key}",
                        })
                        
        return conflicts
        
    def _find_temporal_conflicts(self, findings: list[ResearchFinding]) -> list[dict[str, any]]:
        """Find contradictions in temporal information.
        
        Args:
            findings: List of research findings
            
        Returns:
            List of temporal conflict descriptions
        """
        conflicts = []
        
        # Extract temporal information
        temporal_data = []
        for finding in findings:
            dates = self._extract_dates(finding.content_summary)
            for date, context in dates:
                temporal_data.append({
                    "date": date,
                    "source": finding.source_url,
                    "confidence": finding.confidence_score,
                    "context": context,
                })
                
        # Find conflicting dates
        if len(temporal_data) < 2:
            return conflicts
            
        # Sort by date
        temporal_data.sort(key=lambda x: x["date"])
        
        # Check for impossible sequences
        for i in range(1, len(temporal_data)):
            current = temporal_data[i]
            previous = temporal_data[i-1]
            
            # If a source claims something happened before it was actually released
            if current["date"] < previous["date"]:
                conflicts.append({
                    "type": "temporal_contradiction",
                    "earlier_source": current["source"],
                    "later_source": previous["source"],
                    "description": f"Temporal sequence violation: {current['date']} before {previous['date']}",
                })
                
        return conflicts
        
    def _find_recommendation_conflicts(self, findings: list[ResearchFinding]) -> list[dict[str, any]]:
        """Find conflicts in recommendations.
        
        Args:
            findings: List of research findings
            
        Returns:
            List of recommendation conflict descriptions
        """
        conflicts = []
        
        # Extract recommendations
        recommendations = []
        for finding in findings:
            recs = self._extract_recommendations(finding.content_summary)
            for rec in recs:
                recommendations.append({
                    "recommendation": rec,
                    "source": finding.source_url,
                    "confidence": finding.confidence_score,
                })
                
        # Find opposing recommendations
        for i, rec1 in enumerate(recommendations):
            for rec2 in recommendations[i+1:]:
                if self._are_opposing_recommendations(rec1["recommendation"], rec2["recommendation"]):
                    conflicts.append({
                        "type": "recommendation_contradiction",
                        "recommendations": [rec1, rec2],
                        "description": f"Opposing recommendations: '{rec1['recommendation']}' vs '{rec2['recommendation']}'",
                    })
                    
        return conflicts
        
    def _extract_numbers(self, text: str) -> list[tuple[float, str]]:
        """Extract numerical values with context.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (number, context) tuples
        """
        # Pattern to find numbers with some context
        pattern = r'(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)'
        matches = re.findall(pattern, text)
        
        numbers = []
        for match in matches:
            try:
                number = float(match[0])
                context = match[1].lower()
                numbers.append((number, context))
            except ValueError:
                continue
                
        return numbers
        
    def _extract_factual_statements(self, text: str) -> list[str]:
        """Extract factual statements from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of factual statements
        """
        # Pattern for factual statements (simplified)
        patterns = [
            r'(\w+\s+is\s+\w+)',  # X is Y
            r'(\w+\s+supports?\s+\w+)',  # X supports Y
            r'(\w+\s+requires?\s+\w+)',  # X requires Y
            r'(\w+\s+version\s+\d+)',  # X version Y
            r'(\w+\s+was\s+released\s+in\s+\d{4})',  # X was released in Y
        ]
        
        statements = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            statements.extend(matches)
            
        return statements
        
    def _extract_dates(self, text: str) -> list[tuple[str, str]]:
        """Extract dates with context.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (date, context) tuples
        """
        # Common date patterns
        patterns = [
            (r'(\d{4}-\d{2}-\d{2})', 'date'),
            (r'(\d{1,2}/\d{1,2}/\d{4})', 'date'),
            (r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', 'date'),
        ]
        
        dates = []
        for pattern, context in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.append((match, context))
                
        return dates
        
    def _extract_recommendations(self, text: str) -> list[str]:
        """Extract recommendations from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of recommendation strings
        """
        patterns = [
            r'(should?\s+\w+)',
            r'(recommend\s+\w+)',
            r'(use?\s+\w+)',
            r'(avoid\s+\w+)',
            r'(prefer\s+\w+)',
        ]
        
        recommendations = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            recommendations.extend(matches)
            
        return recommendations
        
    def _normalize_numerical_key(self, context: str) -> str:
        """Normalize numerical context to a standard key.
        
        Args:
            context: Context string from number extraction
            
        Returns:
            Normalized key
        """
        # Map common contexts to standard keys
        context_mapping = {
            "version": "version",
            "v": "version",
            "mb": "memory",
            "gb": "memory",
            "percent": "percentage",
            "%": "percentage",
            "ms": "time",
            "seconds": "time",
            "s": "time",
        }
        
        return context_mapping.get(context.lower(), context.lower())
        
    def _normalize_factual_key(self, statement: str) -> str:
        """Normalize factual statement to a standard key.
        
        Args:
            statement: Factual statement string
            
        Returns:
            Normalized key
        """
        # Extract key terms (simplified)
        words = statement.lower().split()
        if len(words) >= 2:
            return f"{words[0]}_{words[-1]}"  # First and last words
        return statement.lower()
        
    def _are_contradictory_statements(self, stmt1: str, stmt2: str) -> bool:
        """Check if two statements are contradictory.
        
        Args:
            stmt1: First statement
            stmt2: Second statement
            
        Returns:
            True if statements contradict each other
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
        
        stmt1_lower = stmt1.lower()
        stmt2_lower = stmt2.lower()
        
        for pos, neg in contradictions:
            if (pos in stmt1_lower and neg in stmt2_lower) or \
               (neg in stmt1_lower and pos in stmt2_lower):
                return True
                
        return False
        
    def _are_opposing_recommendations(self, rec1: str, rec2: str) -> bool:
        """Check if two recommendations oppose each other.
        
        Args:
            rec1: First recommendation
            rec2: Second recommendation
            
        Returns:
            True if recommendations oppose each other
        """
        # Opposing recommendation patterns
        opposing_pairs = [
            ("use", "avoid"),
            ("enable", "disable"),
            ("prefer", "avoid"),
            ("recommend", "warn against"),
        ]
        
        rec1_lower = rec1.lower()
        rec2_lower = rec2.lower()
        
        for pos, neg in opposing_pairs:
            if (pos in rec1_lower and neg in rec2_lower) or \
               (neg in rec1_lower and pos in rec2_lower):
                return True
                
        return False


class ConfidenceWeightedSynthesizer:
    """Synthesizes results using confidence-weighted aggregation."""
    
    def __init__(self) -> None:
        """Initialize confidence-weighted synthesizer."""
        pass
        
    def synthesize_findings(self, findings: list[ResearchFinding]) -> dict[str, any]:
        """Synthesize findings using confidence-weighted approach.
        
        Args:
            findings: List of research findings
            
        Returns:
            Synthesis results with weighted insights
        """
        if not findings:
            return {
                "summary": "No research findings available.",
                "key_points": [],
                "confidence_breakdown": {},
                "weighted_summary": "",
            }
            
        # Sort by confidence score
        sorted_findings = sorted(findings, key=lambda f: f.confidence_score, reverse=True)
        
        # Calculate confidence breakdown
        confidence_breakdown = self._calculate_confidence_breakdown(findings)
        
        # Extract key points with confidence weighting
        weighted_key_points = self._extract_weighted_key_points(sorted_findings)
        
        # Generate weighted summary
        weighted_summary = self._generate_weighted_summary(sorted_findings)
        
        # Identify consensus and disagreements
        consensus_analysis = self._analyze_consensus(findings)
        
        return {
            "summary": weighted_summary,
            "key_points": weighted_key_points,
            "confidence_breakdown": confidence_breakdown,
            "consensus_analysis": consensus_analysis,
            "high_confidence_sources": [
                f.source_url for f in sorted_findings if f.confidence_score >= 0.8
            ],
        }
        
    def _calculate_confidence_breakdown(self, findings: list[ResearchFinding]) -> dict[str, float]:
        """Calculate confidence score breakdown by source type.
        
        Args:
            findings: List of research findings
            
        Returns:
            Dictionary with confidence breakdown by source type
        """
        breakdown = defaultdict(list)
        
        for finding in findings:
            source_type = finding.source_classification.source_type.value
            breakdown[source_type].append(finding.confidence_score)
            
        # Calculate averages
        avg_breakdown = {}
        for source_type, scores in breakdown.items():
            avg_breakdown[source_type] = sum(scores) / len(scores) if scores else 0.0
            
        return dict(avg_breakdown)
        
    def _extract_weighted_key_points(self, findings: list[ResearchFinding]) -> list[str]:
        """Extract key points weighted by confidence.
        
        Args:
            findings: List of research findings sorted by confidence
            
        Returns:
            List of weighted key points
        """
        all_points = []
        
        for finding in findings:
            # Weight key points by confidence
            weight = finding.confidence_score
            
            for point in finding.key_points:
                all_points.append({
                    "point": point,
                    "weight": weight,
                    "source": finding.source_url,
                })
                
        # Sort by weight and deduplicate
        unique_points = {}
        for item in all_points:
            point = item["point"]
            if point not in unique_points or item["weight"] > unique_points[point]["weight"]:
                unique_points[point] = item
                
        # Return top weighted points
        sorted_points = sorted(unique_points.values(), key=lambda x: x["weight"], reverse=True)
        
        return [item["point"] for item in sorted_points[:10]]  # Top 10 points
        
    def _generate_weighted_summary(self, findings: list[ResearchFinding]) -> str:
        """Generate a confidence-weighted summary.
        
        Args:
            findings: List of research findings
            
        Returns:
            Weighted summary string
        """
        if not findings:
            return "No findings available for synthesis."
            
        # Calculate overall confidence
        total_confidence = sum(f.confidence_score for f in findings)
        avg_confidence = total_confidence / len(findings)
        
        # Determine primary sources (high confidence)
        primary_sources = [f for f in findings if f.confidence_score >= 0.7]
        
        # Generate summary based on confidence levels
        if avg_confidence >= 0.8:
            confidence_desc = "high confidence"
            summary_basis = "primarily from official and highly trusted sources"
        elif avg_confidence >= 0.6:
            confidence_desc = "moderate confidence"
            summary_basis = "from reputable sources with some verification needed"
        else:
            confidence_desc = "low confidence"
            summary_basis = "from various sources requiring additional verification"
            
        # Count source types
        source_types = Counter(f.source_classification.source_type.value for f in findings)
        
        summary_parts = [
            f"Research findings indicate {confidence_desc} ({avg_confidence:.2f} average confidence).",
            f"Analysis based on {len(findings)} sources, primarily {', '.join(source_types.keys())}.",
            f"Conclusions drawn {summary_basis}.",
        ]
        
        if primary_sources:
            summary_parts.append(f"Key insights from {len(primary_sources)} high-confidence sources.")
            
        return ". ".join(summary_parts)
        
    def _analyze_consensus(self, findings: list[ResearchFinding]) -> dict[str, any]:
        """Analyze consensus and disagreements among sources.
        
        Args:
            findings: List of research findings
            
        Returns:
            Consensus analysis results
        """
        if len(findings) < 2:
            return {"consensus_level": "insufficient_data"}
            
        # Group by content similarity (simplified)
        content_groups = self._group_by_content_similarity(findings)
        
        consensus_analysis = {
            "total_sources": len(findings),
            "content_groups": len(content_groups),
            "consensus_level": "mixed",
            "disagreements": [],
        }
        
        # Check for consensus
        if len(content_groups) == 1:
            consensus_analysis["consensus_level"] = "strong"
        elif len(content_groups) <= len(findings) * 0.3:
            consensus_analysis["consensus_level"] = "moderate"
        else:
            consensus_analysis["consensus_level"] = "weak"
            
        # Identify specific disagreements
        for group in content_groups:
            if len(group) > 1:
                # Check for conflicting information within group
                conflicts = self._find_group_conflicts(group)
                consensus_analysis["disagreements"].extend(conflicts)
                
        return consensus_analysis
        
    def _group_by_content_similarity(self, findings: list[ResearchFinding]) -> list[list[ResearchFinding]]:
        """Group findings by content similarity.
        
        Args:
            findings: List of research findings
            
        Returns:
            List of content groups
        """
        groups = []
        used = set()
        
        for finding in findings:
            if finding in used:
                continue
                
            # Find similar findings
            similar = [finding]
            used.add(finding)
            
            for other in findings:
                if other in used:
                    continue
                    
                # Simple similarity check (can be enhanced with NLP)
                if self._are_similar(finding, other):
                    similar.append(other)
                    used.add(other)
                    
            groups.append(similar)
            
        return groups
        
    def _are_similar(self, f1: ResearchFinding, f2: ResearchFinding) -> bool:
        """Check if two findings are similar.
        
        Args:
            f1: First finding
            f2: Second finding
            
        Returns:
            True if findings are similar
        """
        # Simple similarity based on key points overlap
        points1 = set(point.lower() for point in f1.key_points)
        points2 = set(point.lower() for point in f2.key_points)
        
        if not points1 or not points2:
            return False
            
        # If more than 50% of key points overlap
        overlap = len(points1.intersection(points2))
        total_points = len(points1.union(points2))
        
        return overlap / total_points > 0.5
        
    def _find_group_conflicts(self, group: list[ResearchFinding]) -> list[str]:
        """Find conflicts within a content group.
        
        Args:
            group: Group of similar findings
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        # Check for conflicting key points
        all_points = []
        for finding in group:
            all_points.extend(finding.key_points)
            
        # Find contradictory points
        point_counts = Counter(point.lower() for point in all_points)
        
        for point, count in point_counts.items():
            if count > 1:
                # Check if points have contradictory contexts
                conflicting_points = [
                    p for p in all_points 
                    if p.lower() != point and self._are_contradictory_points(point, p)
                ]
                
                if conflicting_points:
                    conflicts.append(f"Conflicting information about '{point}': {len(conflicting_points)} sources disagree")
                    
        return conflicts
        
    def _are_contradictory_points(self, point1: str, point2: str) -> bool:
        """Check if two key points contradict each other.
        
        Args:
            point1: First key point
            point2: Second key point
            
        Returns:
            True if points contradict
        """
        # Simplified contradiction check
        contradictions = [
            ("supported", "not supported"),
            ("required", "optional"),
            ("enabled", "disabled"),
            ("available", "unavailable"),
        ]
        
        p1_lower = point1.lower()
        p2_lower = point2.lower()
        
        for pos, neg in contradictions:
            if (pos in p1_lower and neg in p2_lower) or \
               (neg in p1_lower and pos in p2_lower):
                return True
                
        return False


class ResultSynthesizer:
    """Main result synthesizer with conflict resolution."""
    
    def __init__(self) -> None:
        """Initialize result synthesizer."""
        self.conflict_detector = ConflictDetector()
        self.confidence_synthesizer = ConfidenceWeightedSynthesizer()
        
    def synthesize_results(
        self,
        findings: list[ResearchFinding],
        original_query: str,
    ) -> dict[str, any]:
        """Synthesize research results with comprehensive analysis.
        
        Args:
            findings: List of research findings
            original_query: Original research query
            
        Returns:
            Comprehensive synthesis results
        """
        if not findings:
            return {
                "summary": f"No relevant information found for query: {original_query}",
                "key_points": [],
                "conflicts": [],
                "gaps": ["No sources found"],
                "recommendations": ["Try different search terms or search engines"],
                "confidence_level": "unknown",
                "citations": [],
            }
            
        # Detect conflicts
        conflicts = self.conflict_detector.find_conflicts(findings)
        
        # Generate confidence-weighted synthesis
        synthesis = self.confidence_synthesizer.synthesize_findings(findings)
        
        # Identify gaps
        gaps = self._identify_gaps(findings, original_query)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(findings, conflicts, gaps)
        
        # Format citations
        citations = self._format_citations(findings)
        
        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(findings)
        
        result = {
            "summary": synthesis["summary"],
            "key_points": synthesis["key_points"],
            "conflicts": conflicts,
            "gaps": gaps,
            "recommendations": recommendations,
            "confidence_level": overall_confidence,
            "citations": citations,
            "source_analysis": {
                "total_sources": len(findings),
                "source_types": list(set(f.source_classification.source_type.value for f in findings)),
                "high_confidence_count": len([f for f in findings if f.confidence_score >= 0.8]),
                "confidence_breakdown": synthesis["confidence_breakdown"],
                "consensus_analysis": synthesis["consensus_analysis"],
            }
        }
        
        _logger.info(
            "results_synthesized",
            query=original_query[:100],
            total_findings=len(findings),
            conflicts_count=len(conflicts),
            overall_confidence=overall_confidence,
        )
        
        return result
        
    def _identify_gaps(self, findings: list[ResearchFinding], query: str) -> list[str]:
        """Identify information gaps in research findings.
        
        Args:
            findings: List of research findings
            query: Original research query
            
        Returns:
            List of identified gaps
        """
        gaps = []
        
        # Check for missing source types
        source_types = set(f.source_classification.source_type.value for f in findings)
        
        expected_types = {
            "definition": [SourceType.OFFICIAL, SourceType.ACADEMIC],
            "tutorial": [SourceType.OFFICIAL, SourceType.REPUTABLE_COMMUNITY],
            "comparison": [SourceType.OFFICIAL, SourceType.TECH_PUBLICATION],
            "debug": [SourceType.REPUTABLE_COMMUNITY, SourceType.OFFICIAL],
        }
        
        # Determine query type (simplified)
        query_lower = query.lower()
        if any(word in query_lower for word in ["what is", "define", "meaning"]):
            query_type = "definition"
        elif any(word in query_lower for word in ["how to", "tutorial", "guide"]):
            query_type = "tutorial"
        elif any(word in query_lower for word in ["vs", "versus", "compare"]):
            query_type = "comparison"
        elif any(word in query_lower for word in ["why", "error", "bug", "issue"]):
            query_type = "debug"
        else:
            query_type = "general"
            
        # Check for missing expected source types
        if query_type in expected_types:
            missing_types = [t.value for t in expected_types[query_type] if t.value not in source_types]
            if missing_types:
                gaps.append(f"Missing {', '.join(missing_types)} source types")
                
        # Check for insufficient evidence
        if len(findings) < 3:
            gaps.append("Insufficient number of sources for comprehensive analysis")
            
        # Check for low confidence overall
        avg_confidence = sum(f.confidence_score for f in findings) / len(findings) if findings else 0
        if avg_confidence < 0.6:
            gaps.append("Low overall confidence in available sources")
            
        # Check for temporal gaps
        current_year = 2026
        has_recent_info = any(
            "2026" in f.content_summary or "2025" in f.content_summary
            for f in findings
        )
        
        if not has_recent_info and "latest" in query_lower:
            gaps.append("No recent information found")
            
        return list(set(gaps))  # Remove duplicates
        
    def _generate_recommendations(
        self,
        findings: list[ResearchFinding],
        conflicts: list[dict[str, any]],
        gaps: list[str],
    ) -> list[str]:
        """Generate recommendations based on analysis.
        
        Args:
            findings: Research findings
            conflicts: Detected conflicts
            gaps: Identified gaps
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Conflict-based recommendations
        if conflicts:
            recommendations.append("Verify conflicting information with additional authoritative sources")
            
        # Gap-based recommendations
        if gaps:
            if "official" in " ".join(gaps):
                recommendations.append("Consult official documentation for authoritative information")
            if "academic" in " ".join(gaps):
                recommendations.append("Search academic sources for research-backed information")
            if "Insufficient number" in " ".join(gaps):
                recommendations.append("Expand search to include more diverse sources")
                
        # Confidence-based recommendations
        avg_confidence = sum(f.confidence_score for f in findings) / len(findings) if findings else 0
        if avg_confidence < 0.6:
            recommendations.append("Verify information with additional high-confidence sources")
            
        # Source type recommendations
        source_types = set(f.source_classification.source_type.value for f in findings)
        if SourceType.OFFICIAL.value not in source_types:
            recommendations.append("Prioritize official documentation for critical information")
            
        # General recommendations
        if not recommendations:
            recommendations.append("Research appears complete; consider exploring related topics for additional context")
            
        return list(set(recommendations))  # Remove duplicates
        
    def _format_citations(self, findings: list[ResearchFinding]) -> list[str]:
        """Format citations for research findings.
        
        Args:
            findings: List of research findings
            
        Returns:
            List of formatted citations
        """
        citations = []
        
        # Sort by confidence (highest first)
        sorted_findings = sorted(findings, key=lambda f: f.confidence_score, reverse=True)
        
        for finding in sorted_findings:
            source_type = finding.source_classification.source_type.value
            confidence = finding.confidence_score
            
            # Format citation based on source type and confidence
            if source_type == SourceType.OFFICIAL.value and confidence >= 0.8:
                citation = f"[{finding.source_url}] (Official Documentation - High Confidence)"
            elif source_type == SourceType.ACADEMIC.value:
                citation = f"[{finding.source_url}] (Academic Research - {confidence:.1f} Confidence)"
            elif source_type == SourceType.REPUTABLE_COMMUNITY.value:
                citation = f"[{finding.source_url}] (Community Source - {confidence:.1f} Confidence)"
            else:
                citation = f"[{finding.source_url}] ({source_type.title()} - {confidence:.1f} Confidence)"
                
            citations.append(citation)
            
        return citations
        
    def _calculate_overall_confidence(self, findings: list[ResearchFinding]) -> str:
        """Calculate overall confidence level.
        
        Args:
            findings: List of research findings
            
        Returns:
            Overall confidence level string
        """
        if not findings:
            return "unknown"
            
        # Weight by source type
        weighted_scores = []
        for finding in findings:
            source_type = finding.source_classification.source_type
            
            # Source type weights
            type_weights = {
                SourceType.OFFICIAL: 1.0,
                SourceType.ACADEMIC: 0.9,
                SourceType.REPUTABLE_COMMUNITY: 0.8,
                SourceType.TECH_PUBLICATION: 0.7,
                SourceType.UNKNOWN_BLOG: 0.5,
                SourceType.SOCIAL: 0.3,
            }
            
            weight = type_weights.get(source_type, 0.5)
            weighted_score = finding.confidence_score * weight
            weighted_scores.append(weighted_score)
            
        # Calculate weighted average
        overall_score = sum(weighted_scores) / len(weighted_scores) if weighted_scores else 0
        
        # Convert to confidence level
        if overall_score >= 0.8:
            return "high"
        elif overall_score >= 0.6:
            return "medium"
        elif overall_score >= 0.4:
            return "low"
        else:
            return "unknown"


# Global synthesizer instance
_result_synthesizer: ResultSynthesizer | None = None


def get_result_synthesizer() -> ResultSynthesizer:
    """Get or create global result synthesizer instance.
    
    Returns:
        ResultSynthesizer singleton instance
    """
    global _result_synthesizer
    if _result_synthesizer is None:
        _result_synthesizer = ResultSynthesizer()
    return _result_synthesizer
