"""
File Processing Service
Handles document reading, text extraction, and chunking
Supports: PDF, DOCX, PPTX, TXT
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import uuid
from datetime import datetime
import logging

# Document parsing libraries
from pypdf import PdfReader
from docx import Document as DocxDocument
from pptx import Presentation
import re

# Local imports
from app.utils.config import settings, UPLOAD_DIR
from app.utils.logger import get_logger
from app.models.schemas import TextChunk, StoredFileMetadata

logger = get_logger(__name__)


# ============ FILE VALIDATION ============

class FileValidator:
    """Validates uploaded files before processing"""
    
    ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "txt"}
    MAX_FILE_SIZE = settings.max_file_size  # 50MB
    
    @staticmethod
    def validate_file(filename: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Validate file type and size
        
        Args:
            filename: Name of the file
            file_size: File size in bytes
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check file extension
        file_ext = filename.split('.')[-1].lower()
        if file_ext not in FileValidator.ALLOWED_EXTENSIONS:
            return False, f"Invalid file type: {file_ext}. Allowed: {', '.join(FileValidator.ALLOWED_EXTENSIONS)}"
        
        # Check file size
        if file_size > FileValidator.MAX_FILE_SIZE:
            max_mb = FileValidator.MAX_FILE_SIZE / (1024 * 1024)
            file_mb = file_size / (1024 * 1024)
            return False, f"File too large: {file_mb:.1f}MB (max: {max_mb:.1f}MB)"
        
        logger.info(f"✅ File validation passed: {filename} ({file_size / 1024:.1f}KB)")
        return True, None


# ============ TEXT EXTRACTION ============

class TextExtractor:
    """Extracts text from different document formats"""
    
    @staticmethod
    def extract_from_pdf(file_path: str) -> Tuple[str, int, List[str]]:
        """
        Extract text from PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Tuple[str, int, List[str]]: (full_text, num_pages, page_texts)
        """
        logger.info(f"Extracting text from PDF: {file_path}")
        
        try:
            pdf_reader = PdfReader(file_path)
            num_pages = len(pdf_reader.pages)
            page_texts = []
            full_text = ""
            
            for page_num, page in enumerate(pdf_reader.pages):
                # Extract text from page
                page_text = page.extract_text()
                page_texts.append(page_text)
                full_text += f"\n\n--- Page {page_num + 1} ---\n{page_text}"
            
            logger.info(f"✅ Extracted {num_pages} pages from PDF")
            return full_text, num_pages, page_texts
            
        except Exception as e:
            logger.error(f"❌ Error extracting PDF: {str(e)}")
            raise Exception(f"Failed to extract PDF: {str(e)}")
    
    @staticmethod
    def extract_from_docx(file_path: str) -> Tuple[str, int, List[str]]:
        """
        Extract text from DOCX (Word) file
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            Tuple[str, int, List[str]]: (full_text, num_paragraphs, paragraph_texts)
        """
        logger.info(f"Extracting text from DOCX: {file_path}")
        
        try:
            doc = DocxDocument(file_path)
            full_text = ""
            paragraph_texts = []
            
            for para_num, para in enumerate(doc.paragraphs):
                if para.text.strip():  # Skip empty paragraphs
                    paragraph_texts.append(para.text)
                    full_text += f"\n{para.text}"
            
            # Also extract table data
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text for cell in row.cells])
                    full_text += f"\n{row_text}"
            
            logger.info(f"✅ Extracted {len(paragraph_texts)} paragraphs from DOCX")
            return full_text, len(paragraph_texts), paragraph_texts
            
        except Exception as e:
            logger.error(f"❌ Error extracting DOCX: {str(e)}")
            raise Exception(f"Failed to extract DOCX: {str(e)}")
    
    @staticmethod
    def extract_from_pptx(file_path: str) -> Tuple[str, int, List[str]]:
        """
        Extract text from PPTX (PowerPoint) file
        
        Args:
            file_path: Path to PPTX file
            
        Returns:
            Tuple[str, int, List[str]]: (full_text, num_slides, slide_texts)
        """
        logger.info(f"Extracting text from PPTX: {file_path}")
        
        try:
            presentation = Presentation(file_path)
            full_text = ""
            slide_texts = []
            
            for slide_num, slide in enumerate(presentation.slides):
                slide_text = ""
                
                # Extract text from shapes
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text += f"\n{shape.text}"
                
                slide_texts.append(slide_text)
                full_text += f"\n\n--- Slide {slide_num + 1} ---\n{slide_text}"
            
            logger.info(f"✅ Extracted {len(presentation.slides)} slides from PPTX")
            return full_text, len(presentation.slides), slide_texts
            
        except Exception as e:
            logger.error(f"❌ Error extracting PPTX: {str(e)}")
            raise Exception(f"Failed to extract PPTX: {str(e)}")
    
    @staticmethod
    def extract_from_txt(file_path: str) -> Tuple[str, int, List[str]]:
        """
        Extract text from TXT file
        
        Args:
            file_path: Path to TXT file
            
        Returns:
            Tuple[str, int, List[str]]: (full_text, num_lines, line_texts)
        """
        logger.info(f"Extracting text from TXT: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
            
            line_texts = [line.strip() for line in full_text.split('\n') if line.strip()]
            
            logger.info(f"✅ Extracted {len(line_texts)} lines from TXT")
            return full_text, len(line_texts), line_texts
            
        except Exception as e:
            logger.error(f"❌ Error extracting TXT: {str(e)}")
            raise Exception(f"Failed to extract TXT: {str(e)}")
    
    @staticmethod
    def extract_text(file_path: str, file_type: str) -> Tuple[str, int, List[str]]:
        """
        Route to appropriate extraction method based on file type
        
        Args:
            file_path: Path to file
            file_type: File type (pdf, docx, pptx, txt)
            
        Returns:
            Tuple[str, int, List[str]]: (full_text, count, details)
        """
        file_type = file_type.lower()
        
        if file_type == "pdf":
            return TextExtractor.extract_from_pdf(file_path)
        elif file_type == "docx":
            return TextExtractor.extract_from_docx(file_path)
        elif file_type == "pptx":
            return TextExtractor.extract_from_pptx(file_path)
        elif file_type == "txt":
            return TextExtractor.extract_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")


# ============ TEXT CHUNKING ============

class TextChunker:
    """Splits text into overlapping chunks"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text: remove extra whitespace, normalize
        
        Args:
            text: Raw text
            
        Returns:
            str: Cleaned text
        """
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?;:\'-]', '', text)
        return text.strip()
    
    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = None,
        overlap: int = None
    ) -> List[TextChunk]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Full text to chunk
            chunk_size: Size of each chunk (default: from config)
            overlap: Overlap between chunks (default: from config)
            
        Returns:
            List[TextChunk]: List of text chunks with metadata
        """
        if chunk_size is None:
            chunk_size = settings.chunk_size
        if overlap is None:
            overlap = settings.chunk_overlap
        
        logger.info(f"Chunking text: chunk_size={chunk_size}, overlap={overlap}")
        
        # Clean text
        text = TextChunker.clean_text(text)
        
        if len(text) < chunk_size:
            # If text is smaller than chunk size, return as single chunk
            chunk = TextChunk(
                chunk_id=str(uuid.uuid4()),
                file_id="",  # Will be set later
                chunk_index=0,
                text=text,
                page_number=None,
                section_heading=None
            )
            logger.info(f"✅ Created 1 chunk (text smaller than chunk_size)")
            return [chunk]
        
        chunks = []
        start_idx = 0
        chunk_index = 0
        
        while start_idx < len(text):
            # Calculate end index
            end_idx = min(start_idx + chunk_size, len(text))
            
            # Extract chunk
            chunk_text = text[start_idx:end_idx]
            
            # Create chunk object
            chunk = TextChunk(
                chunk_id=str(uuid.uuid4()),
                file_id="",  # Will be set later
                chunk_index=chunk_index,
                text=chunk_text.strip(),
                page_number=None,
                section_heading=None
            )
            chunks.append(chunk)
            
            # Move to next chunk (with overlap)
            start_idx = end_idx - overlap
            chunk_index += 1
            
            # Prevent infinite loop if overlap >= chunk_size
            if start_idx >= end_idx:
                break
        
        logger.info(f"✅ Created {len(chunks)} chunks from text")
        return chunks
    
    @staticmethod
    def detect_page_numbers(chunks: List[TextChunk], page_markers: List[str]) -> List[TextChunk]:
        """
        Try to detect page numbers in chunks based on page markers
        
        Args:
            chunks: List of chunks
            page_markers: List of page marker strings (e.g., ["--- Page 1 ---", "--- Page 2 ---"])
            
        Returns:
            List[TextChunk]: Chunks with page numbers set
        """
        current_page = None
        
        for chunk in chunks:
            # Check if chunk text contains a page marker
            for page_num, marker in enumerate(page_markers, 1):
                if marker in chunk.text:
                    current_page = page_num
            
            if current_page:
                chunk.page_number = current_page
        
        return chunks


