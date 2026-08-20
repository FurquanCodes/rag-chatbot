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

# Global state for uploaded images in the current chat session
ACTIVE_IMAGES = []

def clear_active_images():
    global ACTIVE_IMAGES
    ACTIVE_IMAGES = []

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
            
            # Check if this is a comparison / multi-topic query
            comparison_indicators = ["differentiate", "difference", "compare", "versus", "vs", "between", "contrast", "both"]
            is_comparison = any(re.search(rf'\b{ind}\b', question, re.IGNORECASE) for ind in comparison_indicators)

            # If user asks to compare/differentiate, do not lock to target_fnum or target_fname.
            # Only clear file_id if it wasn't explicitly provided.
            if is_comparison:
                if not file_id:
                    file_id = None
                target_fnum = None
                target_fname = None

            unique_files_in_store = len(set(m.get("file_id") for m in self.faiss_store.metadata if m.get("file_id")))
            effective_k = max(top_k, min(20, unique_files_in_store * 6)) if not target_fnum and not target_fname else top_k

            retrieved_chunks = []
            
            # Primary search
            primary_chunks, error = self.faiss_store.search(
                query_vector=question_embedding,
                k=effective_k,
                threshold=relevance_threshold,
                file_id=file_id,
                target_file_number=target_fnum,
                target_filename=target_fname,
                raw_query=question
            )
            if primary_chunks:
                retrieved_chunks.extend(primary_chunks)

            # Multi-topic / Cross-document retrieval:
            if not target_fnum and not target_fname and unique_files_in_store > 1:
                # Topic splitting for "differentiate between X and Y" or "compare X and Y"
                m_comp = re.search(r'(?:between|compare|contrast|versus|vs)\s+(.+?)\s+(?:and|versus|vs|with)\s+(.+)', question, re.IGNORECASE)
                sub_queries = []
                if m_comp:
                    q_part1 = m_comp.group(1).strip(" ?.,;")
                    q_part2 = m_comp.group(2).strip(" ?.,;")
                    if len(q_part1) >= 3: sub_queries.append(q_part1)
                    if len(q_part2) >= 3: sub_queries.append(q_part2)
                
                # Check for document names mentioned in query
                for meta in self.faiss_store.metadata:
                    fn = meta.get("filename")
                    if fn and len(fn) > 3:
                        fn_base = fn.rsplit('.', 1)[0] if '.' in fn else fn
                        if fn_base.lower() in question.lower() and fn_base not in sub_queries:
                            sub_queries.append(fn_base)

                # Search sub-queries
                for sq in sub_queries:
                    sq_emb = self.embedding_service.embed_question(sq)
                    if sq_emb:
                        sq_chunks, _ = self.faiss_store.search(
                            query_vector=sq_emb,
                            k=5,
                            threshold=0.0,
                            file_id=None,
                            raw_query=sq
                        )
                        if sq_chunks:
                            retrieved_chunks.extend(sq_chunks)
                
                # Also ensure top chunks from EACH distinct file in store are considered
                file_ids_in_store = list(set(m.get("file_id") for m in self.faiss_store.metadata if m.get("file_id")))
                for fid in file_ids_in_store:
                    f_chunks, _ = self.faiss_store.search(
                        query_vector=question_embedding,
                        k=4,
                        threshold=0.0,
                        file_id=fid,
                        raw_query=question
                    )
                    if f_chunks:
                        retrieved_chunks.extend(f_chunks)

            # Deduplicate chunks preserving highest similarity score
            seen_chunk_ids = set()
            unique_chunks = []
            retrieved_chunks.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            for c in retrieved_chunks:
                cid = c.get("chunk_id")
                if cid and cid not in seen_chunk_ids:
                    seen_chunk_ids.add(cid)
                    unique_chunks.append(c)
            
            retrieved_chunks = unique_chunks[:effective_k]

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
            
            if error and not retrieved_chunks:
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
        
        system_instruction = """You are a highly precise document-grounding QA assistant.
Your primary role is to retrieve and return EXACT wording from the uploaded documents.

IMPORTANT INSTRUCTIONS:
1. EXACT SOURCE MODE IS THE DEFAULT. Whenever possible, answer the question by returning the exact, verbatim text from the provided context. Do NOT paraphrase, summarize, or rewrite the text in your own words unless explicitly asked to do so by the user.
2. If the user asks for a summary or explanation, you may summarize or explain, but YOU MUST STILL accurately represent the facts from the source without inventing information.
3. If the answer requires information from multiple files, structure your response by separating the information by file. 
   Example format:
   ### File 1 — Research.pdf
   [Exact text]
   
   ### File 2 — Project_Report.pdf
   [Exact text]
4. Do NOT invent, guess, or hallucinate citations (file numbers, page numbers, line numbers). All citation information must come from the headers provided in the context blocks below.
5. If the user asks about a specific file or document by its number or name, use only the context blocks that match that file.
6. DO NOT include any file download links or raw URLs in your answer.
7. Base your answer strictly on the facts and information in the provided document context and document headers.
8. If the provided context does NOT contain information relevant to the question, reply EXACTLY with: "I couldn't find this information in the uploaded documents." Do not use your general knowledge to invent an answer.

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
    
    def call_gemini(self, prompt: str | list) -> Tuple[Optional[str], Optional[str]]:
        if not self.configured:
            error = "Gemini API not configured"
            logger.error(f"❌ {error}")
            return None, error
        
        models_to_try = [settings.gemini_model, "gemini-3.6-flash", "gemini-3.7-flash", "gemini-flash-latest", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-3-flash-preview", "gemini-3.5-flash"]
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
                
            # Explicit Source Validation
            # Verify file number, name, text existence directly from metadata
            if not f_num or not s_name or not orig_text or l_start is None:
                continue
                
            dedup_key = (f_num, s_name, p_num, l_start)
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
    
    def get_unique_files(self) -> List[Dict]:
        """Extract all unique files from FAISS store."""
        files = {}
        for meta in self.faiss_store.metadata:
            fid = meta.get("file_id")
            if fid and fid not in files:
                files[fid] = {
                    "file_id": fid,
                    "file_number": meta.get("file_number", 1),
                    "filename": meta.get("filename", f"Document {meta.get('file_number', 1)}")
                }
        return sorted(list(files.values()), key=lambda x: x["file_number"])

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
            q_lower = question.lower()
            import re
            
            # --- IMAGE ROUTING ---
            is_all_images = False
            if ACTIVE_IMAGES and re.search(r'\b(all|every|each)\b.*\b(images?|pictures?|photos?)\b', q_lower):
                is_all_images = True
            elif ACTIVE_IMAGES and "explain all" in q_lower and ("image" in q_lower or "upload" in q_lower):
                is_all_images = True
                
            if is_all_images:
                logger.info("Detected ALL_IMAGES intent. Initiating per-image processing...")
                from PIL import Image
                final_answer_blocks = []
                all_sources = []
                
                for idx, img_data in enumerate(ACTIVE_IMAGES, 1):
                    fname = img_data["file_name"]
                    img = Image.open(img_data["file_path"])
                    prompt = [f"Explain this image in detail. Address the user's question: {question}\nProvide a detailed Image Overview, Text Detected, and Visual Analysis.", img]
                    answer, err = self.call_gemini(prompt)
                    if err:
                        answer = f"Failed to analyze image: {err}"
                        
                    final_answer_blocks.append(f"# Image {idx} — {fname}\n\n{answer}")
                    all_sources.append({
                        "file_id": img_data["image_id"],
                        "file_number": idx,
                        "source_name": fname,
                        "file_type": "image",
                        "page_number": 1,
                        "line_start": 1,
                        "line_end": 1,
                        "evidence_snippet": "Visual Analysis",
                        "relevance_score": 1.0
                    })
                    
                final_answer = "\n\n------------------------------------------------\n\n".join(final_answer_blocks)
                return {
                    "answer": final_answer,
                    "sources": all_sources,
                    "retrieval_details": {"search_time_ms": (time.time() - start_time) * 1000, "documents_searched": 0, "chunks_retrieved": 0, "fallback_used": False, "retrieval_strategy": "multi_image_vision"}
                }, None

            if ACTIVE_IMAGES and ("image" in q_lower or "photo" in q_lower or "picture" in q_lower or "chart" in q_lower or "graph" in q_lower or "screenshot" in q_lower or "diagram" in q_lower or "table" in q_lower or "this" in q_lower or "text" in q_lower or len(self.faiss_store.metadata) == 0):
                logger.info("Detected multimodal intent with active images.")
                from PIL import Image
                retrieved_chunks, _ = self.retrieve_context(question=question, top_k=top_k, relevance_threshold=relevance_threshold, file_id=file_id)
                
                if retrieved_chunks:
                    text_prompt = self.build_prompt(question, retrieved_chunks)
                    multimodal_prompt = "You are a multimodal assistant. You have been provided with both images and document context. Use the provided images as primary visual evidence and the document context as textual evidence to answer the question.\n\n" + text_prompt
                else:
                    multimodal_prompt = f"You are a helpful multimodal AI assistant. Answer the user's question clearly and accurately based on the provided images and OCR text.\n\nUser Question: {question}\n\nInstructions:\n1. If the user's input is a simple greeting, acknowledgment (like 'ok', 'thanks', 'yes'), or conversational, respond naturally and conversationally without describing the image.\n2. Otherwise, answer directly based on the visual and text context of the images."
                
                prompt_content = [multimodal_prompt]
                all_sources = []
                
                for idx, img_data in enumerate(ACTIVE_IMAGES, 1):
                    prompt_content.append(f"\n--- Image {idx}: {img_data['file_name']} ---")
                    prompt_content.append(Image.open(img_data["file_path"]))
                    if img_data['ocr_text']:
                        prompt_content.append(f"OCR Text detected from Image {idx}:\n{img_data['ocr_text']}")
                    
                    all_sources.append({
                        "file_id": img_data["image_id"],
                        "file_number": idx,
                        "source_name": img_data["file_name"],
                        "file_type": "image",
                        "page_number": 1,
                        "line_start": 1,
                        "line_end": 1,
                        "evidence_snippet": "Visual Analysis + OCR",
                        "relevance_score": 1.0
                    })
                    
                answer, err = self.call_gemini(prompt_content)
                if err:
                    answer = f"Failed to analyze multimodal request: {err}"
                
                if retrieved_chunks:
                    doc_response = self.format_response(question, answer, retrieved_chunks, 0)
                    all_sources.extend(doc_response["sources"])
                    
                return {
                    "answer": answer,
                    "sources": all_sources,
                    "retrieval_details": {"search_time_ms": (time.time() - start_time) * 1000, "documents_searched": len(self.faiss_store.metadata), "chunks_retrieved": len(retrieved_chunks), "fallback_used": False, "retrieval_strategy": "multimodal_vision_and_document"}
                }, None
            # --- END IMAGE ROUTING ---

            # Robust intent detection for ALL FILES
            is_all_files = False
            if re.search(r'\b(all|every|each)\b.*\b(files?|documents?|docs?)\b', q_lower):
                is_all_files = True
            elif "all" in q_lower and "summar" in q_lower:
                is_all_files = True
            
            target_fnum_match = re.search(r'(?:file|document|doc)\s*#?\s*(\d+)', q_lower)
            if "summar" in q_lower and not target_fnum_match and not is_all_files:
                is_all_files = True
                
            if is_all_files:
                logger.info("Detected ALL_FILES intent. Initiating per-file processing...")
                unique_files = self.get_unique_files()
                if not unique_files:
                    return {}, "No documents uploaded."
                
                final_answer_blocks = []
                all_sources = []
                
                for display_idx, file_info in enumerate(unique_files, 1):
                    fid = file_info["file_id"]
                    original_fnum = file_info["file_number"]
                    fname = file_info["filename"]
                    
                    retrieved_chunks, _ = self.retrieve_context(
                        question=question,
                        top_k=max(15, top_k or settings.top_k_retrieval), 
                        relevance_threshold=relevance_threshold,
                        file_id=fid
                    )
                    
                    retrieved_chunks = [c for c in retrieved_chunks if c.get("file_id") == fid]
                    
                    if not retrieved_chunks:
                        final_answer_blocks.append(f"# File {display_idx} — {fname}\n\nNo sufficiently relevant content was retrieved from this file.")
                        continue
                        
                    prompt = self.build_prompt(f"Focus ONLY on File {original_fnum} ({fname}). Answer this request using ONLY the provided context blocks: {question}", retrieved_chunks)
                    answer, err = self.call_gemini(prompt)
                    
                    if err:
                        answer = f"Failed to generate answer for this file: {err}"
                        
                    file_response = self.format_response(
                        question=question,
                        answer=answer,
                        retrieved_chunks=retrieved_chunks,
                        search_time_ms=0,
                        fallback_used=False
                    )
                    
                    for src in file_response["sources"]:
                        src["file_number"] = display_idx
                        if src not in all_sources:
                            all_sources.append(src)
                    
                    final_answer_blocks.append(f"# File {display_idx} — {fname}\n\n## Detailed Summary\n\n{answer}")
                    
                final_answer = "\n\n------------------------------------------------\n\n".join(final_answer_blocks)
                search_time_ms = (time.time() - start_time) * 1000
                
                return {
                    "answer": final_answer,
                    "sources": all_sources,
                    "retrieval_details": {
                        "search_time_ms": search_time_ms,
                        "documents_searched": len(unique_files),
                        "chunks_retrieved": len(unique_files) * 15,
                        "fallback_used": False,
                        "retrieval_strategy": "all_documents_per_file"
                    }
                }, None
                
            # Single/Multi Query Fallback
            logger.info("Step 1: Retrieving context from documents...")
            retrieved_chunks, error = self.retrieve_context(
                question=question,
                top_k=top_k,
                relevance_threshold=relevance_threshold,
                file_id=file_id
            )
            
            if error:
                return {}, error
            
            if not retrieved_chunks:
                error = "No relevant context found in documents"
                return {}, error
            
            prompt = self.build_prompt(question, retrieved_chunks)
            answer, error = self.call_gemini(prompt)
            
            if error:
                context_snippets = "\n\n".join([f"Excerpt {i+1}:\n{chunk['text']}" for i, chunk in enumerate(retrieved_chunks[:3])])
                answer = f"Relevant information from your document:\n\n{context_snippets}"
            
            search_time_ms = (time.time() - start_time) * 1000
            
            response = self.format_response(
                question=question,
                answer=answer,
                retrieved_chunks=retrieved_chunks,
                search_time_ms=search_time_ms,
                fallback_used=False
            )
            
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