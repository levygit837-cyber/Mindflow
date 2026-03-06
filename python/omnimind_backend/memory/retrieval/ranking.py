"""Result ranking algorithms for memory retrieval."""

from typing import Any, Dict, List, Optional

from omnimind_backend.infra.logging import get_logger
from omnimind_backend.memory.embeddings.similarity import cosine_similarity

_logger = get_logger(__name__)


class ResultRanker:
    """Ranking algorithms for memory retrieval results."""
    
    def __init__(self):
        self.logger = _logger
    
    def rank_by_relevance(
        self,
        results: List[Dict[str, Any]],
        query_embedding: Optional[List[float]] = None
    ) -> List[Dict[str, Any]]:
        """Rank results by relevance score."""
        try:
            # Sort by existing score if available
            if all("score" in result for result in results):
                return sorted(results, key=lambda x: x["score"], reverse=True)
            
            # If no scores, calculate based on content similarity
            if query_embedding:
                return self.rank_by_semantic_similarity(results, query_embedding)
            
            # Fallback: rank by recency
            return self.rank_by_recency(results)
            
        except Exception as exc:
            self.logger.error(f"Failed to rank results: {str(exc)}")
            return results
    
    def rank_by_semantic_similarity(
        self,
        results: List[Dict[str, Any]],
        query_embedding: List[float]
    ) -> List[Dict[str, Any]]:
        """Rank results by semantic similarity to query."""
        ranked_results = []
        
        for result in results:
            content = result.get("content", "")
            if content and "embedding" in result:
                result_embedding = result["embedding"]
                similarity = cosine_similarity(query_embedding, result_embedding)
                
                ranked_result = result.copy()
                ranked_result["similarity_score"] = similarity
                ranked_results.append(ranked_result)
            else:
                # No embedding available, assign low score
                ranked_result = result.copy()
                ranked_result["similarity_score"] = 0.0
                ranked_results.append(ranked_result)
        
        return sorted(ranked_results, key=lambda x: x["similarity_score"], reverse=True)
    
    def rank_by_recency(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rank results by recency (most recent first)."""
        return sorted(
            results,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
    
    def rank_by_token_count(
        self,
        results: List[Dict[str, Any]],
        ascending: bool = False
    ) -> List[Dict[str, Any]]:
        """Rank results by token count."""
        return sorted(
            results,
            key=lambda x: x.get("token_count", 0),
            reverse=not ascending
        )
    
    def diversify_results(
        self,
        results: List[Dict[str, Any]],
        diversity_threshold: float = 0.8,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Diversify results to avoid redundancy."""
        if not results:
            return []
        
        diversified = [results[0]]  # Always include the top result
        
        for result in results[1:]:
            if len(diversified) >= max_results:
                break
            
            # Check similarity with already included results
            is_too_similar = False
            for included in diversified:
                if self._calculate_result_similarity(result, included) > diversity_threshold:
                    is_too_similar = True
                    break
            
            if not is_too_similar:
                diversified.append(result)
        
        return diversified
    
    def _calculate_result_similarity(
        self,
        result1: Dict[str, Any],
        result2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two results."""
        # Simple similarity based on content overlap
        content1 = result1.get("content", "").lower()
        content2 = result2.get("content", "").lower()
        
        # Jaccard similarity
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    def apply_boosting(
        self,
        results: List[Dict[str, Any]],
        boost_factors: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Apply boosting factors to results."""
        boosted_results = []
        
        for result in results:
            boosted_result = result.copy()
            base_score = boosted_result.get("score", 0.0)
            
            # Apply boost factors
            total_boost = 1.0
            for factor, boost_value in boost_factors.items():
                if result.get(factor):
                    total_boost *= boost_value
            
            boosted_result["boosted_score"] = base_score * total_boost
            boosted_results.append(boosted_result)
        
        # Re-sort by boosted score
        return sorted(boosted_results, key=lambda x: x["boosted_score"], reverse=True)
