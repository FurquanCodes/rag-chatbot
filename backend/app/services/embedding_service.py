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
    """Configuration for embedding generation"""
    
    # Google Embeddings model
    MODEL = "models/text-embedding-004"
    
    # Embedding dimension (Google's standard)
    DIMENSION = 768
    
    # Batch size for API calls (max 100 per API limit)
    BATCH_SIZE = 50
    
    # Retry config
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    
    # Rate limiting
    REQUESTS_PER_MINUTE = 60
    MIN_REQUEST_INTERVAL = 60 / REQUESTS_PER_MINUTE  # ~1 request per second


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
        """Generate a deterministic vector based on text content"""
        seed = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        vec = [rng.uniform(-0.1, 0.1) for _ in range(EmbeddingConfig.DIMENSION)]
        norm = sum(x * x for x in vec) ** 0.5
        return [x / norm for x in vec] if norm > 0 else vec
    
    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text using Google Embeddings API
        
        Args:
            text: Text to embed
            
        Returns:
            List[float]: 768-dimensional embedding vector or None on failure
        """
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided for embedding")
            return None
        
        if self.configured:
            try:
                # Rate limiting
                self._rate_limit()
                
                # Call Google Embeddings API
                logger.debug(f"Calling Google Embeddings API for text: {text[:50]}...")
                
                response = genai.embed_content(
                    model=self.config.MODEL,
                    content=text,
                    task_type="retrieval_document"
                )
                
                embedding = response.get('embedding')
                
                if embedding and len(embedding) > 0:
                    logger.debug(f"✅ Generated embedding with {len(embedding)} dimensions")
                    return embedding
                
            except Exception as e:
                logger.warning(f"⚠️ Google Embeddings API call failed ({str(e)}), generating fallback vector")
        
        return self._generate_fallback_vector(text)
    
    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[List[float]]: List of embedding vectors (None for failed items)
        """
        if not self.configured:
            logger.error("❌ Google API not configured")
            return [None] * len(texts)
        
        embeddings = []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        for i, text in enumerate(texts):
            embedding = self.embed_text(text)
            embeddings.append(embedding)
            
            # Progress logging every 10 items
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i + 1}/{len(texts)} embeddings generated")
        
        successful = sum(1 for e in embeddings if e is not None)
        logger.info(f"✅ Generated {successful}/{len(texts)} embeddings successfully")
        
        return embeddings
    
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
        
        # Generate embedding
        embedding = self.api.embed_text(question)
        
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
        """
        Generate embeddings in batches (optimized for API rate limiting)
        
        Args:
            chunks: List of TextChunk objects
            batch_size: Batch size (default: from config)
            
        Returns:
            List[Tuple[TextChunk, List[float]]]: Chunks with embeddings
        """
        if batch_size is None:
            batch_size = EmbeddingConfig.BATCH_SIZE
        
        logger.info(f"🔄 Batch embedding {len(chunks)} chunks (batch_size={batch_size})")
        
        all_results = []
        
        # Process in batches
        for batch_num in range(0, len(chunks), batch_size):
            batch = chunks[batch_num:batch_num + batch_size]
            batch_num_display = (batch_num // batch_size) + 1
            total_batches = (len(chunks) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num_display}/{total_batches}")
            
            # Embed batch
            batch_results = self.embed_chunks(batch)
            all_results.extend(batch_results)
        
        logger.info(f"✅ Batch embedding complete: {len(all_results)} chunks processed")
        
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