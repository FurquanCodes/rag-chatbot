"""
RAG Service
Retrieves relevant context and generates answers using Gemini
RAG = Retrieval Augmented Generation
"""

import logging
from typing import List, Optional, Tuple, Dict
import time
import re

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
        relevance_threshold: float = None,
        file_id: Optional[str] = None
    ) -> Tuple[List[Dict], Optional[str]]:
        if top_k is None:
            top_k = settings.top_k_retrieval
        if relevance_threshold is None:
            relevance_threshold = 0.0
        
        logger.info(f"🔍 Retrieving context for question: {question[:50]}... (file_id={file_id})")
        
        try:
            logger.debug("Step 1: Embedding question...")
            question_embedding = self.embedding_service.embed_question(question)
            
            if question_embedding is None:
                error = "Failed to embed question"
                logger.error(f"❌ {error}")
                return [], error
            
            target_fnum = None
            target_fname = None
            
            import re
            m_fnum = re.search(r'(?:File|Document|Doc)\s*#?\s*(\d+)', question, re.IGNORECASE)
            if m_fnum:
                try:
                    target_fnum = int(m_fnum.group(1))
                except ValueError:
                    pass
            
            if not target_fnum:
                ordinals = {
                    "first": 1, "1st": 1,
                    "second": 2, "2nd": 2,
                    "third": 3, "3rd": 3,
                    "fourth": 4, "4th": 4,
                    "fifth": 5, "5th": 5
                }
                m_ord = re.search(r'\b(first|1st|second|2nd|third|3rd|fourth|4th|fifth|5th)\s+(?:file|document|doc)\b', question, re.IGNORECASE)
                if m_ord:
                    ord_word = m_ord.group(1).lower()
                    target_fnum = ordinals.get(ord_word)

            for meta in self.faiss_store.metadata:
                fn = meta.get("filename")
                if fn and len(fn) > 3:
                    fn_base = fn.rsplit('.', 1)[0] if '.' in fn else fn
                    if fn.lower() in question.lower() or (len(fn_base) >= 4 and fn_base.lower() in question.lower()):
                        target_fname = fn
                        break
            
            unique_files_in_store = len(set(m.get("file_id") for m in self.faiss_store.metadata if m.get("file_id")))
            effective_k = max(top_k, min(15, unique_files_in_store * 5)) if not target_fnum and not target_fname else top_k

            logger.debug(f"Step 2: Searching FAISS (k={effective_k}, file_num={target_fnum}, filename={target_fname})...")
            retrieved_chunks, error = self.faiss_store.search(
                query_vector=question_embedding,
                k=effective_k,
                threshold=relevance_threshold,
                file_id=file_id,
                target_file_number=target_fnum,
                target_filename=target_fname,
                raw_query=question
            )
            
            if not retrieved_chunks and self.faiss_store.vector_count > 0:
                logger.info("Retrying FAISS search with zero threshold to prefer uploaded document content")
                retrieved_chunks, error = self.faiss_store.search(
                    query_vector=question_embedding,
                    k=effective_k,
                    threshold=0.0,
                    file_id=file_id,
                    target_file_number=target_fnum,
                    target_filename=target_fname,
                    raw_query=question
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
        
        logger.debug("Building prompt with context")
        system_instruction = """You are an intelligent AI assistant specialized in answering user questions using provided document context across one or multiple documents.

IMPORTANT INSTRUCTIONS:
1. Answer the user's question clearly, thoroughly, and comprehensively using the provided document context, document file names, and document metadata.
2. If the user asks about a person, student, author, or topic associated with a document (e.g. if the file name contains 'REHAN GHAZI 928091' or the document mentions 'Syed Muhammad Ahmad Raza'), identify who they are in relation to the document (e.g., student name, roll number, course, institution, instructor, and the topic of their submission like Reinforcement Learning) and explain all related details thoroughly.
3. If the user asks about a specific document (e.g., "Document 1", "Document 2", or a specific filename), extract and answer strictly using information from that document.
4. If the user asks to compare, contrast, or summarize across multiple documents, clearly distinguish facts from each document by citing the document name/number.
5. Structure your response logically with clear headings, paragraphs, and bullet points.
6. Synthesize and explain all details present in the context blocks below to answer the question as completely as possible.
7. DO NOT include any file download links or URLs.
8. Base your answer strictly on the facts and information in the provided document context and document headers.
9. If the provided document context and file headers truly do NOT contain any relevant information related to the question, only then reply EXACTLY with: "Unable to get information about it from documents."

CONTEXT FROM DOCUMENTS:
═══════════════════════════════════════════════════════════════════
"""
        
        context_text = ""
        for chunk in context_chunks:
            f_num = chunk.get('file_number', 1)
            raw_fname = chunk.get('filename') or self.faiss_store.get_filename(chunk['file_id'])
            if not raw_fname or (len(raw_fname) == 36 and raw_fname.count('-') == 4):
                doc_label = f"Document {f_num}"
            else:
                doc_label = raw_fname
                
            p_num = chunk.get('page_number', 1)
            l_start = chunk.get('line_start', 1)
            l_end = chunk.get('line_end', 1)
            f_type = (chunk.get('file_type') or '').lower()
            unit = "Slide" if f_type == "pptx" else "Page"
            orig_text = chunk.get('original_text') or chunk['text']
            
            chunk_marker = f"\n[BLOCK: File {f_num} — {doc_label} | {unit}: {p_num} | Lines: {l_start}–{l_end}]\n"
            context_text += chunk_marker + orig_text + "\n\n"
        
        system_instruction += context_text
        
        system_instruction += """═══════════════════════════════════════════════════════════════════

QUESTION:
─────────────────────────────────────────────────────────────────────
"""
        system_instruction += question
        system_instruction += "\n─────────────────────────────────────────────────────────────────────\n"
        system_instruction += "\nPROVIDE YOUR COMPREHENSIVE ANSWER BELOW:\n"
        
        logger.debug(f"Prompt built: {len(system_instruction)} characters")
        
        return system_instruction
    
    def call_gemini(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        if not self.configured:
            error = "Gemini API not configured"
            logger.error(f"❌ {error}")
            return None, error
        
        models_to_try = [settings.gemini_model, "gemini-3.6-flash", "gemini-3.7-flash", "gemini-flash-latest", "gemini-3-flash-preview", "gemini-3.5-flash"]
        seen_models = set()
        last_error = None
        
        for model_name in models_to_try:
            if not model_name or model_name in seen_models:
                continue
            seen_models.add(model_name)
            try:
                logger.info(f"📞 Calling Gemini API with model: {model_name}...")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=2048,
                        temperature=0.7,
                        top_p=0.9
                    )
                )
                if response and response.text:
                    answer = response.text.strip()
                    logger.info(f"✅ Received response from Gemini model {model_name} ({len(answer)} characters)")
                    return answer, None
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Gemini API model {model_name} failed: {last_error}")
        
        error = f"Gemini API call failed: {last_error}"
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
        logger.debug("Formatting response...")
        
        sources = []
        seen_keys = set()
        
        stopwords = {'what', 'who', 'where', 'when', 'why', 'how', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'the', 'a', 'an', 'in', 'on', 'of', 'for', 'to', 'and', 'or', 'it', 'this', 'that', 'me', 'my', 'give', 'tell', 'explain', 'show', 'written', 'about', 'document'}
        q_words = [w.lower() for w in re.findall(r'\w+', question) if w.lower() not in stopwords]
        
        for i, chunk in enumerate(retrieved_chunks):
            f_num = chunk.get('file_number', 1)
            raw_sname = chunk.get('filename') or self.faiss_store.get_filename(chunk['file_id'])
            if not raw_sname or (len(raw_sname) == 36 and raw_sname.count('-') == 4):
                s_name = f"Document {f_num}"
            else:
                s_name = raw_sname
                
            p_num = chunk.get('page_number')
            l_start = chunk.get('line_start')
            l_end = chunk.get('line_end')
            orig_text = chunk.get('original_text') or chunk['text']
            orig_text_lower = orig_text.lower()
            
            has_q_match = any(qw in orig_text_lower for qw in q_words) if q_words else True
            if i > 0 and q_words and not has_q_match:
                continue
            
            best_snippet = ""
            lines = [ln.strip() for ln in orig_text.split('\n') if ln.strip()]
            for ln in lines:
                if any(qw in ln.lower() for qw in q_words):
                    best_snippet = ln
                    break
            if not best_snippet:
                for ln in lines:
                    if not re.match(r'^(page\s+\d+|slide\s+\d+|\d+\s*of\s*\d+)$', ln.lower()):
                        best_snippet = ln
                        break
            if not best_snippet:
                best_snippet = lines[0] if lines else orig_text[:150]
                
            if len(best_snippet) > 180:
                best_snippet = best_snippet[:177] + "..."
                
            dedup_key = (f_num, s_name, p_num)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            
            source = {
                "source_type": "document",
                "file_number": f_num,
                "source_name": s_name,
                "file_type": chunk.get('file_type'),
                "page_number": p_num,
                "line_start": l_start,
                "line_end": l_end,
                "original_text": best_snippet,
                "evidence_snippet": best_snippet,
                "relevance_score": chunk['similarity_score'],
                "wikipedia_url": None,
                "document_url": None
            }
            sources.append(source)
            if len(sources) >= 3:
                break
        
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
        relevance_threshold: float = None,
        file_id: Optional[str] = None
    ) -> Tuple[Dict, Optional[str]]:
        start_time = time.time()
        logger.info(f"📝 Answering question: {question[:50]}... (file_id={file_id})")
        
        try:
            logger.info("Step 1: Retrieving context from documents...")
            retrieved_chunks, error = self.retrieve_context(
                question=question,
                top_k=top_k,
                relevance_threshold=relevance_threshold,
                file_id=file_id
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
                logger.warning(f"⚠️ Gemini call failed ({error}), building direct response from document context")
                context_snippets = "\n\n".join([f"Excerpt {i+1}:\n{chunk['text']}" for i, chunk in enumerate(retrieved_chunks[:3])])
                answer = f"Relevant information from your document:\n\n{context_snippets}"
            
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