"""
Pydantic schemas for request/response validation
Defines all data structures used in API endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============ ENUMS (Fixed values) ============

class DocumentSourceType(str, Enum):
    """Source types for retrieved context"""
    DOCUMENT = "document"
    WIKIPEDIA = "wikipedia"


class SearchType(str, Enum):
    """Search strategy options"""
    DOCUMENTS_ONLY = "documents_only"
    WIKIPEDIA_ONLY = "wikipedia_only"
    HYBRID = "hybrid"  # Try documents first, Wikipedia as fallback


class UploadStatus(str, Enum):
    """Status of uploaded files"""
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


# ============ FILE UPLOAD SCHEMAS ============

class FileInfo(BaseModel):
    """Information about a single uploaded file"""
    filename: str = Field(..., description="Original filename")
    file_id: str = Field(..., description="Unique file identifier (UUID)")
    file_type: str = Field(..., description="File type: pdf, docx, pptx, txt")
    file_size_bytes: int = Field(..., description="File size in bytes")
    pages: int = Field(default=0, description="Number of pages (for PDF/PPTX)")
    chunks: int = Field(default=0, description="Number of text chunks created")
    status: UploadStatus = Field(default=UploadStatus.PROCESSED, description="Processing status")
    uploaded_at: datetime = Field(default_factory=datetime.utcnow, description="Upload timestamp")
    
    class Config:
        use_enum_values = True  # Return enum as string in JSON


class UploadResponse(BaseModel):
    """Response from file upload endpoint"""
    status: str = Field(default="success", description="Operation status")
    message: str = Field(..., description="Human-readable message")
    data: dict = Field(
        default_factory=dict,
        description="Upload details"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "3 files uploaded and processed",
                "data": {
                    "uploaded_files": [
                        {
                            "filename": "document1.pdf",
                            "file_id": "uuid-123",
                            "file_type": "pdf",
                            "file_size_bytes": 2048576,
                            "pages": 25,
                            "chunks": 45,
                            "status": "processed",
                            "uploaded_at": "2026-08-05T11:00:00"
                        }
                    ],
                    "total_files": 1,
                    "total_chunks": 45,
                    "total_embeddings_generated": 45,
                    "processing_time_seconds": 12.5
                }
            }
        }


# ============ DOCUMENT RETRIEVAL SCHEMAS ============

class DocumentMetadata(BaseModel):
    """Metadata for a document"""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File type: pdf, docx, pptx, txt")
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    status: str = Field(..., description="Processing status")
    pages: int = Field(default=0, description="Number of pages")
    chunks: int = Field(default=0, description="Number of chunks")
    file_size_mb: float = Field(..., description="File size in MB")


class DocumentListResponse(BaseModel):
    """Response from list documents endpoint"""
    status: str = Field(default="success", description="Operation status")
    data: dict = Field(..., description="Document list data")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "documents": [
                        {
                            "file_id": "uuid-1",
                            "filename": "document1.pdf",
                            "file_type": "pdf",
                            "uploaded_at": "2026-08-05T11:00:00",
                            "status": "processed",
                            "pages": 25,
                            "chunks": 45,
                            "file_size_mb": 2.05
                        }
                    ],
                    "total_documents": 1,
                    "total_chunks": 45
                }
            }
        }


class DeleteDocumentResponse(BaseModel):
    """Response from delete document endpoint"""
    status: str = Field(default="success", description="Operation status")
    message: str = Field(..., description="Confirmation message")
    data: dict = Field(..., description="Deletion details")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Document deleted successfully",
                "data": {
                    "file_id": "uuid-1",
                    "filename": "document1.pdf",
                    "chunks_removed": 45
                }
            }
        }


# ============ CHAT/RAG SCHEMAS ============

class ChatRequest(BaseModel):
    """Request for chat/question endpoint"""
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's question"
    )
    collection_id: str = Field(
        default="default",
        description="User/collection ID for multi-tenant support"
    )
    file_id: Optional[str] = Field(
        default=None,
        description="Optional target file ID to restrict search"
    )
    search_type: SearchType = Field(
        default=SearchType.HYBRID,
        description="Search strategy: documents_only, wikipedia_only, or hybrid"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of chunks to retrieve (1-20)"
    )
    relevance_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score (0-1)"
    )
    
    @validator('question')
    def question_not_empty(cls, v):
        """Ensure question is not just whitespace"""
        if not v.strip():
            raise ValueError('Question cannot be empty or whitespace')
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "question": "What are the main topics in this document?",
                "collection_id": "user-123",
                "search_type": "hybrid",
                "top_k": 5,
                "relevance_threshold": 0.7
            }
        }


class EvidenceSource(BaseModel):
    """A single source of evidence for an answer"""
    source_type: DocumentSourceType = Field(
        ...,
        description="Type of source: document or wikipedia"
    )
    source_name: str = Field(
        ...,
        description="Name of the source (filename or Wikipedia article)"
    )
    page_number: Optional[int] = Field(
        default=None,
        description="Page number (for documents)"
    )
    section_heading: Optional[str] = Field(
        default=None,
        description="Section heading (if available)"
    )
    evidence_snippet: str = Field(
        ...,
        description="Relevant text excerpt from the source"
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How relevant this source is to the question (0-1)"
    )
    wikipedia_url: Optional[str] = Field(
        default=None,
        description="Wikipedia URL (for wikipedia sources)"
    )


class RetrievalDetails(BaseModel):
    """Details about the retrieval process"""
    search_time_ms: float = Field(
        ...,
        description="Time taken to search (milliseconds)"
    )
    documents_searched: int = Field(
        default=0,
        description="Number of documents searched"
    )
    chunks_retrieved: int = Field(
        ...,
        description="Number of chunks retrieved"
    )
    fallback_used: bool = Field(
        default=False,
        description="Whether Wikipedia fallback was used"
    )
    retrieval_strategy: str = Field(
        ...,
        description="Strategy used: document_search, wikipedia_search, or hybrid"
    )


class ChatResponse(BaseModel):
    """Response from chat/question endpoint"""
    status: str = Field(default="success", description="Operation status")
    data: dict = Field(..., description="Response data")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "data": {
                    "answer": "The main topics covered in the document are machine learning and deep learning...",
                    "sources": [
                        {
                            "source_type": "document",
                            "source_name": "document1.pdf",
                            "page_number": 1,
                            "section_heading": "Introduction",
                            "evidence_snippet": "Machine learning is the foundation of AI...",
                            "relevance_score": 0.92,
                            "wikipedia_url": None
                        }
                    ],
                    "retrieval_details": {
                        "search_time_ms": 125.5,
                        "documents_searched": 3,
                        "chunks_retrieved": 5,
                        "fallback_used": False,
                        "retrieval_strategy": "document_search"
                    }
                }
            }
        }


# ============ ERROR SCHEMAS ============

class ErrorDetail(BaseModel):
    """Error response structure"""
    status: str = Field(default="error", description="Operation status")
    message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(
        default=None,
        description="Error code for client handling"
    )
    details: Optional[dict] = Field(
        default=None,
        description="Additional error details"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "error",
                "message": "Invalid file format",
                "error_code": "INVALID_FILE_FORMAT",
                "details": {
                    "allowed_formats": ["pdf", "docx", "pptx", "txt"],
                    "provided_format": "exe"
                }
            }
        }


# ============ HEALTH CHECK SCHEMAS ============

class ServiceStatus(BaseModel):
    """Status of a single service"""
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status: ok, warning, error")
    message: Optional[str] = Field(default=None, description="Status message")


class HealthCheckResponse(BaseModel):
    """Response from health check endpoint"""
    status: str = Field(default="healthy", description="Overall status")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
    environment: str = Field(..., description="Environment: development or production")
    version: str = Field(..., description="API version")
    services: dict = Field(
        default_factory=dict,
        description="Status of individual services"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2026-08-05T11:18:17",
                "environment": "development",
                "version": "1.0.0",
                "services": {
                    "api": "ok",
                    "gemini": "ok",
                    "faiss": "ok",
                    "storage": "ok"
                }
            }
        }


# ============ CHUNK SCHEMA (Internal) ============

class TextChunk(BaseModel):
    """A single text chunk from a document"""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    file_id: str = Field(..., description="Parent file ID")
    chunk_index: int = Field(..., description="Position in document (0-indexed)")
    text: str = Field(..., description="Actual text content")
    page_number: Optional[int] = Field(default=None, description="Page number")
    section_heading: Optional[str] = Field(default=None, description="Section title")
    embedding: Optional[List[float]] = Field(
        default=None,
        description="Embedding vector (768 dimensions)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Creation timestamp"
    )


# ============ FILE METADATA SCHEMA (Internal) ============

class StoredFileMetadata(BaseModel):
    """Metadata stored for uploaded files"""
    file_id: str = Field(..., description="Unique file identifier")
    collection_id: str = Field(..., description="Collection/user ID")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File extension")
    file_size_bytes: int = Field(..., description="File size")
    file_path: str = Field(..., description="Storage path")
    pages: int = Field(default=0, description="Number of pages")
    chunks: int = Field(default=0, description="Number of chunks")
    total_chars: int = Field(default=0, description="Total characters")
    embedding_model: str = Field(..., description="Embedding model used")
    uploaded_at: datetime = Field(..., description="Upload time")
    processed_at: Optional[datetime] = Field(default=None, description="Processing completion time")
    status: str = Field(default="processed", description="Processing status")