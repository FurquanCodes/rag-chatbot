"""
Wikipedia Service
Fallback search when document search doesn't find relevant context
"""

import logging
from typing import List, Optional, Tuple, Dict
import requests

# Local imports
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============ WIKIPEDIA SERVICE ============

class WikipediaService:
    """
    Wikipedia search and context extraction
    Used as fallback when document search returns no relevant results
    """
    
    # Wikipedia API endpoint
    API_URL = "https://en.wikipedia.org/w/api.php"
    
    def __init__(self):
        """Initialize Wikipedia service"""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "RAG-Chatbot/1.0 (https://github.com/FurquanCodes/rag-chatbot)"
        })
        logger.info("✅ Wikipedia service initialized")
    
    def search(
        self,
        query: str,
        max_results: int = 3
    ) -> Tuple[List[Dict], Optional[str]]:
        """
        Search Wikipedia for articles related to query
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            Tuple[List[Dict], Optional[str]]: (results, error_message)
        """
        
        logger.info(f"🔍 Searching Wikipedia for: {query}")
        
        try:
            # Search Wikipedia
            params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": query,
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
            
            results = []
            for item in data["query"]["search"][:max_results]:
                result = {
                    "title": item["title"],
                    "snippet": item["snippet"],
                    "url": f"https://en.wikipedia.org/wiki/{item['title'].replace(' ', '_')}",
                    "relevance_score": 0.8
                }
                results.append(result)
            
            logger.info(f"✅ Found {len(results)} Wikipedia articles")
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
        """
        Get full summary of a Wikipedia article
        
        Args:
            title: Article title
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (summary, error_message)
        """
        
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
    
    def build_context(self, results: List[Dict]) -> str:
        """
        Build prompt context from Wikipedia results
        
        Args:
            results: List of Wikipedia search results
            
        Returns:
            str: Formatted prompt for Gemini
        """
        
        logger.debug(f"Building context from {len(results)} Wikipedia results...")
        
        context = """You are a helpful AI assistant. Answer the question based on the provided Wikipedia information.

CONTEXT FROM WIKIPEDIA:
═══════════════════════════════════════════════════════════════════
"""
        
        for i, result in enumerate(results, 1):
            context += f"\n[{i}. {result['title']}]\n"
            context += result['snippet'] + "\n"
            context += f"Source: {result['url']}\n"
        
        context += """═══════════════════════════════════════════════════════════════════

INSTRUCTIONS:
1. Base your answer on the Wikipedia information provided
2. Be accurate and cite the relevant sections
3. If the information is incomplete, say so
4. Provide a helpful, comprehensive answer

PROVIDE YOUR ANSWER BELOW:
"""
        
        return context