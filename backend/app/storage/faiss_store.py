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
    
    def __init__(self, index_path: str = None, dimension: int = 768):
        """
        Initialize FAISS Vector Store
        
        Args:
            index_path: Path to save/load index (default: from config)
            dimension: Vector dimension (default: 768 for Google Embeddings)
        """
        self.dimension = dimension
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
                    logger.warning(f"⚠️ Skipping chunk {chunk.chunk_id}: None embedding")
                    continue
                
                # Convert to numpy float32
                vector = np.array(embedding, dtype=np.float32)
                
                # Validate vector dimension
                if len(vector) != self.dimension:
                    logger.warning(
                        f"⚠️ Skipping chunk {chunk.chunk_id}: "
                        f"wrong dimension {len(vector)} != {self.dimension}"
                    )
                    continue
                
                # Normalize for cosine similarity
                faiss.normalize_L2(vector.reshape(1, -1))
                
                vectors.append(vector)
                valid_chunks.append(chunk)
            
            if not vectors:
                error = "No valid vectors to add"
                logger.error(f"❌ {error}")
                return False, error
            
            # Convert to numpy array
            vectors_array = np.array(vectors, dtype=np.float32)
            
            # Add to index
            self.index.add(vectors_array)
            self.vector_count = self.index.ntotal
            
            for chunk in valid_chunks:
                metadata = {
                    "chunk_id": chunk.chunk_id,
                    "file_id": chunk.file_id,
                    "filename": getattr(chunk, "filename", None),
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "page_number": chunk.page_number,
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
        threshold: float = 0.0
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Search for similar vectors in index
        
        Args:
            query_vector: Query embedding (768-dim)
            k: Number of results to return
            threshold: Minimum similarity threshold (0-1, 0=no threshold)
            
        Returns:
            Tuple[List[Dict], Optional[str]]: (results, error_message)
            
        Results format:
        [
            {
                "rank": 1,
                "chunk_id": "uuid-123",
                "file_id": "uuid-456",
                "text": "...",
                "page_number": 1,
                "similarity_score": 0.92  # 0-1, higher=better
            },
            ...
        ]
        """
        
        if self.vector_count == 0:
            error = "No vectors in index"
            logger.error(f"❌ {error}")
            return [], error
        
        if not query_vector or len(query_vector) != self.dimension:
            error = f"Invalid query vector dimension: {len(query_vector) if query_vector else 0}"
            logger.error(f"❌ {error}")
            return [], error
        
        try:
            logger.info(f"Searching for top-{k} similar vectors")
            
            # Prepare query vector
            query = np.array([query_vector], dtype=np.float32)
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query)
            
            # Search
            # FAISS returns distances and indices
            # For normalized L2, distance = 2 - 2*cosine_similarity
            # So: similarity = 1 - (distance / 2)
            distances, indices = self.index.search(query, min(k, self.vector_count))
            
            results = []
            all_candidates = []
            
            for rank, (distance, idx) in enumerate(zip(distances[0], indices[0]), 1):
                if idx < 0 or idx >= len(self.metadata):
                    continue
                similarity_score = max(0.0, 1.0 - (distance / 2.0))
                metadata = self.metadata[idx]
                
                result = {
                    "rank": rank,
                    "chunk_id": metadata["chunk_id"],
                    "file_id": metadata["file_id"],
                    "filename": metadata.get("filename"),
                    "chunk_index": metadata["chunk_index"],
                    "text": metadata["text"],
                    "page_number": metadata["page_number"],
                    "section_heading": metadata["section_heading"],
                    "similarity_score": float(similarity_score)
                }
                
                all_candidates.append(result)
                if similarity_score >= threshold:
                    results.append(result)
            
            final_results = results if results else all_candidates
            logger.info(f"✅ Found {len(final_results)} results")
            return final_results, None
            
        except Exception as e:
            error = f"Search failed: {str(e)}"
            logger.error(f"❌ {error}")
            return [], error
    
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