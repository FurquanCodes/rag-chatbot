import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status

from app.utils.config import settings
from app.utils.logger import get_logger
from app.utils.constants import API_ROUTES
from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import get_rag_service
from app.services.wikipedia_service import WikipediaService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        rag_service = get_rag_service()

        if request.search_type in ["documents_only", "hybrid"]:
            response, error = rag_service.answer_question(
                question=request.question,
                top_k=request.top_k,
                relevance_threshold=request.relevance_threshold
            )

            if error is None and response:
                return ChatResponse(
                    status="success",
                    data=response
                )
            else:
                if request.search_type == "documents_only":
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail={
                            "status": "error",
                            "message": "No relevant information found in uploaded documents",
                            "error_code": "NO_RELEVANT_CONTEXT"
                        }
                    )

        if request.search_type in ["wikipedia_only", "hybrid"]:
            wiki_service = WikipediaService()
            wiki_results, error = wiki_service.search(request.question)

            if error or not wiki_results:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "status": "error",
                        "message": "Failed to find relevant information in documents or Wikipedia",
                        "error_code": "NO_CONTEXT_AVAILABLE"
                    }
                )

            wiki_context = wiki_service.build_context(wiki_results)
            answer, gemini_error = rag_service.call_gemini(wiki_context)

            if gemini_error or not answer:
                summaries_text = "\n\n".join([f"• [{r['title']}]: {r['summary'][:250]}..." for r in wiki_results[:3]])
                answer = (
                    "⚠️ **Google Gemini API Key required for AI answer generation**\n\n"
                    "Found relevant information on Wikipedia:\n"
                    f"{summaries_text}\n\n"
                    "👉 **To enable full AI answer generation**, please add a valid `GOOGLE_API_KEY` to your `backend/.env` file."
                )

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

            return ChatResponse(
                status="success",
                data=response
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "Invalid search strategy",
                "error_code": "INVALID_STRATEGY"
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Internal server error",
                "error_code": "INTERNAL_ERROR",
                "details": str(e) if settings.api_env == "development" else None
            }
        )