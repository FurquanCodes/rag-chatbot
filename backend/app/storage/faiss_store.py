"""
FAISS Vector Store
Manages vector storage, retrieval, and similarity search
FAISS = Facebook AI Similarity Search (ultra-fast vector database)
"""

import logging
import os
import pickle
from typing import List, Tuple, Optional, Dict
from pathlib import Path
import re
import numpy as np

# FAISS
import faiss

# Local imports
from app.utils.config import settings, FAISS_INDEX_DIR
from app.utils.logger import get_logger
from app.models.schemas import TextChunk

logger = get_logger(__name__)


# ============ FAISS STORE ============

class FAISSVectorStore:
    """
    Manages FAISS vector index and metadata storage
    
    Architecture:
    - FAISS Index: Stores 768-dimensional vectors for ultra-fast search
    - Metadata Store: Stores chunk text, file_id, page_number, etc.
    - Persistence: Saves/loads to disk
    """
    
    def __init__(self, index_path: str = None, dimension: int = None):
        self.dimension = dimension or settings.embedding_dimension
        self.index_path = Path(index_path) if index_path else FAISS_INDEX_DIR
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.index_path / "faiss_index.bin"
        self.metadata_file = self.index_path / "metadata.pkl"
        
        # Initialize or load index
        self.index = None
        self.metadata = []  # List of chunk metadata dicts
        self.vector_count = 0
        
        self._initialize_index()
        logger.info(f"✅ FAISSVectorStore initialized at {self.index_path}")
    
    def _initialize_index(self) -> None:
        """Initialize or load existing FAISS index"""
        
        if self.index_file.exists() and self.metadata_file.exists():
            # Load existing index
            logger.info(f"Loading existing FAISS index from {self.index_file}")
            self.load_index()
        else:
            # Create new index
            logger.info(f"Creating new FAISS index (dimension={self.dimension})")
            self._create_new_index()
    
    def _create_new_index(self) -> None:
        """Create a new FAISS index"""
        
        # Create index using L2 (Euclidean distance)
        # For cosine similarity, we normalize vectors before adding
        quantizer = faiss.IndexFlatL2(self.dimension)
        self.index = quantizer
        
        self.metadata = []
        self.vector_count = 0
        
        logger.info("✅ New FAISS index created")
    
    def add_vectors(
        self,
        chunks: List[TextChunk],
        embeddings: List[List[float]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Add vectors to FAISS index with metadata
        
        Args:
            chunks: List of TextChunk objects
            embeddings: List of embedding vectors (768-dim each)
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        
        if not chunks or not embeddings:
            error = "Empty chunks or embeddings list"
            logger.error(f"❌ {error}")
            return False, error
        
        if len(chunks) != len(embeddings):
            error = f"Chunks and embeddings length mismatch: {len(chunks)} vs {len(embeddings)}"
            logger.error(f"❌ {error}")
            return False, error
        
        try:
            logger.info(f"Adding {len(chunks)} vectors to FAISS index")
            
            # Prepare vectors for FAISS (must be np.float32 array)
            vectors = []
            valid_chunks = []
            
            for chunk, embedding in zip(chunks, embeddings):
                if embedding is None:
                    continue
                
                vector = np.array(embedding, dtype=np.float32)
                if len(vector) != self.dimension:
                    continue
                
                vectors.append(vector)
                valid_chunks.append(chunk)
            
            if not vectors:
                error = "No valid vectors to add"
                logger.error(f"❌ {error}")
                return False, error
            
            vectors_array = np.array(vectors, dtype=np.float32)
            faiss.normalize_L2(vectors_array)
            self.index.add(vectors_array)
            self.vector_count = self.index.ntotal
            
            # Store metadata
            for chunk in valid_chunks:
                metadata = {
                    "chunk_id": chunk.chunk_id,
                    "file_id": chunk.file_id,
                    "file_number": getattr(chunk, "file_number", 1),
                    "filename": getattr(chunk, "filename", None),
                    "file_type": getattr(chunk, "file_type", None),
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "original_text": getattr(chunk, "original_text", chunk.text),
                    "page_number": chunk.page_number,
                    "line_start": getattr(chunk, "line_start", None),
                    "line_end": getattr(chunk, "line_end", None),
                    "section_heading": chunk.section_heading,
                    "created_at": chunk.created_at.isoformat() if chunk.created_at else None
                }
                self.metadata.append(metadata)
            
            logger.info(f"✅ Added {len(valid_chunks)} vectors (total: {self.vector_count})")
            return True, None
            
        except Exception as e:
            error = f"Failed to add vectors: {str(e)}"
            logger.error(f"❌ {error}")
            return False, error
    
    def search(
        self,
        query_vector: List[float],
        k: int = 5,
        threshold: float = 0.0,
        file_id: Optional[str] = None,
        target_file_number: Optional[int] = None,
        target_filename: Optional[str] = None,
        raw_query: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        if self.vector_count == 0:
            error = "No vectors in index"
            logger.error(f"❌ {error}")
            return [], error
        
        if not query_vector or len(query_vector) != self.dimension:
            error = f"Invalid query vector dimension: {len(query_vector) if query_vector else 0}"
            logger.error(f"❌ {error}")
            return [], error
        
        try:
            target_file_id = file_id if file_id and str(file_id).strip() else None

            logger.info(f"Searching for top-{k} similar vectors (file_id={target_file_id}, file_num={target_file_number}, filename={target_filename})")
            query = np.array([query_vector], dtype=np.float32)
            faiss.normalize_L2(query)
            
            search_k = self.vector_count
            distances, indices = self.index.search(query, search_k)
            
            raw_q_words = []
            if raw_query:
                raw_q_words = [w.lower() for w in re.findall(r'[A-Za-z0-9_]+', raw_query) if len(w) >= 3]

            candidates = []
            
            for distance, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self.metadata):
                    continue
                    
                metadata = self.metadata[idx]
                
                if target_file_id and metadata.get("file_id") != target_file_id:
                    continue
                if target_file_number and metadata.get("file_number") != target_file_number:
                    continue
                if target_filename and metadata.get("filename") and target_filename.lower() not in metadata.get("filename").lower():
                    continue
                
                similarity_score = max(0.0, 1.0 - (distance / 2.0))
                
                chunk_text_lower = (metadata.get("text") or "").lower()
                for qw in raw_q_words:
                    if qw in chunk_text_lower:
                        similarity_score += 0.3
                
                if similarity_score < threshold:
                    continue
                
                result = {
                    "rank": 0,
                    "chunk_id": metadata["chunk_id"],
                    "file_id": metadata["file_id"],
                    "file_number": metadata.get("file_number", 1),
                    "filename": metadata.get("filename") or self.get_filename(metadata["file_id"]),
                    "file_type": metadata.get("file_type"),
                    "chunk_index": metadata["chunk_index"],
                    "text": metadata["text"],
                    "original_text": metadata.get("original_text", metadata["text"]),
                    "page_number": metadata.get("page_number"),
                    "line_start": metadata.get("line_start"),
                    "line_end": metadata.get("line_end"),
                    "section_heading": metadata.get("section_heading"),
                    "similarity_score": float(similarity_score)
                }
                candidates.append(result)
            
            if not candidates and target_file_id:
                logger.info("No candidates matched specified file_id, retrying across all documents...")
                return self.search(
                    query_vector=query_vector,
                    k=k,
                    threshold=threshold,
                    file_id=None,
                    target_file_number=target_file_number,
                    target_filename=target_filename,
                    raw_query=raw_query
                )

            candidates.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            results = []
            for rank, item in enumerate(candidates[:k], 1):
                item["rank"] = rank
                results.append(item)
            
            logger.info(f"✅ Found {len(results)} results (file_id={file_id}, threshold={threshold})")
            return results, None
            
        except Exception as e:
            error = f"Search failed: {str(e)}"
            logger.error(f"❌ {error}")
            return [], error

    def get_filename(self, file_id: str) -> Optional[str]:
        for meta in self.metadata:
            if meta.get("file_id") == file_id and meta.get("filename"):
                return meta["filename"]
        return None
    
    def delete_by_file_id(self, file_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete all vectors for a specific file
        
        Note: FAISS doesn't support direct deletion.
        We rebuild the index without the file's vectors.
        
        Args:
            file_id: File ID to delete
            
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        
        try:
            logger.info(f"Deleting vectors for file_id: {file_id}")
            
            # Find indices to keep
            indices_to_keep = []
            new_metadata = []
            
            for idx, meta in enumerate(self.metadata):
                if meta["file_id"] != file_id:
                    indices_to_keep.append(idx)
                    new_metadata.append(meta)
            
            deleted_count = len(self.metadata) - len(new_metadata)
            
            if deleted_count == 0:
                logger.warning(f"⚠️ No vectors found for file_id: {file_id}")
                return True, None
            
            # Rebuild index without deleted vectors
            if indices_to_keep:
                all_vectors = self.index.reconstruct_n(0, self.vector_count)
                vectors_to_keep = all_vectors[indices_to_keep]
                self._create_new_index()
                self.index.add(vectors_to_keep)
                self.metadata = new_metadata
                self.vector_count = self.index.ntotal
            else:
                self._create_new_index()
            
            logger.info(f"✅ Deleted {deleted_count} vectors for file_id: {file_id}")
            return True, None
            
        except Exception as e:
            error = f"Deletion failed: {str(e)}"
            logger.error(f"❌ {error}")
            return False, error
    
    def get_stats(self) -> Dict:
        """
        Get index statistics
        
        Returns:
            dict: Index stats (size, vector_count, etc.)
        """
        
        try:
            # Count unique files
            file_ids = set(m["file_id"] for m in self.metadata)
            
            stats = {
                "total_vectors": self.vector_count,
                "total_chunks": len(self.metadata),
                "unique_files": len(file_ids),
                "vector_dimension": self.dimension,
                "index_size_bytes": os.path.getsize(self.index_file) if self.index_file.exists() else 0
            }
            
            logger.info(f"Index stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {str(e)}")
            return {}
    
    def save_index(self) -> Tuple[bool, Optional[str]]:
        """
        Save index and metadata to disk
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        
        try:
            logger.info(f"Saving FAISS index to {self.index_file}")
            
            # Save index
            faiss.write_index(self.index, str(self.index_file))
            
            # Save metadata
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
            
            logger.info(f"✅ Index saved: {self.vector_count} vectors")
            return True, None
            
        except Exception as e:
            error = f"Failed to save index: {str(e)}"
            logger.error(f"❌ {error}")
            return False, error
    
    def load_index(self) -> Tuple[bool, Optional[str]]:
        """
        Load index and metadata from disk
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        
        try:
            logger.info(f"Loading FAISS index from {self.index_file}")
            
            # Load index
            self.index = faiss.read_index(str(self.index_file))
            self.vector_count = self.index.ntotal
            
            # Load metadata
            with open(self.metadata_file, 'rb') as f:
                self.metadata = pickle.load(f)
            
            logger.info(f"✅ Index loaded: {self.vector_count} vectors")
            return True, None
            
        except Exception as e:
            error = f"Failed to load index: {str(e)}"
            logger.error(f"❌ {error}")
            return False, error
    
    def clear_index(self) -> Tuple[bool, Optional[str]]:
        """
        Clear all vectors and metadata
        
        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        
        try:
            logger.info("Clearing FAISS index")
            
            self._create_new_index()
            
            logger.info("✅ Index cleared")
            return True, None
            
        except Exception as e:
            error = f"Failed to clear index: {str(e)}"
            logger.error(f"❌ {error}")
            return False, error


# ============ SINGLETON INSTANCE ============

_faiss_store = None


def get_faiss_store() -> FAISSVectorStore:
    """
    Get singleton FAISS store instance
    
    Returns:
        FAISSVectorStore: Global vector store instance
    """
    global _faiss_store
    
    if _faiss_store is None:
        _faiss_store = FAISSVectorStore()
    
    return _faiss_store