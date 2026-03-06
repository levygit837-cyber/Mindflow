"""Embedding service for generating and managing text embeddings.

This service provides multilingual embedding generation with support for
multiple models, caching, and optimization for different task types.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from functools import lru_cache
import hashlib
import math
import os
import re
from datetime import datetime, UTC
import asyncio

from mindflow_backend.infra.config import get_settings
from mindflow_backend.infra.logging import get_logger
from mindflow_backend.services.interfaces.base_interfaces import BaseAbstractService
from mindflow_backend.services.interfaces.context_interfaces import EmbeddingServiceInterface


class EmbeddingService(BaseAbstractService, EmbeddingServiceInterface):
    """Service for generating and managing text embeddings.
    
    This service provides multilingual embedding generation with support for
    multiple models, caching, and task-specific optimization.
    """
    
    def __init__(self) -> None:
        """Initialize embedding service with model configuration."""
        super().__init__()
        self.settings = get_settings()
        
        # Embedding model configuration
        self.default_model = getattr(self.settings, 'embedding_model', 'text-embedding-004')
        self.default_dimensions = getattr(self.settings, 'embedding_dimensions', 768)
        
        # Cache for embeddings
        self._embedding_cache: Dict[str, List[float]] = {}
        self._cache_size_limit = 10000
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Supported languages
        self._supported_languages = [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
            "ar", "hi", "th", "vi", "tr", "pl", "nl", "sv", "da", "no"
        ]
        
        # Task-specific optimizations
        self._task_optimizations = {
            "semantic_search": {"weight_recent": 1.0, "weight_keywords": 0.8},
            "classification": {"weight_recent": 0.9, "weight_keywords": 1.0},
            "clustering": {"weight_recent": 0.8, "weight_keywords": 0.9},
            "retrieval": {"weight_recent": 1.0, "weight_keywords": 0.7}
        }
    
    def _get_logger(self) -> Any:
        """Get logger instance for this service."""
        return get_logger(__name__)
    
    async def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        language: Optional[str] = None
    ) -> List[float]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            model: Optional model name
            language: Optional language code
            
        Returns:
            Embedding vector
        """
        self.log_operation(
            "generate_embedding",
            text_length=len(text),
            model=model or self.default_model
        )
        
        try:
            # Check cache first
            cache_key = self._get_cache_key(text, model, language)
            if cache_key in self._embedding_cache:
                self._cache_hits += 1
                return self._embedding_cache[cache_key]
            
            self._cache_misses += 1
            
            # Detect language if not provided
            if language is None:
                language = await self.detect_language(text)
            
            # Generate embedding using appropriate method
            if model and model.startswith("text-embedding"):
                embedding = await self._generate_llm_embedding(text, model)
            else:
                # Fallback to hash-based embedding
                embedding = self._generate_hash_embedding(text, self.default_dimensions)
            
            # Cache the result
            await self._cache_embedding(cache_key, embedding)
            
            return embedding
            
        except Exception as exc:
            self._logger.error(f"Error generating embedding: {str(exc)}")
            # Fallback to hash embedding
            return self._generate_hash_embedding(text, self.default_dimensions)
    
    async def generate_batch_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 32
    ) -> List[List[float]]:
        """Generate embeddings for batch of texts.
        
        Args:
            texts: List of texts to embed
            model: Optional model name
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        self.log_operation("generate_batch_embeddings", text_count=len(texts), batch_size=batch_size)
        
        try:
            all_embeddings = []
            
            # Process in batches
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                # Generate embeddings for batch
                batch_tasks = [
                    self.generate_embedding(text, model)
                    for text in batch
                ]
                
                batch_embeddings = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Handle exceptions
                for j, embedding in enumerate(batch_embeddings):
                    if isinstance(embedding, Exception):
                        self._logger.error(f"Batch embedding {i+j} failed: {str(embedding)}")
                        # Use fallback embedding
                        embedding = self._generate_hash_embedding(batch[j], self.default_dimensions)
                    
                    all_embeddings.append(embedding)
                
                # Small delay to prevent overwhelming the API
                if i + batch_size < len(texts):
                    await asyncio.sleep(0.1)
            
            return all_embeddings
            
        except Exception as exc:
            self._logger.error(f"Error generating batch embeddings: {str(exc)}")
            raise
    
    async def get_embedding_model_info(self, model: str) -> Dict[str, Any]:
        """Get embedding model information.
        
        Args:
            model: Model name
            
        Returns:
            Dictionary containing model information
        """
        self.log_operation("get_embedding_model_info", model=model)
        
        try:
            # Model information registry
            model_info = {
                "text-embedding-004": {
                    "name": "Google Text Embedding 004",
                    "dimensions": 768,
                    "max_input_length": 8192,
                    "languages": self._supported_languages,
                    "provider": "google",
                    "status": "active"
                },
                "text-embedding-multilingual": {
                    "name": "Multilingual Text Embedding",
                    "dimensions": 768,
                    "max_input_length": 8192,
                    "languages": self._supported_languages,
                    "provider": "google",
                    "status": "active"
                },
                "hash-fallback": {
                    "name": "Hash-based Fallback",
                    "dimensions": self.default_dimensions,
                    "max_input_length": 1000000,
                    "languages": ["all"],
                    "provider": "internal",
                    "status": "fallback"
                }
            }
            
            info = model_info.get(model, {
                "name": model,
                "dimensions": self.default_dimensions,
                "max_input_length": 8192,
                "languages": ["en"],
                "provider": "unknown",
                "status": "unknown"
            })
            
            # Add runtime information
            info["cache_stats"] = {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0.0
            }
            
            return info
            
        except Exception as exc:
            self._logger.error(f"Error getting model info for {model}: {str(exc)}")
            raise
    
    async def compare_embeddings(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Compare two embeddings and return similarity score.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score
        """
        try:
            if not embedding1 or not embedding2 or len(embedding1) != len(embedding2):
                return 0.0
            
            # Calculate cosine similarity
            dot_product = sum(x * y for x, y in zip(embedding1, embedding2))
            magnitude1 = sum(x * x for x in embedding1) ** 0.5
            magnitude2 = sum(x * x for x in embedding2) ** 0.5
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            similarity = dot_product / (magnitude1 * magnitude2)
            
            # Ensure result is in valid range [-1, 1]
            return max(-1.0, min(1.0, similarity))
            
        except Exception as exc:
            self._logger.error(f"Error comparing embeddings: {str(exc)}")
            return 0.0
    
    async def detect_language(self, text: str) -> str:
        """Detect language of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Language code
        """
        try:
            # Simple language detection based on character patterns
            # In production, you'd use a proper language detection library
            
            text_sample = text[:1000].lower()
            
            # Check for common language patterns
            if any(char in text_sample for char in "áéíóúñü¿¡"):
                return "es"  # Spanish
            elif any(char in text_sample for char in "àâäéèêëïîôöùûüÿç"):
                return "fr"  # French
            elif any(char in text_sample for char in "äöüß"):
                return "de"  # German
            elif any(char in text_sample for char in "àèéìíòòù"):
                return "it"  # Italian
            elif any(char in text_sample for char in "ãâáàçéêíóôõú"):
                return "pt"  # Portuguese
            elif any(char in text_sample for char in "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"):
                return "ru"  # Russian
            elif any(char in text_sample for char in "あいうえおかきくけこ"):
                return "ja"  # Japanese
            elif any(char in text_sample for char in "가나다라마바사"):
                return "ko"  # Korean
            elif any(char in text_sample for char in "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处队南给色光门即保治北造百规热领七海口东导器压志世金增争济阶油思术极交受联什认六共权收证改清己美再采转更单风切打白教速花带安场身车例真务具万每目至达走积示议声报斗完类八离华名确才科张信马节话米整空元况今集温传土许步群广石记需段研界拉林律叫且究观越织装影算低持音众书布复容儿须际商非验连断深难近矿千周委素技备半办青省列习响约支般史感劳便团往酸历市克何除消构府称太准精值号率族维划选标写存候毛亲快效斯院查江型眼王按格养易置派层片始却专状育厂京识适属圆包火住调满县局照参红细引听该铁价严首底液官德随病苏失尔死讲配女黄推显谈罪神艺呢席含企望密批营项防举球英氧势告李台落木帮轮破亚师围注远字材排供河态封另施减树溶怎止案言士均武固叶鱼波视仅费紧爱左章早朝害续轻服试食充兵源判护司足某练差致板田降黑犯负击范继兴似余坚曲输修的故城夫够送笔船占右财吃富春职觉汉画功巴跟虽杂飞检吸助升阳互初创抗考投坏策古径换未跑留钢曾端责站简述钱副尽帝射草冲承独令限阿宣环双请超微让控州良轴找否纪益依优顶础载倒房突坐粉敌略客袁冷胜绝析块剂测丝协诉念陈仍罗盐友洋错错夜田移"):
                return "zh"  # Chinese
            elif any(char in text_sample for char in "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"):
                return "ar"  # Arabic
            
            # Default to English
            return "en"
            
        except Exception as exc:
            self._logger.error(f"Error detecting language: {str(exc)}")
            return "en"
    
    async def get_supported_languages(self) -> List[str]:
        """Get supported languages for multilingual embeddings.
        
        Returns:
            List of supported language codes
        """
        return self._supported_languages.copy()
    
    async def optimize_embedding_for_task(
        self,
        embedding: List[float],
        task_type: str
    ) -> List[float]:
        """Optimize embedding for specific task type.
        
        Args:
            embedding: Original embedding vector
            task_type: Type of task (semantic_search, classification, etc.)
            
        Returns:
            Optimized embedding vector
        """
        try:
            optimization = self._task_optimizations.get(task_type, {
                "weight_recent": 1.0,
                "weight_keywords": 1.0
            })
            
            # For now, return the original embedding
            # In production, this would apply task-specific transformations
            # such as:
            # - Dimensionality reduction for certain tasks
            # - Weighting specific dimensions
            # - Applying task-specific normalization
            
            return embedding
            
        except Exception as exc:
            self._logger.error(f"Error optimizing embedding for {task_type}: {str(exc)}")
            return embedding
    
    # Helper methods
    
    async def _generate_llm_embedding(self, text: str, model: str) -> List[float]:
        """Generate embedding using LLM provider."""
        try:
            # Try to use Google Generative AI embeddings
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            
            api_key = self.settings.google_api_key
            if not api_key:
                api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            
            if api_key:
                embeddings_model = GoogleGenerativeAIEmbeddings(
                    model=model,
                    google_api_key=api_key,
                )
                vector = embeddings_model.embed_query(text)
                
                # Ensure correct dimensions
                if len(vector) != self.default_dimensions:
                    vector = self._normalize_vector_dimensions(vector, self.default_dimensions)
                
                return vector
            else:
                raise ValueError("No API key available for embeddings")
                
        except Exception as exc:
            self._logger.warning(f"LLM embedding failed, using fallback: {str(exc)}")
            return self._generate_hash_embedding(text, self.default_dimensions)
    
    def _generate_hash_embedding(self, text: str, dims: int) -> List[float]:
        """Generate hash-based fallback embedding."""
        vector = [0.0] * dims
        tokens = self._tokenize(text)
        
        if not tokens:
            return vector
        
        for token in tokens:
            digest = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = digest % dims
            sign = -1.0 if ((digest >> 1) & 1) else 1.0
            vector[idx] += sign
        
        # Normalize the vector
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        
        return vector
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for hash embedding."""
        return re.findall(r"[a-zA-Z0-9_]+", text.lower())
    
    def _normalize_vector_dimensions(self, vector: List[float], target_dims: int) -> List[float]:
        """Normalize vector to target dimensions."""
        if len(vector) == target_dims:
            return vector
        elif len(vector) > target_dims:
            return vector[:target_dims]
        else:
            # Pad with zeros
            return vector + [0.0] * (target_dims - len(vector))
    
    def _get_cache_key(self, text: str, model: Optional[str], language: Optional[str]) -> str:
        """Generate cache key for embedding."""
        key_parts = [
            text[:100],  # First 100 chars
            model or self.default_model,
            language or "auto"
        ]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()
    
    async def _cache_embedding(self, key: str, embedding: List[float]) -> None:
        """Cache embedding with size management."""
        # Check cache size limit
        if len(self._embedding_cache) >= self._cache_size_limit:
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self._embedding_cache.keys())[:100]
            for k in keys_to_remove:
                del self._embedding_cache[k]
        
        self._embedding_cache[key] = embedding
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "cache_size": len(self._embedding_cache),
            "cache_limit": self._cache_size_limit,
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }
    
    def clear_cache(self) -> None:
        """Clear embedding cache."""
        self._embedding_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
