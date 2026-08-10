"""
RAG Service
Retrieves relevant context and generates answers using Gemini
RAG = Retrieval Augmented Generation
"""

import logging
from typing import List, Optional, Tuple, Dict
import time

# Google Generative AI
import google.generativeai as genai

# Local imports
from app.utils.config import settings
from app.utils.logger import get_logger
from app.services.embedding_service import EmbeddingService
from app.storage.faiss_store import get_faiss_store

logger = get_logger(__name__)


# ============ RAG SERVICE ============

class RAGService:
    """
    Retrieval Augmented Generation Service
    
    Pipeline:
    1. Embed question
    2. Search FAISS for similar chunks
    3. Build prompt with context
    4. Call Gemini API
    5. Format and return answer
    """
    
    def __init__(self):
        """Initialize RAG service"""
        self.embedding_service = EmbeddingService()
        self.faiss_store = get_faiss_store()
        
        # Configure Gemini API
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.configured = True
            logger.info("✅ Gemini API configured")
        else:
            self.configured = False
            logger.warning("⚠️ Gemini API not configured")
    
    def retrieve_context(
        self,
        question: str,
        top_k: int = None,
        relevance_threshold: float = None
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Retrieve relevant chunks from FAISS
        
        Args:
            question: User's question
            top_k: Number of chunks to retrieve (default: from config)
            relevance_threshold: Minimum similarity score (default: from config)
            
        Returns:
            Tuple[List[Dict], Optional[str]]: (retrieved_chunks, error_message)
        """
        
        if top_k is None:
            top_k = settings.top_k_retrieval
        if relevance_threshold is None:
            relevance_threshold = 0.0
        
        logger.info(f"🔍 Retrieving context for question: {question[:50]}...")
        
        try:
            logger.debug("Step 1: Embedding question...")
            question_embedding = self.embedding_service.embed_question(question)
            
            if question_embedding is None:
                error = "Failed to embed question"
                logger.error(f"❌ {error}")
                return [], error
            
            logger.debug(f"Step 2: Searching FAISS (top_k={top_k}, threshold={relevance_threshold})...")
            retrieved_chunks, error = self.faiss_store.search(
                query_vector=question_embedding,
                k=top_k,
                threshold=relevance_threshold
            )
            
            if not retrieved_chunks and self.faiss_store.vector_count > 0:
                logger.info("Retrying FAISS search with zero threshold to prefer uploaded document content")
                retrieved_chunks, error = self.faiss_store.search(
                    query_vector=question_embedding,
                    k=top_k,
                    threshold=0.0
                )
            
            if error:
                logger.error(f"❌ FAISS search error: {error}")
                return [], error
            
            logger.info(f"✅ Retrieved {len(retrieved_chunks)} relevant chunks")
            return retrieved_chunks, None
            
        except Exception as e:
            error = f"Context retrieval failed: {str(e)}"
            logger.error(f"❌ {error}")
            return [], error
    
    def build_prompt(
        self,
        question: str,
        context_chunks: List[Dict]
    ) -> str:
        """
        Build prompt for Gemini with context
        
        Args:
            question: User's question
            context_chunks: Retrieved context chunks
            
        Returns:
            str: Formatted prompt for Gemini
        """
        
        logger.debug("Building prompt with context...")
        
        # System instruction
        system_instruction = """You are a helpful AI assistant specialized in answering questions based on provided documents.

IMPORTANT RULES:
1. ALWAYS answer based ONLY on the provided context
2. If the context doesn't contain the answer, say: "I don't have information about this in the documents"
3. Cite the specific document/section when possible
4. Be concise and accurate
5. If multiple documents mention the same topic, consider all of them

CONTEXT FROM DOCUMENTS:
═══════════════════════════════════════════════════════════════════
"""
        
        # Add context chunks
        context_text = ""
        for chunk in context_chunks:
            chunk_marker = f"\n[{chunk['rank']}. {chunk['file_id'][:8]}"
            
            if chunk.get('page_number'):
                chunk_marker += f" - Page {chunk['page_number']}"
            
            if chunk.get('section_heading'):
                chunk_marker += f" - {chunk['section_heading']}"
            
            chunk_marker += "]\n"
            context_text += chunk_marker + chunk['text'] + "\n\n"
        
        system_instruction += context_text
        
        # Add question
        system_instruction += """═══════════════════════════════════════════════════════════════════

QUESTION:
─────────────────────────────────────────────────────────────────────
"""
        system_instruction += question
        system_instruction += "\n─────────────────────────────────────────────────────────────────────\n"
        system_instruction += "\nPROVIDE YOUR ANSWER BELOW:\n"
        
        logger.debug(f"Prompt built: {len(system_instruction)} characters")
        
        return system_instruction
    
    def call_gemini(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Call Gemini API to generate answer
        
        Args:
            prompt: Formatted prompt with context
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (answer, error_message)
        """
        
        if not self.configured:
            error = "Gemini API not configured"
            logger.error(f"❌ {error}")
            return None, error
        
        try:
            logger.info("📞 Calling Gemini API...")
            
            # Call Gemini
            model = genai.GenerativeModel(settings.gemini_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1024,
                    temperature=0.7,
                    top_p=0.9
                )
            )
            
            if not response or not response.text:
                error = "Empty response from Gemini"
                logger.error(f"❌ {error}")
                return None, error
            
            answer = response.text.strip()
            logger.info(f"✅ Received response from Gemini ({len(answer)} characters)")
            
            return answer, None
            
        except Exception as e:
            error = f"Gemini API call failed: {str(e)}"
            logger.error(f"❌ {error}")
            return None, error
    
    def format_response(
        self,
        question: str,
        answer: str,
        retrieved_chunks: List[Dict],
        search_time_ms: float,
        fallback_used: bool = False
    ) -> Dict:
        """
        Format response with answer and source attribution
        
        Args:
            question: Original question
            answer: Generated answer
            retrieved_chunks: Retrieved context chunks
            search_time_ms: Time taken for search
            fallback_used: Whether Wikipedia fallback was used
            
        Returns:
            dict: Formatted response
        """
        
        logger.debug("Formatting response...")
        
        # Build sources list
        sources = []
        for chunk in retrieved_chunks:
            source = {
                "source_type": "document",
                "source_name": chunk['file_id'],
                "page_number": chunk.get('page_number'),
                "section_heading": chunk.get('section_heading'),
                "evidence_snippet": chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text'],
                "relevance_score": chunk['similarity_score'],
                "wikipedia_url": None
            }
            sources.append(source)
        
        # Build retrieval details
        retrieval_details = {
            "search_time_ms": search_time_ms,
            "documents_searched": len(self.faiss_store.metadata),
            "chunks_retrieved": len(retrieved_chunks),
            "fallback_used": fallback_used,
            "retrieval_strategy": "wikipedia_search" if fallback_used else "document_search"
        }
        
        response = {
            "answer": answer,
            "sources": sources,
            "retrieval_details": retrieval_details
        }
        
        return response
    
    def answer_question(
        self,
        question: str,
        top_k: int = None,
        relevance_threshold: float = None
    ) -> Tuple[Dict, Optional[str]]:
        """
        Complete RAG pipeline: retrieve + generate answer
        
        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            relevance_threshold: Minimum similarity threshold
            
        Returns:
            Tuple[Dict, Optional[str]]: (response, error_message)
        """
        
        start_time = time.time()
        logger.info(f"📝 Answering question: {question[:50]}...")
        
        try:
            # Step 1: Retrieve context
            logger.info("Step 1: Retrieving context from documents...")
            retrieved_chunks, error = self.retrieve_context(
                question=question,
                top_k=top_k,
                relevance_threshold=relevance_threshold
            )
            
            if error:
                logger.error(f"❌ Retrieval failed: {error}")
                return {}, error
            
            # Step 2: Check if relevant context found
            if not retrieved_chunks:
                error = "No relevant context found in documents"
                logger.warning(f"⚠️ {error}")
                return {}, error
            
            # Step 3: Build prompt
            logger.info("Step 2: Building prompt with context...")
            prompt = self.build_prompt(question, retrieved_chunks)
            
            # Step 4: Call Gemini
            logger.info("Step 3: Calling Gemini API...")
            answer, error = self.call_gemini(prompt)
            
            if error:
                logger.error(f"❌ Gemini call failed: {error}")
                return {}, error
            
            # Step 5: Format response
            logger.info("Step 4: Formatting response...")
            search_time_ms = (time.time() - start_time) * 1000
            
            response = self.format_response(
                question=question,
                answer=answer,
                retrieved_chunks=retrieved_chunks,
                search_time_ms=search_time_ms,
                fallback_used=False
            )
            
            logger.info(f"✅ Question answered in {search_time_ms:.0f}ms")
            
            return response, None
            
        except Exception as e:
            error = f"Answer generation failed: {str(e)}"
            logger.error(f"❌ {error}")
            return {}, error
    
    def get_health_status(self) -> Dict:
        """
        Get RAG service health status
        
        Returns:
            dict: Health status information
        """
        
        faiss_stats = self.faiss_store.get_stats()
        embedding_health = self.embedding_service.check_health()
        
        health = {
            "status": "healthy" if self.configured else "degraded",
            "gemini_configured": self.configured,
            "gemini_model": settings.gemini_model,
            "faiss_ready": faiss_stats.get("total_vectors", 0) > 0,
            "faiss_stats": faiss_stats,
            "embedding_service": embedding_health
        }
        
        return health


# ============ SINGLETON ============

_rag_service = None


def get_rag_service() -> RAGService:
    """
    Get singleton RAG service instance
    
    Returns:
        RAGService: Global RAG service instance
    """
    global _rag_service
    
    if _rag_service is None:
        _rag_service = RAGService()
    
    return _rag_service