# ============ FILE STORAGE ============

class FileStorage:
    """Manages file storage on disk"""
    
    @staticmethod
    def save_uploaded_file(
        file_content: bytes,
        filename: str,
        collection_id: str
    ) -> Tuple[str, str]:
        """
        Save uploaded file to disk
        
        Args:
            file_content: Binary file content
            filename: Original filename
            collection_id: User/collection ID
            
        Returns:
            Tuple[str, str]: (file_path, file_id)
        """
        # Create directory for collection if it doesn't exist
        collection_dir = UPLOAD_DIR / collection_id
        collection_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique file ID
        file_id = str(uuid.uuid4())
        file_ext = filename.split('.')[-1].lower()
        
        # Create unique filename
        unique_filename = f"{file_id}.{file_ext}"
        file_path = collection_dir / unique_filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        logger.info(f"✅ File saved: {file_path} (ID: {file_id})")
        return str(file_path), file_id
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        Delete file from disk
        
        Args:
            file_path: Path to file
            
        Returns:
            bool: Success status
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"✅ File deleted: {file_path}")
                return True
            else:
                logger.warning(f"⚠️ File not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"❌ Error deleting file: {str(e)}")
            return False


# ============ MAIN FILE PROCESSOR ============

class FileProcessor:
    """Main orchestrator for file processing"""
    
    def __init__(self):
        self.validator = FileValidator()
        self.extractor = TextExtractor()
        self.chunker = TextChunker()
        self.storage = FileStorage()
    
    def process_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: str,
        collection_id: str = "default"
    ) -> Tuple[List[TextChunk], StoredFileMetadata]:
        """
        Complete file processing pipeline
        
        Pipeline:
        1. Validate file
        2. Save to disk
        3. Extract text
        4. Chunk text
        5. Return chunks + metadata
        
        Args:
            file_content: Binary file content
            filename: Original filename
            file_type: File type (pdf, docx, pptx, txt)
            collection_id: User/collection ID
            
        Returns:
            Tuple[List[TextChunk], StoredFileMetadata]: (chunks, metadata)
            
        Raises:
            ValueError: If file validation fails
            Exception: If processing fails
        """
        logger.info(f"Processing file: {filename} ({file_type})")
        
        # Step 1: Validate
        is_valid, error_msg = self.validator.validate_file(filename, len(file_content))
        if not is_valid:
            logger.error(f"❌ File validation failed: {error_msg}")
            raise ValueError(error_msg)
        
        # Step 2: Save to disk
        file_path, file_id = self.storage.save_uploaded_file(
            file_content, filename, collection_id
        )
        
        try:
            # Step 3: Extract text
            full_text, page_count, page_details = self.extractor.extract_text(file_path, file_type)
            total_chars = len(full_text)
            
            # Step 4: Chunk text
            chunks = self.chunker.chunk_text(full_text)
            
            # Set file_id for all chunks
            for chunk in chunks:
                chunk.file_id = file_id
            
            # Try to detect page numbers
            if page_details and file_type in ["pdf", "pptx"]:
                page_markers = [f"--- Page {i + 1} ---" for i in range(len(page_details))]
                chunks = self.chunker.detect_page_numbers(chunks, page_markers)
            
            # Step 5: Create metadata
            metadata = StoredFileMetadata(
                file_id=file_id,
                collection_id=collection_id,
                filename=filename,
                file_type=file_type,
                file_size_bytes=len(file_content),
                file_path=file_path,
                pages=page_count if file_type in ["pdf", "pptx"] else 0,
                chunks=len(chunks),
                total_chars=total_chars,
                embedding_model=settings.embedding_model,
                uploaded_at=datetime.utcnow(),
                processed_at=datetime.utcnow(),
                status="processed"
            )
            
            logger.info(f"✅ File processing complete: {len(chunks)} chunks created")
            return chunks, metadata
            
        except Exception as e:
            # Clean up on failure
            self.storage.delete_file(file_path)
            logger.error(f"❌ File processing failed: {str(e)}")
            raise Exception(f"Failed to process file: {str(e)}")
        # At the END of file_processor.py (after all classes)

__all__ = ['FileProcessor', 'FileValidator', 'TextExtractor', 'TextChunker', 'FileStorage']