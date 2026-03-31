"""Multilingual Embedding Service for semantic context analysis.

Provides embedding generation and language detection capabilities
for multiple languages to support semantic search between sub-tasks.
"""

from __future__ import annotations

import asyncio

import numpy as np
from sentence_transformers import SentenceTransformer

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger

_logger = get_logger(__name__)


class MultilingualEmbeddingService:
    """Service for generating multilingual embeddings.
    
    Uses sentence-transformers models to generate embeddings
    that work across multiple languages for semantic search.
    """
    
    def __init__(self, model_name: str | None = None):
        """Initialize the multilingual embedding service.
        
        Args:
            model_name: Name of the sentence-transformers model to use.
                       Defaults to multilingual MiniLM model.
        """
        self.model_name = model_name or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        self.model: SentenceTransformer | None = None
        self.embedding_dimension = 384  # Default for MiniLM model
        self._lock = asyncio.Lock()
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the embedding model asynchronously."""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
                
            try:
                _logger.info("initializing_multilingual_embeddings", model=self.model_name)
                
                # Load model in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    None, 
                    lambda: SentenceTransformer(self.model_name)
                )
                
                self.embedding_dimension = self.model.get_sentence_embedding_dimension()
                self._initialized = True
                
                _logger.info(
                    "multilingual_embeddings_initialized", 
                    model=self.model_name,
                    dimension=self.embedding_dimension
                )
                
            except Exception as exc:
                _logger.error("failed_to_initialize_embeddings", error=str(exc))
                raise RuntimeError(f"Failed to initialize embedding model: {exc}")
    
    async def generate_embedding(
        self, 
        text: str, 
        language: str = "auto"
    ) -> list[float]:
        """Generate embedding for the given text.
        
        Args:
            text: Text to generate embedding for
            language: Language code (auto-detect if "auto")
            
        Returns:
            List of float values representing the embedding
        """
        if not self._initialized:
            await self.initialize()
            
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * self.embedding_dimension
            
        try:
            # Detect language if needed
            if language == "auto":
                language = await self.detect_language(text)
            
            # Generate embedding in thread pool
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model.encode(
                    text,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
            )
            
            # Convert to list of floats
            return embedding.tolist()
            
        except Exception as exc:
            _logger.error("embedding_generation_failed", error=str(exc), text_length=len(text))
            # Return zero vector as fallback
            return [0.0] * self.embedding_dimension
    
    async def generate_batch_embeddings(
        self,
        texts: list[str],
        language: str = "auto"
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to generate embeddings for
            language: Language code for all texts
            
        Returns:
            List of embedding vectors
        """
        if not self._initialized:
            await self.initialize()
            
        if not texts:
            return []
            
        try:
            # Filter out empty texts
            valid_texts = [text for text in texts if text and text.strip()]
            
            if not valid_texts:
                # Return zero vectors for all empty texts
                return [[0.0] * self.embedding_dimension] * len(texts)
            
            # Generate batch embeddings
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(
                    valid_texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    batch_size=32
                )
            )
            
            # Convert to list and handle empty texts
            result = []
            text_idx = 0
            for text in texts:
                if text and text.strip():
                    result.append(embeddings[text_idx].tolist())
                    text_idx += 1
                else:
                    result.append([0.0] * self.embedding_dimension)
                    
            return result
            
        except Exception as exc:
            _logger.error("batch_embedding_generation_failed", error=str(exc), texts_count=len(texts))
            # Return zero vectors as fallback
            return [[0.0] * self.embedding_dimension] * len(texts)
    
    async def detect_language(self, text: str) -> str:
        """Detect the language of the given text.
        
        Args:
            text: Text to detect language for
            
        Returns:
            Language code (e.g., 'en', 'pt', 'es')
        """
        # Simple language detection based on common patterns
        # In a production environment, you might want to use a proper language detection library
        
        if not text or not text.strip():
            return "unknown"
            
        # Check for common Portuguese indicators
        portuguese_indicators = [
            " ção", " ões", " ão", " é ", " ê ", " á ", " ó ", " í ", " ú ",
            " que ", " para ", " com ", " como ", " mais ", " muito ",
            " não ", " sim ", " ou ", " mas ", " por ", " sobre "
        ]
        
        # Check for common Spanish indicators  
        spanish_indicators = [
            "ción", "ón", " el ", " la ", " los ", " las ", " que ",
            " para ", " con ", " como ", " más ", " muy ", " no ",
            " sí ", " o ", " pero ", " por ", " sobre "
        ]
        
        text_lower = text.lower()
        
        # Count indicators for each language
        pt_score = sum(1 for indicator in portuguese_indicators if indicator in text_lower)
        es_score = sum(1 for indicator in spanish_indicators if indicator in text_lower)
        
        # Default to English if no strong indicators
        if pt_score > es_score and pt_score > 2:
            return "pt"
        elif es_score > pt_score and es_score > 2:
            return "es"
        else:
            return "en"
    
    async def calculate_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure result is in [0, 1] range
            return float(max(0.0, min(1.0, similarity)))
            
        except Exception as exc:
            _logger.error("similarity_calculation_failed", error=str(exc))
            return 0.0
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        return self.embedding_dimension


# Global instance for singleton pattern
_embedding_service: MultilingualEmbeddingService | None = None


async def get_multilingual_embedding_service() -> MultilingualEmbeddingService:
    """Get or create the global multilingual embedding service instance."""
    global _embedding_service
    
    if _embedding_service is None:
        settings = get_settings()
        model_name = getattr(settings, 'multilingual_embedding_model', None)
        _embedding_service = MultilingualEmbeddingService(model_name)
        await _embedding_service.initialize()
        
    return _embedding_service
