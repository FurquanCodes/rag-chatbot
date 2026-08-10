import logging
import time
from typing import Dict, List, Optional, Tuple

import google.generativeai as genai

from app.services.embedding_service import EmbeddingService
from app.storage.faiss_store import get_faiss_store
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.faiss_store = get_faiss_store()
        self.configured = False
        self._check_config()

    def _check_config(self) -> bool:
        key = (settings.google_api_key or "").strip()
        if key and not ("your_" in key.lower() or "here" in key.lower()):
            try:
                genai.configure(api_key=key)
                self.configured = True
            except Exception:
                self.configured = False
        else:
            self.configured = False
        return self.configured

    def retrieve_context(
        self,
        question: str,
        top_k: int = None,
        relevance_threshold: float = None
    ) -> Tuple[List[Dict], Optional[str]]:
        if top_k is None:
            top_k = settings.top_k_retrieval
        if relevance_threshold is None:
            relevance_threshold = settings.relevance_threshold

        try:
            question_embedding = self.embedding_service.embed_question(question)
            if question_embedding is None:
                return [], "Failed to embed question"

            retrieved_chunks, error = self.faiss_store.search(
                query_vector=question_embedding,
                k=top_k,
                threshold=relevance_threshold
            )
            if error:
                return [], error
            return retrieved_chunks, None
        except Exception as e:
            return [], f"Context retrieval failed: {str(e)}"

    def build_prompt(
        self,
        question: str,
        context_chunks: List[Dict]
    ) -> str:
        system_instruction = (
            "You are a helpful AI assistant specialized in answering questions based on provided documents.\n\n"
            "IMPORTANT RULES:\n"
            "1. ALWAYS answer based ONLY on the provided context\n"
            "2. If the context doesn't contain the answer, say: \"I don't have information about this in the documents\"\n"
            "3. Cite the specific document/section when possible\n"
            "4. Be concise and accurate\n\n"
            "CONTEXT FROM DOCUMENTS:\n"
            "═══════════════════════════════════════════════════════════════════\n"
        )

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
        system_instruction += (
            "═══════════════════════════════════════════════════════════════════\n\n"
            "QUESTION:\n"
            "─────────────────────────────────────────────────────────────────────\n"
        )
        system_instruction += question
        system_instruction += "\n─────────────────────────────────────────────────────────────────────\n"
        system_instruction += "\nPROVIDE YOUR ANSWER BELOW:\n"
        return system_instruction

    def call_gemini(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        self._check_config()
        if not self.configured:
            return None, "Google Gemini API key not configured or invalid"

        models_to_try = [settings.gemini_model, "gemini-3.6-flash", "gemini-flash-latest"]
        seen_models = []
        last_error = None

        for model_name in models_to_try:
            if not model_name or model_name in seen_models:
                continue
            seen_models.append(model_name)

            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1024,
                        temperature=0.7,
                        top_p=0.9
                    )
                )
                if response and response.text:
                    return response.text.strip(), None
            except Exception as e:
                last_error = str(e)
                if "API_KEY_INVALID" in last_error or "API key" in last_error or "400" in last_error or "403" in last_error:
                    if "404" not in last_error and "not found" not in last_error.lower():
                        self.configured = False
                        break

        return None, f"Gemini API call failed: {last_error}"

    def format_response(
        self,
        question: str,
        answer: str,
        retrieved_chunks: List[Dict],
        search_time_ms: float,
        fallback_used: bool = False
    ) -> Dict:
        sources = []
        for chunk in retrieved_chunks:
            source = {
                "source_type": "document",
                "source_name": chunk.get('filename') or chunk['file_id'],
                "page_number": chunk.get('page_number'),
                "section_heading": chunk.get('section_heading'),
                "evidence_snippet": chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text'],
                "relevance_score": chunk['similarity_score'],
                "wikipedia_url": None
            }
            sources.append(source)

        retrieval_details = {
            "search_time_ms": search_time_ms,
            "documents_searched": len(self.faiss_store.metadata),
            "chunks_retrieved": len(retrieved_chunks),
            "fallback_used": fallback_used,
            "retrieval_strategy": "wikipedia_search" if fallback_used else "document_search"
        }

        return {
            "answer": answer,
            "sources": sources,
            "retrieval_details": retrieval_details
        }

    def answer_question(
        self,
        question: str,
        top_k: int = None,
        relevance_threshold: float = None
    ) -> Tuple[Dict, Optional[str]]:
        start_time = time.time()
        try:
            retrieved_chunks, error = self.retrieve_context(
                question=question,
                top_k=top_k,
                relevance_threshold=relevance_threshold
            )
            if error:
                return {}, error

            if not retrieved_chunks:
                return {}, "No relevant context found in documents"

            prompt = self.build_prompt(question, retrieved_chunks)
            answer, gemini_error = self.call_gemini(prompt)

            search_time_ms = (time.time() - start_time) * 1000

            if gemini_error or not answer:
                snippet_text = "\n\n".join([f"• [{c.get('filename', 'Doc')}]: {c['text'][:300]}..." for c in retrieved_chunks[:3]])
                answer = (
                    "⚠️ **Google Gemini API Key required for AI answer generation**\n\n"
                    "Found relevant context in your uploaded document(s):\n"
                    f"{snippet_text}\n\n"
                    "👉 **To enable full AI answer generation**, please add a valid `GOOGLE_API_KEY` to your `backend/.env` file."
                )

            response = self.format_response(
                question=question,
                answer=answer,
                retrieved_chunks=retrieved_chunks,
                search_time_ms=search_time_ms,
                fallback_used=False
            )
            return response, None
        except Exception as e:
            return {}, f"Answer generation failed: {str(e)}"

    def get_health_status(self) -> Dict:
        faiss_stats = self.faiss_store.get_stats()
        embedding_health = self.embedding_service.check_health()
        return {
            "status": "healthy" if self.configured else "degraded",
            "gemini_configured": self.configured,
            "gemini_model": settings.gemini_model,
            "faiss_ready": faiss_stats.get("total_vectors", 0) > 0,
            "faiss_stats": faiss_stats,
            "embedding_service": embedding_health
        }


_rag_service = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service