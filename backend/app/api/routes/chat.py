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
        # ============ STEP 1: TRY DOCUMENTS SEARCH ============
        
        if request.search_type in ["documents_only", "hybrid"]:
            logger.info("Step 1: Searching documents...")
            
            rag_service = get_rag_service()
            response, error = rag_service.answer_question(
                question=request.question,
                top_k=request.top_k,
                relevance_threshold=request.relevance_threshold
            )
            
            if error is None and response:
                # Success - answer found in documents
                logger.info("✅ Answer found in documents")
                return ChatResponse(
                    status="success",
                    data=response
                )
            else:
                # No relevant context found
                logger.warning(f"⚠️ No relevant context in documents: {error}")
                
                # If documents_only mode, return error
                if request.search_type == "documents_only":
                    logger.info("Document-only mode: returning error")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail={
                            "status": "error",
                            "message": "No relevant information found in uploaded documents",
                            "error_code": "NO_RELEVANT_CONTEXT"
                        }
                    )
                
                # Fall through to Wikipedia (hybrid mode)
                logger.info("Hybrid mode: falling back to Wikipedia...")
        
        # ============ STEP 2: WIKIPEDIA FALLBACK ============
        
        if request.search_type in ["wikipedia_only", "hybrid"]:
            logger.info("Step 2: Searching Wikipedia as fallback...")
            
            wiki_service = WikipediaService()
            
            # Search Wikipedia
            wiki_results, error = wiki_service.search(request.question)
            
            if error or not wiki_results:
                logger.error(f"❌ Wikipedia search failed: {error}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "error",
                        "message": "Failed to find relevant information in documents or Wikipedia",
                        "error_code": "NO_CONTEXT_AVAILABLE"
                    }
                )
            
            # Build context from Wikipedia results
            wiki_context = wiki_service.build_context(wiki_results)
            
            # Call Gemini with Wikipedia context
            answer, error = rag_service.call_gemini(wiki_context)
            
            if error or not answer:
                logger.error(f"❌ Gemini call with Wikipedia context failed: {error}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "error",
                        "message": "Failed to generate answer",
                        "error_code": "GENERATION_FAILED"
                    }
                )
            
            # Format Wikipedia response
            sources = []
            for result in wiki_results:
                source = {
                    "source_type": "wikipedia",
                    "source_name": f"Wikipedia - {result['title']}",
                    "wikipedia_url": result['url'],
                    "evidence_snippet": result['summary'][:200] + "..." if len(result['summary']) > 200 else result['summary'],
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
                    "chunks_retrieved": 0,
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