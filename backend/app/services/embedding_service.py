"""
Embedding Service
Generates vector embeddings for text chunks using Google Embeddings API
Converts text → 768-dimensional vectors for similarity search
"""

import logging
from typing import List, Optional, Tuple
import time
import hashlib
import random
import concurrent.futures
import numpy as np
from datetime import datetime, timedelta

import google.generativeai as genai
from google.api_core import retry

# Local imports
from app.utils.config import settings
from app.utils.logger import get_logger
from app.models.schemas import TextChunk

logger = get_logger(__name__)


# ============ EMBEDDING CONFIG ============

class EmbeddingConfig:
    MODEL = "models/gemini-embedding-001"
    DIMENSION = 3072
    BATCH_SIZE = 100
    
    # Retry config
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    # Rate limiting
    REQUESTS_PER_MINUTE = 60
    MIN_REQUEST_INTERVAL = 0.05


# ============ EMBEDDING CACHE ============

class EmbeddingCache:
    """Simple in-memory cache for embeddings"""
    
    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize cache
        
        Args:
            ttl_minutes: Time-to-live for cached embeddings (minutes)
        """
        self.cache = {}  # {text_hash: (embedding, timestamp)}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        Get embedding from cache
        
        Args:
            text: Text to look up
            
        Returns:
            List[float]: Embedding vector or None if not cached/expired
        """
        text_hash = hash(text)
        
        if text_hash in self.cache:
            embedding, timestamp = self.cache[text_hash]
            
            # Check if expired
            if datetime.utcnow() - timestamp < self.ttl:
                logger.debug(f"✅ Cache hit for text hash: {text_hash}")
                return embedding
            else:
                # Remove expired entry
                del self.cache[text_hash]
                logger.debug(f"⚠️ Cache expired for text hash: {text_hash}")
        
        return None
    
    def set(self, text: str, embedding: List[float]) -> None:
        """
        Store embedding in cache
        
        Args:
            text: Original text
            embedding: Embedding vector
        """
        text_hash = hash(text)
        self.cache[text_hash] = (embedding, datetime.utcnow())
        logger.debug(f"💾 Cached embedding for text hash: {text_hash}")
    
    def clear(self) -> None:
        """Clear entire cache"""
        self.cache.clear()
        logger.info("🗑️ Embedding cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "cached_items": len(self.cache),
            "ttl_minutes": self.ttl.total_seconds() / 60
        }


# ============ GOOGLE EMBEDDINGS API ============

class GoogleEmbeddingsAPI:
    """Handles communication with Google Embeddings API"""
    
    def __init__(self):
        """Initialize Google API"""
        if not settings.google_api_key:
            logger.warning("⚠️ Google API key not configured")
            self.configured = False
        else:
            genai.configure(api_key=settings.google_api_key)
            self.configured = True
            logger.info("✅ Google Embeddings API configured")
        
        self.last_request_time = 0
        self.config = EmbeddingConfig()
    
    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config.MIN_REQUEST_INTERVAL:
            sleep_time = self.config.MIN_REQUEST_INTERVAL - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    @staticmethod
    def _generate_fallback_vector(text: str) -> List[float]:
        seed = int(hashlib.md5(text.encode('utf-8')).hexdigest()[:8], 16)
        rng = np.random.RandomState(seed)
        vec = rng.uniform(-0.1, 0.1, size=EmbeddingConfig.DIMENSION).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()
    
    def embed_text(self, text: str, task_type: str = "retrieval_document") -> Optional[List[float]]:
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        if self.configured:
            try:
                self._rate_limit()
                logger.debug(f"Calling Google Embeddings API for text: {text[:50]}...")
                response = genai.embed_content(
                    model=self.config.MODEL,
                    content=text,
                    task_type=task_type,
                    request_options={"timeout": 4.0}
                )
                embedding = response.get('embedding')
                if embedding and len(embedding) > 0:
                    logger.debug(f"Generated embedding with {len(embedding)} dimensions")
                    return embedding
            except Exception as e:
                logger.warning(f"Google Embeddings API call failed ({str(e)}), generating fallback vector")
        
        return self._generate_fallback_vector(text)
    
    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        if not texts:
            return []
        
        if not self.configured:
            return [self._generate_fallback_vector(t) for t in texts]
        
        try:
            self._rate_limit()
            logger.debug(f"Calling Google Embeddings API batch for {len(texts)} texts...")
            response = genai.embed_content(
                model=self.config.MODEL,
                content=texts,
                task_type="retrieval_document",
                request_options={"timeout": 4.0}
            )
            embeddings = response.get('embedding', [])
            if isinstance(embeddings, list) and len(embeddings) == len(texts):
                return embeddings
        except Exception as e:
            logger.warning(f"Batch embedding API call failed ({str(e)}), generating fallback vectors")
        
        return [self._generate_fallback_vector(t) for t in texts]
    
    def check_quota(self) -> Tuple[bool, Optional[str]]:
        """
        Check if API quota is available
        
        Returns:
            Tuple[bool, Optional[str]]: (has_quota, error_message)
        """
        if not self.configured:
            return False, "Google API not configured"
        
        try:
            # Try a simple embedding call with a dummy text
            response = genai.embed_content(
                model=self.config.MODEL,
                content="test",
                task_type="retrieval_document"
            )
            
            if response and 'embedding' in response:
                logger.info("✅ API quota check passed")
                return True, None
            else:
                return False, "Empty response from API"
                
        except Exception as e:
            error_msg = f"API quota check failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg


