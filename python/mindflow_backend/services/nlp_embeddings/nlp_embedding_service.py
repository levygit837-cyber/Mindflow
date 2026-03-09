"""NLP Embedding Service for MindFlow.

Provides flexible embedding generation using NLP techniques,
local models, or cloud models based on configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum
import asyncio
from datetime import datetime

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class EmbeddingMethod(str, Enum):
    """Available embedding generation methods."""
    TFIDF = "tfidf"
    BM25 = "bm25"
    SENTENCE_TRANSFORMER = "sentence_transformer"
    LOCAL_MODEL = "local_model"
    CLOUD_MODEL = "cloud_model"
    HYBRID = "hybrid"


class EmbeddingConfig:
    """Configuration for embedding generation."""
    
    def __init__(
        self,
        method: EmbeddingMethod = EmbeddingMethod.TFIDF,
        model_name: Optional[str] = None,
        max_features: int = 10000,
        min_df: int = 1,
        max_df: float = 0.95,
        ngram_range: tuple = (1, 2),
        normalize: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize embedding configuration.
        
        Args:
            method: Embedding generation method.
            model_name: Model name for transformer-based methods.
            max_features: Maximum number of features for TF-IDF.
            min_df: Minimum document frequency.
            max_df: Maximum document frequency.
            ngram_range: N-gram range for TF-IDF.
            normalize: Whether to normalize embeddings.
            **kwargs: Additional method-specific parameters.
        """
        self.method = method
        self.model_name = model_name
        self.max_features = max_features
        self.min_df = min_df
        self.max_df = max_df
        self.ngram_range = ngram_range
        self.normalize = normalize
        self.kwargs = kwargs


class BaseEmbeddingGenerator(ABC):
    """Base class for embedding generators."""
    
    @abstractmethod
    async def fit(self, texts: List[str]) -> None:
        """Fit the embedding model on texts."""
        ...
    
    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        ...
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        ...
    
    @abstractmethod
    async def similarity(self, query: List[float], candidates: List[List[float]]) -> List[float]:
        """Calculate similarity scores."""
        ...


class TfidfEmbeddingGenerator(BaseEmbeddingGenerator):
    """TF-IDF based embedding generator."""
    
    def __init__(self, config: EmbeddingConfig) -> None:
        """Initialize TF-IDF embedding generator.
        
        Args:
            config: Embedding configuration.
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for TF-IDF embeddings")
        
        self.config = config
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.is_fitted = False
    
    async def fit(self, texts: List[str]) -> None:
        """Fit TF-IDF vectorizer on texts.
        
        Args:
            texts: Training texts.
        """
        loop = asyncio.get_event_loop()
        
        self.vectorizer = TfidfVectorizer(
            max_features=self.config.max_features,
            min_df=self.config.min_df,
            max_df=self.config.max_df,
            ngram_range=self.config.ngram_range,
            stop_words='english' if self.config.kwargs.get('remove_stopwords', True) else None,
        )
        
        await loop.run_in_executor(
            None,
            self.vectorizer.fit_transform,
            texts
        )
        
        self.is_fitted = True
        _logger.info(f"TF-IDF fitted on {len(texts)} texts with {len(self.vectorizer.vocabulary_)} features")
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate TF-IDF embeddings.
        
        Args:
            texts: Texts to embed.
            
        Returns:
            List of embedding vectors.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            self.vectorizer.transform,
            texts
        )
        
        # Convert sparse matrix to dense and normalize
        dense_embeddings = embeddings.toarray()
        
        if self.config.normalize:
            norms = np.linalg.norm(dense_embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Avoid division by zero
            dense_embeddings = dense_embeddings / norms
        
        return dense_embeddings.tolist()
    
    def get_dimension(self) -> int:
        """Get TF-IDF embedding dimension."""
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        return len(self.vectorizer.vocabulary_)
    
    async def similarity(self, query: List[float], candidates: List[List[float]]) -> List[float]:
        """Calculate cosine similarity.
        
        Args:
            query: Query embedding.
            candidates: Candidate embeddings.
            
        Returns:
            Similarity scores.
        """
        loop = asyncio.get_event_loop()
        
        query_array = np.array([query])
        candidates_array = np.array(candidates)
        
        similarities = await loop.run_in_executor(
            None,
            cosine_similarity,
            query_array,
            candidates_array
        )
        
        return similarities[0].tolist()


class SentenceTransformerEmbeddingGenerator(BaseEmbeddingGenerator):
    """Sentence Transformer based embedding generator."""
    
    def __init__(self, config: EmbeddingConfig) -> None:
        """Initialize sentence transformer generator.
        
        Args:
            config: Embedding configuration.
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers is required for transformer embeddings")
        
        self.config = config
        self.model: Optional[SentenceTransformer] = None
        self.model_name = config.model_name or "all-MiniLM-L6-v2"
    
    async def fit(self, texts: List[str]) -> None:
        """Load sentence transformer model.
        
        Args:
            texts: Training texts (not used for transformers).
        """
        loop = asyncio.get_event_loop()
        
        self.model = await loop.run_in_executor(
            None,
            SentenceTransformer,
            self.model_name
        )
        
        _logger.info(f"Sentence transformer loaded: {self.model_name}")
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate transformer embeddings.
        
        Args:
            texts: Texts to embed.
            
        Returns:
            List of embedding vectors.
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call fit() first.")
        
        loop = asyncio.get_event_loop()
        
        embeddings = await loop.run_in_executor(
            None,
            self.model.encode,
            texts,
            True,  # convert_to_numpy
            True,  # normalize_embeddings
        )
        
        return embeddings.tolist()
    
    def get_dimension(self) -> int:
        """Get embedding dimension."""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Get dimension by encoding a test sentence
        test_embedding = self.model.encode("test", convert_to_numpy=True)
        return len(test_embedding)
    
    async def similarity(self, query: List[float], candidates: List[List[float]]) -> List[float]:
        """Calculate cosine similarity.
        
        Args:
            query: Query embedding.
            candidates: Candidate embeddings.
            
        Returns:
            Similarity scores.
        """
        loop = asyncio.get_event_loop()
        
        query_array = np.array([query])
        candidates_array = np.array(candidates)
        
        similarities = await loop.run_in_executor(
            None,
            cosine_similarity,
            query_array,
            candidates_array
        )
        
        return similarities[0].tolist()


