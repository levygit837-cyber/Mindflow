"""Hybrid embedding service combining multiple approaches.

Combines NLP techniques with optional model-based embeddings
for optimal performance and accuracy.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union, Tuple
import asyncio
import numpy as np

from mindflow_backend.infra.logging import get_logger
from .nlp_embedding_service import (
    EmbeddingConfig,
    EmbeddingMethod,
    BaseEmbeddingGenerator,
    NLPEmbeddingService,
)

_logger = get_logger(__name__)


class HybridEmbeddingService:
    """Hybrid embedding service combining multiple methods."""
    
    def __init__(
        self,
        primary_method: EmbeddingMethod = EmbeddingMethod.TFIDF,
        secondary_method: Optional[EmbeddingMethod] = None,
        weights: Optional[List[float]] = None,
        fallback_method: Optional[EmbeddingMethod] = None,
        **config_kwargs: Any,
    ) -> None:
        """Initialize hybrid embedding service.
        
        Args:
            primary_method: Primary embedding method.
            secondary_method: Secondary embedding method for hybrid.
            weights: Weights for combining methods [primary, secondary].
            fallback_method: Fallback method if primary fails.
            **config_kwargs: Additional configuration.
        """
        self.primary_method = primary_method
        self.secondary_method = secondary_method
        self.fallback_method = fallback_method or EmbeddingMethod.TFIDF
        self.weights = weights or [0.7, 0.3]
        
        # Create configurations
        self.primary_config = EmbeddingConfig(
            method=primary_method,
            **config_kwargs.get('primary_config', {})
        )
        
        self.secondary_config = EmbeddingConfig(
            method=secondary_method,
            **config_kwargs.get('secondary_config', {})
        ) if secondary_method else None
        
        self.fallback_config = EmbeddingConfig(
            method=self.fallback_method,
            **config_kwargs.get('fallback_config', {})
        )
        
        # Initialize services
        self.primary_service: Optional[NLPEmbeddingService] = None
        self.secondary_service: Optional[NLPEmbeddingService] = None
        self.fallback_service: Optional[NLPEmbeddingService] = None
        
        self.is_fitted = False
    
    async def initialize(self) -> None:
        """Initialize all embedding services."""
        try:
            # Initialize primary service
            self.primary_service = NLPEmbeddingService(self.primary_config)
            _logger.info(f"Primary service initialized: {self.primary_method}")
            
            # Initialize secondary service if specified
            if self.secondary_method:
                self.secondary_service = NLPEmbeddingService(self.secondary_config)
                _logger.info(f"Secondary service initialized: {self.secondary_method}")
            
            # Initialize fallback service
            self.fallback_service = NLPEmbeddingService(self.fallback_config)
            _logger.info(f"Fallback service initialized: {self.fallback_method}")
            
        except Exception as e:
            _logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def fit(self, texts: List[str]) -> None:
        """Fit all embedding services.
        
        Args:
            texts: Training texts.
        """
        if not self.primary_service:
            await self.initialize()
        
        # Fit primary service
        try:
            await self.primary_service.fit(texts)
            _logger.info(f"Primary service fitted: {self.primary_method}")
        except Exception as e:
            _logger.warning(f"Primary service failed to fit: {e}")
            if self.fallback_service:
                await self.fallback_service.fit(texts)
                _logger.info(f"Fallback service fitted: {self.fallback_method}")
        
        # Fit secondary service if available
        if self.secondary_service:
            try:
                await self.secondary_service.fit(texts)
                _logger.info(f"Secondary service fitted: {self.secondary_method}")
            except Exception as e:
                _logger.warning(f"Secondary service failed to fit: {e}")
                self.secondary_service = None
        
        self.is_fitted = True
    
    async def generate_embeddings(
        self,
        texts: Union[str, List[str]],
        use_hybrid: bool = True,
    ) -> List[List[float]]:
        """Generate embeddings using hybrid approach.
        
        Args:
            texts: Text(s) to embed.
            use_hybrid: Whether to use hybrid combination.
            
        Returns:
            Generated embeddings.
        """
        if not self.is_fitted:
            raise RuntimeError("Service not fitted. Call fit() first.")
        
        if isinstance(texts, str):
            texts = [texts]
        
        if use_hybrid and self.secondary_service:
            return await self._generate_hybrid_embeddings(texts)
        else:
            return await self._generate_primary_embeddings(texts)
    
    async def _generate_primary_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using primary service.
        
        Args:
            texts: Texts to embed.
            
        Returns:
            Generated embeddings.
        """
        try:
            return await self.primary_service.generate_embeddings(texts)
        except Exception as e:
            _logger.warning(f"Primary service failed: {e}, using fallback")
            return await self.fallback_service.generate_embeddings(texts)
    
    async def _generate_hybrid_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate hybrid embeddings combining multiple methods.
        
        Args:
            texts: Texts to embed.
            
        Returns:
            Combined embeddings.
        """
        # Get primary embeddings
        try:
            primary_embeddings = await self.primary_service.generate_embeddings(texts)
        except Exception as e:
            _logger.warning(f"Primary service failed: {e}")
            return await self._generate_primary_embeddings(texts)
        
        # Get secondary embeddings if available
        if self.secondary_service:
            try:
                secondary_embeddings = await self.secondary_service.generate_embeddings(texts)
                return self._combine_embeddings(primary_embeddings, secondary_embeddings)
            except Exception as e:
                _logger.warning(f"Secondary service failed: {e}")
        
        return primary_embeddings
    
    def _combine_embeddings(
        self,
        primary_embeddings: List[List[float]],
        secondary_embeddings: List[List[float]],
    ) -> List[List[float]]:
        """Combine embeddings from multiple methods.
        
        Args:
            primary_embeddings: Primary method embeddings.
            secondary_embeddings: Secondary method embeddings.
            
        Returns:
            Combined embeddings.
        """
        combined = []
        
        for i in range(len(primary_embeddings)):
            primary_vec = np.array(primary_embeddings[i])
            secondary_vec = np.array(secondary_embeddings[i])
            
            # Weighted combination
            if len(self.weights) >= 2:
                combined_vec = (
                    self.weights[0] * primary_vec +
                    self.weights[1] * secondary_vec
                )
            else:
                combined_vec = 0.7 * primary_vec + 0.3 * secondary_vec
            
            # Normalize
            norm = np.linalg.norm(combined_vec)
            if norm > 0:
                combined_vec = combined_vec / norm
            
            combined.append(combined_vec.tolist())
        
        return combined
    
    async def similarity_search(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
        use_hybrid: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search for most similar texts using hybrid approach.
        
        Args:
            query: Query text.
            candidates: Candidate texts.
            top_k: Number of top results.
            use_hybrid: Whether to use hybrid search.
            
        Returns:
            Search results with similarity scores.
        """
        if not self.is_fitted:
            raise RuntimeError("Service not fitted")
        
        # Generate embeddings
        query_embedding = await self.generate_embeddings(query, use_hybrid=use_hybrid)
        candidate_embeddings = await self.generate_embeddings(candidates, use_hybrid=use_hybrid)
        
        # Calculate similarities
        similarities = await self._calculate_similarities(
            query_embedding[0],
            candidate_embeddings
        )
        
        # Sort and return results
        results = []
        for i, similarity in enumerate(similarities):
            results.append({
                "text": candidates[i],
                "similarity": similarity,
                "index": i,
                "method": "hybrid" if use_hybrid and self.secondary_service else "primary",
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    
    async def _calculate_similarities(
        self,
        query: List[float],
        candidates: List[List[float]],
    ) -> List[float]:
        """Calculate cosine similarities.
        
        Args:
            query: Query embedding.
            candidates: Candidate embeddings.
            
        Returns:
            Similarity scores.
        """
        loop = asyncio.get_event_loop()
        
        query_array = np.array([query])
        candidates_array = np.array(candidates)
        
        # Use numpy for efficient calculation
        similarities = await loop.run_in_executor(
            None,
            np.dot,
            query_array,
            candidates_array.T
        )
        
        return similarities[0].tolist()
    
    def get_dimension(self) -> int:
        """Get embedding dimension.
        
        Returns:
            Embedding dimension.
        """
        if not self.is_fitted:
            raise RuntimeError("Service not fitted")
        
        if self.secondary_service:
            # Return combined dimension for hybrid
            primary_dim = self.primary_service.get_dimension()
            secondary_dim = self.secondary_service.get_dimension()
            return primary_dim + secondary_dim
        else:
            return self.primary_service.get_dimension()
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive service information.
        
        Returns:
            Service configuration and status.
        """
        info = {
            "primary_method": self.primary_method.value,
            "secondary_method": self.secondary_method.value if self.secondary_method else None,
            "fallback_method": self.fallback_method.value,
            "weights": self.weights,
            "is_fitted": self.is_fitted,
            "dimension": self.get_dimension() if self.is_fitted else None,
        }
        
        # Add service-specific info
        if self.primary_service and self.is_fitted:
            info["primary_service"] = await self.primary_service.get_service_info()
        
        if self.secondary_service and self.is_fitted:
            info["secondary_service"] = await self.secondary_service.get_service_info()
        
        if self.fallback_service and self.is_fitted:
            info["fallback_service"] = await self.fallback_service.get_service_info()
        
        return info
    
    async def benchmark_methods(
        self,
        test_texts: List[str],
        query_text: str,
    ) -> Dict[str, Any]:
        """Benchmark different embedding methods.
        
        Args:
            test_texts: Test documents.
            query_text: Query for similarity search.
            
        Returns:
            Benchmark results.
        """
        if not self.is_fitted:
            raise RuntimeError("Service not fitted")
        
        results = {}
        
        # Test primary method
        try:
            start_time = asyncio.get_event_loop().time()
            primary_results = await self.primary_service.similarity_search(
                query_text, test_texts, top_k=5
            )
            primary_time = asyncio.get_event_loop().time() - start_time
            
            results["primary"] = {
                "method": self.primary_method.value,
                "results": primary_results,
                "time": primary_time,
                "dimension": self.primary_service.get_dimension(),
            }
        except Exception as e:
            results["primary"] = {"error": str(e)}
        
        # Test secondary method if available
        if self.secondary_service:
            try:
                start_time = asyncio.get_event_loop().time()
                secondary_results = await self.secondary_service.similarity_search(
                    query_text, test_texts, top_k=5
                )
                secondary_time = asyncio.get_event_loop().time() - start_time
                
                results["secondary"] = {
                    "method": self.secondary_method.value,
                    "results": secondary_results,
                    "time": secondary_time,
                    "dimension": self.secondary_service.get_dimension(),
                }
            except Exception as e:
                results["secondary"] = {"error": str(e)}
        
        # Test hybrid method
        try:
            start_time = asyncio.get_event_loop().time()
            hybrid_results = await self.similarity_search(
                query_text, test_texts, top_k=5, use_hybrid=True
            )
            hybrid_time = asyncio.get_event_loop().time() - start_time
            
            results["hybrid"] = {
                "method": "hybrid",
                "results": hybrid_results,
                "time": hybrid_time,
                "dimension": self.get_dimension(),
            }
        except Exception as e:
            results["hybrid"] = {"error": str(e)}
        
        return results


def create_hybrid_service(
    primary_method: EmbeddingMethod = EmbeddingMethod.TFIDF,
    secondary_method: Optional[EmbeddingMethod] = EmbeddingMethod.SENTENCE_TRANSFORMER,
    weights: Optional[List[float]] = None,
    **kwargs: Any,
) -> HybridEmbeddingService:
    """Create hybrid embedding service.
    
    Args:
        primary_method: Primary embedding method.
        secondary_method: Secondary embedding method.
        weights: Combination weights.
        **kwargs: Additional configuration.
        
    Returns:
        Configured hybrid embedding service.
    """
    return HybridEmbeddingService(
        primary_method=primary_method,
        secondary_method=secondary_method,
        weights=weights,
        **kwargs
    )
