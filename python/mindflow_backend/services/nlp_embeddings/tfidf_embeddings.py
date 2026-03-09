"""TF-IDF based embedding implementation.

Lightweight and fast embedding generation using TF-IDF
vectorization with optional BM25 scoring.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import math
import asyncio
from collections import Counter, defaultdict

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from mindflow_backend.infra.logging import get_logger
from .nlp_embedding_service import EmbeddingConfig, BaseEmbeddingGenerator

_logger = get_logger(__name__)


class BM25EmbeddingGenerator(BaseEmbeddingGenerator):
    """BM25 based embedding generator for keyword search."""
    
    def __init__(self, config: EmbeddingConfig) -> None:
        """Initialize BM25 embedding generator.
        
        Args:
            config: Embedding configuration.
        """
        self.config = config
        self.doc_freqs: List[Counter] = []
        self.idf: Optional[dict] = None
        self.doc_len: List[int] = []
        self.avg_doc_len: float = 0
        self.corpus_size: int = 0
        self.k1 = config.kwargs.get('k1', 1.2)
        self.b = config.kwargs.get('b', 0.75)
        self.epsilon = config.kwargs.get('epsilon', 0.25)
        self.is_fitted = False
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization.
        
        Args:
            text: Text to tokenize.
            
        Returns:
            List of tokens.
        """
        # Simple tokenization - can be enhanced with better tokenizers
        import re
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    async def fit(self, texts: List[str]) -> None:
        """Fit BM25 model on corpus.
        
        Args:
            texts: Training texts.
        """
        self.corpus_size = len(texts)
        
        # Tokenize all documents
        tokenized_docs = [self._tokenize(doc) for doc in texts]
        
        # Calculate document frequencies
        self.doc_freqs = [Counter(doc) for doc in tokenized_docs]
        
        # Calculate document lengths
        self.doc_len = [len(doc) for doc in tokenized_docs]
        self.avg_doc_len = sum(self.doc_len) / self.corpus_size if self.corpus_size > 0 else 0
        
        # Calculate IDF
        self.idf = {}
        for doc_freq in self.doc_freqs:
            for term in doc_freq:
                if term not in self.idf:
                    df = sum(1 for doc in self.doc_freqs if term in doc)
                    self.idf[term] = math.log((self.corpus_size - df + 0.5) / (df + 0.5))
        
        self.is_fitted = True
        _logger.info(f"BM25 fitted on {len(texts)} documents with {len(self.idf)} unique terms")
    
    def _get_score(self, doc_freq: Counter, query_tokens: List[str]) -> float:
        """Calculate BM25 score for document.
        
        Args:
            doc_freq: Document term frequencies.
            query_tokens: Query tokens.
            
        Returns:
            BM25 score.
        """
        score = 0
        doc_len = len(doc_freq)
        
        for term in query_tokens:
            if term in doc_freq and term in self.idf:
                tf = doc_freq[term]
                idf = self.idf[term]
                
                # BM25 formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += idf * (numerator / denominator)
        
        return score
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate BM25-based embeddings.
        
        Args:
            texts: Texts to embed.
            
        Returns:
            List of embedding vectors.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        
        # For BM25, we'll create a sparse representation
        # Each document is represented by its BM25 scores against all terms
        embeddings = []
        
        for text in texts:
            tokens = self._tokenize(text)
            token_counter = Counter(tokens)
            
            # Create sparse vector based on vocabulary
            embedding = []
            for term in sorted(self.idf.keys()):
                if term in token_counter:
                    # Use normalized term frequency as embedding value
                    tf = token_counter[term]
                    normalized_tf = tf / len(tokens) if len(tokens) > 0 else 0
                    embedding.append(normalized_tf)
                else:
                    embedding.append(0.0)
            
            embeddings.append(embedding)
        
        return embeddings
    
    def get_dimension(self) -> int:
        """Get BM25 embedding dimension.
        
        Returns:
            Number of unique terms in vocabulary.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        return len(self.idf)
    
    async def similarity(self, query: List[float], candidates: List[List[float]]) -> List[float]:
        """Calculate similarity using BM25 scoring.
        
        Args:
            query: Query embedding.
            candidates: Candidate embeddings.
            
        Returns:
            Similarity scores.
        """
        # For BM25, use dot product as similarity
        similarities = []
        
        for candidate in candidates:
            if len(query) != len(candidate):
                similarities.append(0.0)
                continue
            
            # Dot product similarity
            similarity = sum(q * c for q, c in zip(query, candidate))
            similarities.append(similarity)
        
        return similarities


class AdvancedTfidfEmbeddingGenerator(BaseEmbeddingGenerator):
    """Advanced TF-IDF with additional features."""
    
    def __init__(self, config: EmbeddingConfig) -> None:
        """Initialize advanced TF-IDF generator.
        
        Args:
            config: Embedding configuration.
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for advanced TF-IDF embeddings")
        
        self.config = config
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.is_fitted = False
        
        # Additional features
        self.use_char_ngrams = config.kwargs.get('use_char_ngrams', False)
        self.use_word_ngrams = config.kwargs.get('use_word_ngrams', True)
        self.max_features = config.max_features
        self.min_df = config.min_df
        self.max_df = config.max_df
    
    async def fit(self, texts: List[str]) -> None:
        """Fit advanced TF-IDF vectorizer.
        
        Args:
            texts: Training texts.
        """
        loop = asyncio.get_event_loop()
        
        # Configure analyzer based on features
        if self.use_char_ngrams and self.use_word_ngrams:
            # Hybrid approach
            self.vectorizer = TfidfVectorizer(
                analyzer='word',
                ngram_range=(1, 2),
                max_features=self.max_features // 2,
                min_df=self.min_df,
                max_df=self.max_df,
                stop_words='english',
            )
            
            # Fit word-level
            word_features = await loop.run_in_executor(
                None,
                self.vectorizer.fit_transform,
                texts
            )
            
            # Create character-level vectorizer
            char_vectorizer = TfidfVectorizer(
                analyzer='char',
                ngram_range=(3, 5),
                max_features=self.max_features // 2,
                min_df=self.min_df,
                max_df=self.max_df,
            )
            
            char_features = await loop.run_in_executor(
                None,
                char_vectorizer.fit_transform,
                texts
            )
            
            # Store both vectorizers (simplified approach)
            self.char_vectorizer = char_vectorizer
            
        elif self.use_char_ngrams:
            self.vectorizer = TfidfVectorizer(
                analyzer='char',
                ngram_range=(3, 5),
                max_features=self.max_features,
                min_df=self.min_df,
                max_df=self.max_df,
            )
        else:
            self.vectorizer = TfidfVectorizer(
                analyzer='word',
                ngram_range=self.config.ngram_range,
                max_features=self.max_features,
                min_df=self.min_df,
                max_df=self.max_df,
                stop_words='english' if self.config.kwargs.get('remove_stopwords', True) else None,
            )
        
        await loop.run_in_executor(
            None,
            self.vectorizer.fit_transform,
            texts
        )
        
        self.is_fitted = True
        _logger.info(f"Advanced TF-IDF fitted on {len(texts)} texts")
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate advanced TF-IDF embeddings.
        
        Args:
            texts: Texts to embed.
            
        Returns:
            List of embedding vectors.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        
        loop = asyncio.get_event_loop()
        
        if hasattr(self, 'char_vectorizer'):
            # Hybrid approach
            word_embeddings = await loop.run_in_executor(
                None,
                self.vectorizer.transform,
                texts
            )
            
            char_embeddings = await loop.run_in_executor(
                None,
                self.char_vectorizer.transform,
                texts
            )
            
            # Combine embeddings
            combined = []
            for i in range(len(texts)):
                word_vec = word_embeddings[i].toarray().flatten()
                char_vec = char_embeddings[i].toarray().flatten()
                combined_vec = np.concatenate([word_vec, char_vec])
                
                # Normalize
                norm = np.linalg.norm(combined_vec)
                if norm > 0:
                    combined_vec = combined_vec / norm
                
                combined.append(combined_vec.tolist())
            
            return combined
        else:
            embeddings = await loop.run_in_executor(
                None,
                self.vectorizer.transform,
                texts
            )
            
            dense_embeddings = embeddings.toarray()
            
            if self.config.normalize:
                norms = np.linalg.norm(dense_embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1
                dense_embeddings = dense_embeddings / norms
            
            return dense_embeddings.tolist()
    
    def get_dimension(self) -> int:
        """Get embedding dimension.
        
        Returns:
            Embedding dimension.
        """
        if not self.is_fitted:
            raise RuntimeError("Model not fitted")
        
        if hasattr(self, 'char_vectorizer'):
            word_dim = len(self.vectorizer.vocabulary_)
            char_dim = len(self.char_vectorizer.vocabulary_)
            return word_dim + char_dim
        else:
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


def create_tfidf_service(
    advanced: bool = False,
    use_bm25: bool = False,
    **kwargs: Any,
) -> BaseEmbeddingGenerator:
    """Create TF-IDF based embedding service.
    
    Args:
        advanced: Use advanced TF-IDF features.
        use_bm25: Use BM25 instead of TF-IDF.
        **kwargs: Additional configuration.
        
    Returns:
        Configured embedding generator.
    """
    config = EmbeddingConfig(
        method="tfidf" if not use_bm25 else "bm25",
        **kwargs
    )
    
    if use_bm25:
        return BM25EmbeddingGenerator(config)
    elif advanced:
        return AdvancedTfidfEmbeddingGenerator(config)
    else:
        from .nlp_embedding_service import TfidfEmbeddingGenerator
        return TfidfEmbeddingGenerator(config)