class HybridEmbeddingGenerator(BaseEmbeddingGenerator):
    """Hybrid embedding generator combining multiple methods."""
    
    def __init__(self, config: EmbeddingConfig) -> None:
        """Initialize hybrid embedding generator.
        
        Args:
            config: Embedding configuration.
        """
        self.config = config
        self.generators: List[BaseEmbeddingGenerator] = []
        self.weights = config.kwargs.get('weights', [0.5, 0.5])
        
        # Initialize generators based on configuration
        methods = config.kwargs.get('methods', [EmbeddingMethod.TFIDF, EmbeddingMethod.SENTENCE_TRANSFORMER])
        
        for method in methods:
            if method == EmbeddingMethod.TFIDF:
                self.generators.append(TfidfEmbeddingGenerator(config))
            elif method == EmbeddingMethod.SENTENCE_TRANSFORMER:
                self.generators.append(SentenceTransformerEmbeddingGenerator(config))
    
    async def fit(self, texts: List[str]) -> None:
        """Fit all generators.
        
        Args:
            texts: Training texts.
        """
        for generator in self.generators:
            await generator.fit(texts)
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate hybrid embeddings.
        
        Args:
            texts: Texts to embed.
            
        Returns:
            Combined embedding vectors.
        """
        all_embeddings = []
        
        for i, generator in enumerate(self.generators):
            embeddings = await generator.generate_embeddings(texts)
            all_embeddings.append((embeddings, self.weights[i]))
        
        # Combine embeddings with weights
        combined_embeddings = []
        for text_idx in range(len(texts)):
            combined_vector = []
            for embeddings, weight in all_embeddings:
                vector = embeddings[text_idx]
                if combined_vector:
                    # Concatenate weighted vectors
                    combined_vector.extend([v * weight for v in vector])
                else:
                    combined_vector = [v * weight for v in vector]
            combined_embeddings.append(combined_vector)
        
        return combined_embeddings
    
    def get_dimension(self) -> int:
        """Get combined embedding dimension."""
        total_dim = sum(gen.get_dimension() for gen in self.generators)
        return total_dim
    
    async def similarity(self, query: List[float], candidates: List[List[float]]) -> List[float]:
        """Calculate cosine similarity for hybrid embeddings.
        
        Args:
            query: Query embedding.
            candidates: Candidate embeddings.
            
        Returns:
            Similarity scores.
        """
        loop = asyncio.get_event_loop()
        
        query_array = np.array([query])
        candidates_array = np.array(candidates)
        
        similarities = await loop.run_in_executor(
            None,
            cosine_similarity,
            query_array,
            candidates_array
        )
        
        return similarities[0].tolist()


class NLPEmbeddingService:
    """Flexible NLP embedding service supporting multiple methods."""
    
    def __init__(self, config: EmbeddingConfig) -> None:
        """Initialize NLP embedding service.
        
        Args:
            config: Embedding configuration.
        """
        self.config = config
        self.generator = self._create_generator(config)
        self.is_fitted = False
    
    def _create_generator(self, config: EmbeddingConfig) -> BaseEmbeddingGenerator:
        """Create appropriate embedding generator.
        
        Args:
            config: Embedding configuration.
            
        Returns:
            Embedding generator instance.
        """
        if config.method == EmbeddingMethod.TFIDF:
            return TfidfEmbeddingGenerator(config)
        elif config.method == EmbeddingMethod.SENTENCE_TRANSFORMER:
            return SentenceTransformerEmbeddingGenerator(config)
        elif config.method == EmbeddingMethod.HYBRID:
            return HybridEmbeddingGenerator(config)
        else:
            raise ValueError(f"Unsupported embedding method: {config.method}")
    
    async def fit(self, texts: List[str]) -> None:
        """Fit the embedding model.
        
        Args:
            texts: Training texts.
        """
        await self.generator.fit(texts)
        self.is_fitted = True
        _logger.info(f"Embedding service fitted with method: {self.config.method}")
    
    async def generate_embeddings(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """Generate embeddings for texts.
        
        Args:
            texts: Single text or list of texts.
            
        Returns:
            List of embedding vectors.
        """
        if not self.is_fitted:
            raise RuntimeError("Service not fitted. Call fit() first.")
        
        if isinstance(texts, str):
            texts = [texts]
        
        return await self.generator.generate_embeddings(texts)
    
    def get_dimension(self) -> int:
        """Get embedding dimension.
        
        Returns:
            Embedding dimension.
        """
        if not self.is_fitted:
            raise RuntimeError("Service not fitted")
        return self.generator.get_dimension()
    
    async def similarity_search(
        self,
        query: str,
        candidates: List[str],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search for most similar texts.
        
        Args:
            query: Query text.
            candidates: Candidate texts.
            top_k: Number of top results.
            
        Returns:
            List of similarity results.
        """
        if not self.is_fitted:
            raise RuntimeError("Service not fitted")
        
        # Generate embeddings
        query_embedding = await self.generate_embeddings(query)
        candidate_embeddings = await self.generate_embeddings(candidates)
        
        # Calculate similarities
        similarities = await self.generator.similarity(query_embedding[0], candidate_embeddings)
        
        # Sort by similarity
        results = []
        for i, similarity in enumerate(similarities):
            results.append({
                "text": candidates[i],
                "similarity": similarity,
                "index": i,
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        return results[:top_k]
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information.
        
        Returns:
            Service configuration and status.
        """
        return {
            "method": self.config.method.value,
            "model_name": getattr(self.config, 'model_name', None),
            "is_fitted": self.is_fitted,
            "dimension": self.get_dimension() if self.is_fitted else None,
            "config": {
                "max_features": self.config.max_features,
                "ngram_range": self.config.ngram_range,
                "normalize": self.config.normalize,
            }
        }


def create_embedding_service(
    method: EmbeddingMethod = EmbeddingMethod.TFIDF,
    model_name: Optional[str] = None,
    **kwargs: Any,
) -> NLPEmbeddingService:
    """Create embedding service with configuration.
    
    Args:
        method: Embedding generation method.
        model_name: Model name for transformer methods.
        **kwargs: Additional configuration parameters.
        
    Returns:
        Configured embedding service.
    """
    config = EmbeddingConfig(
        method=method,
        model_name=model_name,
        **kwargs
    )
    
    return NLPEmbeddingService(config)
