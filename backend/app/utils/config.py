"""
Configuration management using Pydantic Settings
Centralized configuration for the entire backend application
"""

from pydantic import BaseSettings
from pydantic import Field
from pathlib import Path
import logging
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    Provides type safety and validation for all configuration
    """
    
    # ============ API Configuration ============
    api_title: str = Field(default="RAG Chatbot API", description="API title")
    api_version: str = Field(default="1.0.0", description="API version")
    api_description: str = Field(default="RAG Chatbot with FastAPI backend", description="API description")
    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=8000, description="API port number")
    api_env: str = Field(default="development", description="Environment: development or production")
    
    # ============ Google Gemini API ============
    google_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-1.5-flash", description="Gemini model name")
    
    # ============ File Upload Configuration ============
    upload_folder: str = Field(default="./uploads", description="Directory to store uploaded files")
    max_file_size: int = Field(default=50 * 1024 * 1024, description="Max file size in bytes (50MB)")
    allowed_file_types: list = Field(
        default=["pdf", "docx", "pptx", "txt"],
        description="Allowed document file types"
    )
    
    # ============ FAISS Vector Store ============
    faiss_index_path: str = Field(default="./faiss_index", description="Path to store FAISS index")
    embedding_model: str = Field(default="models/embedding-001", description="Google Embedding model")
    embedding_dimension: int = Field(default=768, description="Embedding vector dimension")
    
    # ============ RAG Configuration ============
    chunk_size: int = Field(default=1000, description="Document chunk size in characters")
    chunk_overlap: int = Field(default=200, description="Overlap between chunks")
    top_k_retrieval: int = Field(default=5, description="Number of top chunks to retrieve")
    relevance_threshold: float = Field(default=0.7, description="Relevance score threshold (0-1)")
    
    # ============ Logging Configuration ============
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="./logs/app.log", description="Log file path")
    
    # ============ CORS Configuration ============
    frontend_url: str = Field(default="http://localhost:3000", description="Frontend URL for CORS")
    allowed_origins: list = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed origins for CORS"
    )
    
    class Config:
        """Load configuration from .env file"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create settings instance (cached)
@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Using lru_cache ensures settings are loaded only once per application instance
    """
    return Settings()


# Initialize settings
settings = get_settings()


# ============ Path Configuration ============
BASE_DIR = Path(__file__).parent.parent.parent  # Points to backend/ folder
UPLOAD_DIR = Path(settings.upload_folder).resolve()
FAISS_INDEX_DIR = Path(settings.faiss_index_path).resolve()
LOG_DIR = Path(settings.log_file).parent.resolve()

# Create directories if they don't exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)


def print_startup_info():
    """Print startup information (for debugging)"""
    print("\n" + "="*60)
    print("🚀 RAG CHATBOT BACKEND STARTING")
    print("="*60)
    print(f"Environment: {settings.api_env}")
    print(f"API Server: {settings.api_host}:{settings.api_port}")
    print(f"Gemini Model: {settings.gemini_model}")
    print(f"Upload Folder: {UPLOAD_DIR}")
    print(f"FAISS Index: {FAISS_INDEX_DIR}")
    print(f"Logging Level: {settings.log_level}")
    print("="*60 + "\n")