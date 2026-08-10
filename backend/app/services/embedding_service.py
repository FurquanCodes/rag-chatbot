import logging
import re
import time
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import google.generativeai as genai
import numpy as np

from app.models.schemas import TextChunk
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


def generate_fallback_vector(text: str, dimension: int = 768) -> List[float]:
    vec = np.zeros(dimension, dtype=np.float32)
    words = re.findall(r'\w+', text.lower())
    if not words:
        words = ["empty"]
    for word in words:
        idx = abs(hash(word)) % dimension
        vec[idx] += 1.0
    for i in range(len(words) - 1):
        bigram = f"{words[i]}_{words[i+1]}"
        idx = abs(hash(bigram)) % dimension
        vec[idx] += 1.5
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


class EmbeddingConfig:
    MODEL = "models/embedding-001"
    DIMENSION = 768
    BATCH_SIZE = 100
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    REQUESTS_PER_MINUTE = 60
    MIN_REQUEST_INTERVAL = 60 / REQUESTS_PER_MINUTE


class EmbeddingCache:
    def __init__(self, ttl_minutes: int = 60):
        self.cache = {}
        self.ttl = timedelta(minutes=ttl_minutes)

    def get(self, text: str) -> Optional[List[float]]:
        text_hash = hash(text)
        if text_hash in self.cache:
            embedding, timestamp = self.cache[text_hash]
            if datetime.utcnow() - timestamp < self.ttl:
                return embedding
            else:
                del self.cache[text_hash]
        return None

    def set(self, text: str, embedding: List[float]) -> None:
        text_hash = hash(text)
        self.cache[text_hash] = (embedding, datetime.utcnow())

    def clear(self) -> None:
        self.cache.clear()

    def get_stats(self) -> dict:
        return {
            "cached_items": len(self.cache),
            "ttl_minutes": self.ttl.total_seconds() / 60
        }


class GoogleEmbeddingsAPI:
    def __init__(self):
        self.config = EmbeddingConfig()
        self.last_request_time = 0
        self.configured = False
        self._failed_key = False
        self._check_config()

    def _check_config(self) -> bool:
        if self._failed_key:
            self.configured = False
            return False

        key = (settings.google_api_key or "").strip()
        if not key or "your_" in key.lower() or "here" in key.lower() or not key.startswith("AIzaSy"):
            self.configured = False
            return False

        try:
            genai.configure(api_key=key)
            self.configured = True
        except Exception:
            self.configured = False
            self._failed_key = True
        return self.configured

    def _rate_limit(self) -> None:
        if not self.configured:
            return
        elapsed = time.time() - self.last_request_time
        if elapsed < self.config.MIN_REQUEST_INTERVAL:
            sleep_time = self.config.MIN_REQUEST_INTERVAL - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def embed_text(self, text: str) -> Optional[List[float]]:
        if not self._check_config():
            return generate_fallback_vector(text, self.config.DIMENSION)

        if not text or not text.strip():
            return None

        try:
            self._rate_limit()
            response = genai.embed_content(
                model=self.config.MODEL,
                content=text,
                task_type="retrieval_document",
                title="RAG Document"
            )
            embedding = response['embedding']
            if not embedding or len(embedding) == 0:
                return generate_fallback_vector(text, self.config.DIMENSION)
            return embedding
        except Exception:
            self.configured = False
            self._failed_key = True
            return generate_fallback_vector(text, self.config.DIMENSION)

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        if not texts:
            return []

        if not self._check_config():
            return [generate_fallback_vector(text, self.config.DIMENSION) for text in texts]

        results = []
        batch_size = self.config.BATCH_SIZE
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            try:
                self._rate_limit()
                response = genai.embed_content(
                    model=self.config.MODEL,
                    content=batch_texts,
                    task_type="retrieval_document",
                    title="RAG Document"
                )
                embeddings = response.get('embedding', [])
                if isinstance(embeddings, list) and len(embeddings) == len(batch_texts):
                    results.extend(embeddings)
                else:
                    for text in batch_texts:
                        results.append(generate_fallback_vector(text, self.config.DIMENSION))
            except Exception:
                self.configured = False
                self._failed_key = True
                remaining_count = len(texts) - len(results)
                logger.warning(f"Embedding API error or key failure. Generating {remaining_count} fallback vectors in memory.")
                for text in texts[len(results):]:
                    results.append(generate_fallback_vector(text, self.config.DIMENSION))
                break
        return results

    def check_quota(self) -> Tuple[bool, Optional[str]]:
        if not self._check_config():
            return False, "Google API key not configured or invalid"
        try:
            response = genai.embed_content(
                model=self.config.MODEL,
                content="test",
                task_type="retrieval_document"
            )
            if response and 'embedding' in response:
                return True, None
            return False, "Empty response from API"
        except Exception as e:
            self._failed_key = True
            return False, str(e)


class EmbeddingService:
    def __init__(self, use_cache: bool = True):
        self.api = GoogleEmbeddingsAPI()
        self.cache = EmbeddingCache() if use_cache else None

    def embed_chunk(self, chunk: TextChunk) -> Optional[List[float]]:
        if not chunk.text or not chunk.text.strip():
            return None
        if self.cache:
            cached = self.cache.get(chunk.text)
            if cached:
                return cached
        embedding = self.api.embed_text(chunk.text)
        if embedding and self.cache:
            self.cache.set(chunk.text, embedding)
        return embedding

    def embed_chunks(self, chunks: List[TextChunk]) -> List[Tuple[TextChunk, Optional[List[float]]]]:
        results = []
        for chunk in chunks:
            emb = self.embed_chunk(chunk)
            if emb:
                chunk.embedding = emb
            results.append((chunk, emb))
        return results

    def embed_question(self, question: str) -> Optional[List[float]]:
        if not question or not question.strip():
            return None
        if self.cache:
            cached = self.cache.get(question)
            if cached:
                return cached
        embedding = self.api.embed_text(question)
        if embedding and self.cache:
            self.cache.set(question, embedding)
        return embedding

    def batch_embed_chunks(
        self,
        chunks: List[TextChunk],
        batch_size: int = None
    ) -> List[Tuple[TextChunk, Optional[List[float]]]]:
        if not chunks:
            return []
        texts = [chunk.text for chunk in chunks]
        embeddings = self.api.embed_batch(texts)
        results = []
        for chunk, emb in zip(chunks, embeddings):
            if emb:
                chunk.embedding = emb
                if self.cache and chunk.text:
                    self.cache.set(chunk.text, emb)
            results.append((chunk, emb))
        return results

    def check_health(self) -> dict:
        has_quota, quota_error = self.api.check_quota()
        cache_stats = self.cache.get_stats() if self.cache else {"cached_items": 0}
        return {
            "status": "healthy" if has_quota else "degraded",
            "api_configured": self.api.configured,
            "api_quota_available": has_quota,
            "api_quota_error": quota_error,
            "cache_enabled": self.cache is not None,
            "cache_stats": cache_stats,
            "embedding_model": EmbeddingConfig.MODEL,
            "embedding_dimension": EmbeddingConfig.DIMENSION
        }


def get_embedding_service() -> EmbeddingService:
    if not hasattr(get_embedding_service, '_instance'):
        get_embedding_service._instance = EmbeddingService()
    return get_embedding_service._instance