"""
Chat Routes
Handles user questions and RAG-based answers
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

# Local imports
from app.utils.config import settings
from app.utils.logger import get_logger
from app.utils.constants import API_ROUTES
from bs4 import BeautifulSoup
from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import get_rag_service
from app.services.wikipedia_service import WikipediaService

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["Chat"])


# ============ CHAT ENDPOINT ============

@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat endpoint - Answer questions using RAG
    
    Complete pipeline:
    1. Search uploaded documents (FAISS)
    2. If relevant context found:
       - Build prompt with context
       - Call Gemini API
       - Return answer with sources
    3. If NO relevant context found:
       - Search Wikipedia as fallback
       - Use Wikipedia context
       - Call Gemini API
       - Return answer with Wikipedia sources
    
    Args:
        request: ChatRequest with question and options
        
    Returns:
        ChatResponse: Answer with sources and retrieval details
        
    Raises:
        HTTPException: If processing fails
    """
    
    logger.info(f"💬 Chat request: {request.question[:50]}...")
    logger.info(f"   Collection: {request.collection_id}")
    logger.info(f"   Strategy: {request.search_type}")
    
    try:
        rag_service = get_rag_service()
        
        if request.search_type in ["documents_only", "hybrid"]:
            logger.info(f"Step 1: Searching documents (first preference)... (file_id={request.file_id})")
            
            retrieved_chunks, error = rag_service.retrieve_context(
                question=request.question,
                top_k=request.top_k,
                relevance_threshold=0.0,
                file_id=request.file_id
            )
            
            if retrieved_chunks and not error:
                response, err = rag_service.answer_question(
                    question=request.question,
                    top_k=request.top_k,
                    relevance_threshold=0.0,
                    file_id=request.file_id
                )
                if response and not err:
                    logger.info("✅ Primary choice satisfied: Returning answer from documents")
                    return ChatResponse(
                        status="success",
                        data=response
                    )
            
            if request.search_type == "documents_only":
                logger.info("Document-only mode: returning unable to get information response")
                return ChatResponse(
                    status="success",
                    data={
                        "answer": "Unable to get information about it.",
                        "sources": [],
                        "retrieval_details": {
                            "search_time_ms": 0,
                            "documents_searched": 0,
                            "chunks_retrieved": 0,
                            "fallback_used": False,
                            "retrieval_strategy": "document_search"
                        }
                    }
                )
            
            logger.info("Hybrid mode: no document chunks found, falling back to Wikipedia as second preference...")
        
        if request.search_type in ["wikipedia_only", "hybrid"]:
            logger.info("Step 2: Searching Wikipedia as fallback...")
            
            wiki_service = WikipediaService()
            
            wiki_results, error = wiki_service.search(request.question)
            
            if error or not wiki_results:
                logger.warning(f"⚠️ Wikipedia search returned no usable results: {error}")
                return ChatResponse(
                    status="success",
                    data={
                        "answer": "Unable to get information about it.",
                        "sources": [],
                        "retrieval_details": {
                            "search_time_ms": 0,
                            "documents_searched": 0,
                            "chunks_retrieved": 0,
                            "fallback_used": True,
                            "retrieval_strategy": "wikipedia_search"
                        }
                    }
                )
            
            wiki_context = wiki_service.build_context(request.question, wiki_results)
            
            answer, error = rag_service.call_gemini(wiki_context)
            
            if error or not answer:
                logger.warning(f"⚠️ Gemini call with Wikipedia context failed: {error}")
                answer = "Unable to get information about it."
            
            sources = []
            if wiki_results:
                result = wiki_results[0]
                raw_text = result.get('summary') or result.get('snippet') or ''
                clean_snippet = BeautifulSoup(raw_text, "html.parser").get_text()
                if len(clean_snippet) > 200:
                    clean_snippet = clean_snippet[:200] + "..."
                
                source = {
                    "source_type": "wikipedia",
                    "source_name": f"Wikipedia - {result['title']}",
                    "wikipedia_url": result['url'],
                    "evidence_snippet": clean_snippet,
                    "relevance_score": result.get('relevance_score', 0.8),
                    "page_number": None,
                    "section_heading": None
                }
                sources.append(source)
            
            response = {
                "answer": answer,
                "sources": sources,
                "retrieval_details": {
                    "search_time_ms": 0,
                    "documents_searched": 0,
                    "chunks_retrieved": len(wiki_results),
                    "fallback_used": True,
                    "retrieval_strategy": "wikipedia_search"
                }
            }
            
            logger.info("✅ Answer generated from Wikipedia")
            return ChatResponse(
                status="success",
                data=response
            )
        
        # Should never reach here
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "Invalid search strategy",
                "error_code": "INVALID_STRATEGY"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"❌ Unexpected error in chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error", 
                "message": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "details": str(e) if settings.api_env == "development" else None
            }
        )