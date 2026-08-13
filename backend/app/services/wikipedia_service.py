from typing import List, Optional, Tuple, Dict
import logging
import requests
import re
import html

from app.utils.logger import get_logger

logger = get_logger(__name__)


class WikipediaService:
    API_URL = "https://en.wikipedia.org/w/api.php"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "RAG-Chatbot/1.0 (https://github.com/FurquanCodes/rag-chatbot)"
        })
        logger.info("✅ Wikipedia service initialized")
    
    def _clean_query(self, query: str) -> str:
        cleaned = query.strip()
        pattern = r'^(who\s+(is|was|are|were)|what\s+(is|was|are|were)|tell\s+me\s+about|explain|who\'s|what\'s|give\s+me\s+information\s+about)\s+'
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()
        return cleaned if cleaned else query

    def search(
        self,
        query: str,
        max_results: int = 3
    ) -> Tuple[List[Dict], Optional[str]]:
        search_query = self._clean_query(query)
        logger.info(f"🔍 Searching Wikipedia for query '{query}' (cleaned: '{search_query}')")
        
        try:
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": search_query,
                "srlimit": max_results,
                "srprop": "snippet"
            }
            
            response = self.session.get(self.API_URL, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if "query" not in data or "search" not in data["query"]:
                error = "No Wikipedia results found"
                logger.warning(f"⚠️ {error}")
                return [], error
            
            raw_items = data["query"]["search"][:max_results]
            if not raw_items:
                return [], "No Wikipedia results found"

            titles = [item["title"] for item in raw_items]
            extracts_map = {}

            try:
                ex_params = {
                    "action": "query",
                    "format": "json",
                    "titles": "|".join(titles),
                    "prop": "extracts",
                    "exintro": True,
                    "explaintext": True
                }
                ex_resp = self.session.get(self.API_URL, params=ex_params, timeout=5)
                if ex_resp.status_code == 200:
                    ex_data = ex_resp.json()
                    pages = ex_data.get("query", {}).get("pages", {})
                    for page_id, page_info in pages.items():
                        title = page_info.get("title")
                        extract = page_info.get("extract", "").strip()
                        if title and extract:
                            extracts_map[title] = extract
            except Exception as e:
                logger.warning(f"Failed to fetch Wikipedia extracts: {e}")

            results = []
            for item in raw_items:
                title = item["title"]
                raw_snippet = item.get("snippet", "")
                clean_snippet = re.sub(r'<[^>]+>', '', raw_snippet)
                clean_snippet = html.unescape(clean_snippet).strip()

                extract = extracts_map.get(title, clean_snippet)

                result = {
                    "title": title,
                    "snippet": clean_snippet,
                    "summary": extract,
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "relevance_score": 0.8
                }
                results.append(result)
            
            logger.info(f"✅ Found {len(results)} Wikipedia articles with intro extracts")
            return results, None
            
        except requests.exceptions.Timeout:
            error = "Wikipedia search timed out"
            logger.error(f"❌ {error}")
            return [], error
        
        except requests.exceptions.RequestException as e:
            error = f"Wikipedia API error: {str(e)}"
            logger.error(f"❌ {error}")
            return [], error
        
        except Exception as e:
            error = f"Wikipedia search failed: {str(e)}"
            logger.error(f"❌ {error}")
            return [], error

    def get_summary(self, title: str) -> Tuple[Optional[str], Optional[str]]:
        logger.info(f"📖 Getting Wikipedia summary for: {title}")
        
        try:
            params = {
                "action": "query",
                "format": "json",
                "titles": title,
                "prop": "extracts",
                "explaintext": True,
                "exintro": True
            }
            
            response = self.session.get(self.API_URL, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if "query" not in data or "pages" not in data["query"]:
                error = "Failed to get article"
                logger.error(f"❌ {error}")
                return None, error
            
            pages = data["query"]["pages"]
            
            for page_id, page_data in pages.items():
                if "extract" in page_data:
                    summary = page_data["extract"]
                    logger.info(f"✅ Got summary ({len(summary)} characters)")
                    return summary, None
            
            error = "No extract found"
            logger.error(f"❌ {error}")
            return None, error
            
        except Exception as e:
            error = f"Failed to get summary: {str(e)}"
            logger.error(f"❌ {error}")
            return None, error

    def build_context(self, question: str, results: List[Dict]) -> str:
        logger.debug(f"Building context from {len(results)} Wikipedia results...")
        
        context = """You are a helpful AI assistant. Answer the user's question accurately based on the provided Wikipedia information.

IMPORTANT INSTRUCTIONS:
1. FOCUS STRICTLY ON THE TARGET ENTITY / SUBJECT asked in the user's question. For example, if asked about RDJ or Robert Downey Jr., provide information directly about Robert Downey Jr. including his identity, profession, and career achievements.
2. Do NOT focus on side figures, family members, or spouse unless explicitly requested.
3. If the provided Wikipedia information does not contain sufficient or relevant information to answer who or what the subject of the question is, reply EXACTLY with: "Unable to get information about it."
4. At the very end of your answer, include a "Sources:" section with the exact Wikipedia article title and direct clickable markdown link (e.g., "Sources: [Wikipedia - Quantum Computing](https://en.wikipedia.org/wiki/Quantum_computing)").
5. Be direct, clear, accurate, and concise.

CONTEXT FROM WIKIPEDIA:
═══════════════════════════════════════════════════════════════════
"""
        
        for i, result in enumerate(results, 1):
            context += f"\n[{i}. {result['title']}]\n"
            text_content = result.get('summary') or result.get('snippet') or ""
            context += text_content + "\n"
            context += f"Source URL: {result['url']}\n"
        
        context += """═══════════════════════════════════════════════════════════════════

QUESTION:
"""
        context += question + "\n"
        context += "\nPROVIDE YOUR ANSWER BELOW:\n"
        
        return context