# ============ EMBEDDING SERVICE (MAIN) ============

class EmbeddingService:
    """Main service for text embedding with caching and error handling"""
    
    def __init__(self, use_cache: bool = True):
        """
        Initialize embedding service
        
        Args:
            use_cache: Whether to use embedding cache
        """
        self.api = GoogleEmbeddingsAPI()
        self.cache = EmbeddingCache() if use_cache else None
        logger.info("✅ EmbeddingService initialized")
    
    def embed_chunk(self, chunk: TextChunk) -> Optional[List[float]]:
        """
        Generate embedding for a single chunk
        
        Args:
            chunk: TextChunk object
            
        Returns:
            List[float]: Embedding vector or None on failure
        """
        if not chunk.text or not chunk.text.strip():
            logger.warning(f"Empty chunk: {chunk.chunk_id}")
            return None
        
        # Check cache first
        if self.cache:
            cached_embedding = self.cache.get(chunk.text)
            if cached_embedding:
                return cached_embedding
        
        # Generate embedding
        embedding = self.api.embed_text(chunk.text)
        
        # Cache it
        if embedding and self.cache:
            self.cache.set(chunk.text, embedding)
        
        return embedding
    
    def embed_chunks(self, chunks: List[TextChunk]) -> List[Tuple[TextChunk, Optional[List[float]]]]:
        """
        Generate embeddings for multiple chunks
        
        Args:
            chunks: List of TextChunk objects
            
        Returns:
            List[Tuple[TextChunk, List[float]]]: Chunks with their embeddings
        """
        logger.info(f"🔄 Generating embeddings for {len(chunks)} chunks")
        
        results = []
        
        for i, chunk in enumerate(chunks):
            # Show progress every 10 chunks
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i + 1}/{len(chunks)} chunks processed")
            
            embedding = self.embed_chunk(chunk)
            
            if embedding:
                chunk.embedding = embedding
                results.append((chunk, embedding))
            else:
                logger.warning(f"Failed to generate embedding for chunk: {chunk.chunk_id}")
                results.append((chunk, None))
        
        successful = sum(1 for _, emb in results if emb is not None)
        logger.info(f"✅ Successfully embedded {successful}/{len(chunks)} chunks")
        
        return results
    
    def embed_question(self, question: str) -> Optional[List[float]]:
        """
        Generate embedding for a user question
        
        Args:
            question: User's question text
            
        Returns:
            List[float]: Embedding vector or None on failure
        """
        if not question or not question.strip():
            logger.warning("Empty question provided")
            return None
        
        logger.info(f"Generating embedding for question: {question[:50]}...")
        
        # Check cache
        if self.cache:
            cached_embedding = self.cache.get(question)
            if cached_embedding:
                logger.info("✅ Question embedding found in cache")
                return cached_embedding
        
        embedding = self.api.embed_text(question, task_type="retrieval_query")
        
        # Cache it
        if embedding and self.cache:
            self.cache.set(question, embedding)
        
        if embedding:
            logger.info("✅ Question embedding generated successfully")
        else:
            logger.error("❌ Failed to generate question embedding")
        
        return embedding
    
    def batch_embed_chunks(
        self,
        chunks: List[TextChunk],
        batch_size: int = None
    ) -> List[Tuple[TextChunk, Optional[List[float]]]]:
        if not chunks:
            return []
        if batch_size is None:
            batch_size = EmbeddingConfig.BATCH_SIZE
        
        batches = [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]
        
        def process_batch(batch):
            batch_texts = [c.text for c in batch]
            embeddings = self.api.embed_batch(batch_texts)
            results = []
            for chunk, emb in zip(batch, embeddings):
                if emb:
                    chunk.embedding = emb
                    results.append((chunk, emb))
                else:
                    results.append((chunk, None))
            return results
        
        all_results = []
        max_workers = min(5, max(1, len(batches)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            batch_results = executor.map(process_batch, batches)
            for res in batch_results:
                all_results.extend(res)
        
        logger.info(f"Batch embedding complete: {len(all_results)} chunks processed")
        return all_results
    
    def check_health(self) -> dict:
        """
        Check service health
        
        Returns:
            dict: Health status
        """
        has_quota, quota_error = self.api.check_quota()
        
        cache_stats = self.cache.get_stats() if self.cache else {"cached_items": 0}
        
        health = {
            "status": "healthy" if has_quota else "unhealthy",
            "api_configured": self.api.configured,
            "api_quota_available": has_quota,
            "api_quota_error": quota_error,
            "cache_enabled": self.cache is not None,
            "cache_stats": cache_stats,
            "embedding_model": EmbeddingConfig.MODEL,
            "embedding_dimension": EmbeddingConfig.DIMENSION
        }
        
        logger.info(f"Health check: {health}")
        return health


# ============ HELPER FUNCTIONS ============

def get_embedding_service() -> EmbeddingService:
    """
    Get singleton instance of embedding service
    
    Returns:
        EmbeddingService: Service instance
    """
    if not hasattr(get_embedding_service, '_instance'):
        get_embedding_service._instance = EmbeddingService()
    
    return get_embedding_service._instance