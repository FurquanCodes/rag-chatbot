"""
Upload Routes
Handles file upload and document processing
"""

import logging
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
import time
from app.utils.config import settings, UPLOAD_DIR

# Local imports
from app.utils.config import settings
from app.utils.logger import get_logger
from app.utils.constants import API_ROUTES, ERROR_MESSAGES, SUCCESS_MESSAGES
from app.models.schemas import UploadResponse, FileInfo, UploadStatus, DeleteDocumentResponse
from app.services.file_processor import FileProcessor
from app.services.embedding_service import EmbeddingService
from app.storage.faiss_store import get_faiss_store

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1", tags=["Documents"])


# ============ UPLOAD ENDPOINT ============

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_documents(
    files: List[UploadFile] = File(..., description="Documents to upload (PDF, DOCX, PPTX, TXT)"),
    collection_id: str = Form(default="default", description="User/collection ID")
) -> UploadResponse:
    """
    Upload and process documents
    
    Complete pipeline:
    1. Validate files
    2. Extract text
    3. Chunk text
    4. Generate embeddings
    5. Store in FAISS
    
    Args:
        files: List of uploaded files
        collection_id: User/collection identifier
        
    Returns:
        UploadResponse: Upload status and details
        
    Raises:
        HTTPException: If validation or processing fails
    """
    
    start_time = time.time()
    logger.info(f"📤 Upload initiated: {len(files)} files, collection_id={collection_id}")
    
    # ============ INPUT VALIDATION ============
    
    if not files:
        logger.error("❌ No files provided")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "No files provided",
                "error_code": "NO_FILES"
            }
        )
    
    if len(files) > 10:
        logger.error(f"❌ Too many files: {len(files)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "Maximum 10 files per upload",
                "error_code": "TOO_MANY_FILES"
            }
        )
    
    if not collection_id or not collection_id.strip():
        collection_id = "default"
    
    # ============ PROCESS FILES ============
    
    uploaded_files_info = []
    total_chunks = 0
    total_embeddings = 0
    failed_files = []
    
    # Initialize services
    file_processor = FileProcessor()
    embedding_service = EmbeddingService()
    faiss_store = get_faiss_store()
    
    for file_idx, file in enumerate(files, 1):
        try:
            logger.info(f"Processing file {file_idx}/{len(files)}: {file.filename}")
            
            # Get file type
            file_type = file.filename.split('.')[-1].lower()
            
            # Read file content
            file_content = file.file.read()
            
            from app.services.rag_service import ACTIVE_IMAGES
            
            if file_type in {"png", "jpg", "jpeg", "webp", "gif"}:
                logger.info(f"Processing image {file.filename}...")
                image_number = len(ACTIVE_IMAGES) + 1
                img_data = file_processor.process_image(
                    file_content=file_content,
                    filename=file.filename,
                    collection_id=collection_id,
                    image_number=image_number
                )
                ACTIVE_IMAGES.append(img_data)
                
                file_info = FileInfo(
                    filename=file.filename,
                    file_id=img_data["image_id"],
                    file_type=file_type,
                    file_size_bytes=len(file_content),
                    pages=1,
                    chunks=0,
                    status=UploadStatus.PROCESSED
                )
                uploaded_files_info.append(file_info)
                logger.info(f"✅ {file.filename}: Image processed successfully")
                continue
            
            existing_fnums = [m.get("file_number", 1) for m in faiss_store.metadata if isinstance(m.get("file_number"), int)]
            base_file_num = max(existing_fnums) if existing_fnums else 0
            assigned_file_number = base_file_num + file_idx

            chunks, metadata = file_processor.process_file(
                file_content=file_content,
                filename=file.filename,
                file_type=file_type,
                collection_id=collection_id,
                file_number=assigned_file_number
            )
            
            if not chunks:
                logger.warning(f"⚠️ No chunks generated for {file.filename}")
                failed_files.append({
                    "filename": file.filename,
                    "reason": "No text content extracted"
                })
                continue
            
            # ============ STEP 2: GENERATE EMBEDDINGS ============
            logger.info(f"Step 2: Generating embeddings for {len(chunks)} chunks...")
            chunk_embedding_pairs = embedding_service.batch_embed_chunks(chunks)
            
            # Separate chunks and embeddings
            chunks_with_embeddings = []
            embeddings_list = []
            
            for chunk, embedding in chunk_embedding_pairs:
                if embedding is not None:
                    chunks_with_embeddings.append(chunk)
                    embeddings_list.append(embedding)
                else:
                    logger.warning(f"⚠️ Failed to embed chunk: {chunk.chunk_id}")
            
            if not embeddings_list:
                logger.warning(f"⚠️ No embeddings generated for {file.filename}")
                failed_files.append({
                    "filename": file.filename,
                    "reason": "Failed to generate embeddings"
                })
                continue
            
            # ============ STEP 3: STORE IN FAISS ============
            logger.info(f"Step 3: Storing {len(embeddings_list)} embeddings in FAISS...")
            success, error = faiss_store.add_vectors(
                chunks=chunks_with_embeddings,
                embeddings=embeddings_list
            )
            
            if not success:
                logger.error(f"❌ Failed to store in FAISS: {error}")
                failed_files.append({
                    "filename": file.filename,
                    "reason": f"Storage failed: {error}"
                })
                continue
            
            # ============ STEP 4: SAVE FAISS INDEX ============
            logger.info(f"Step 4: Persisting FAISS index to disk...")
            success, error = faiss_store.save_index()
            
            if not success:
                logger.error(f"⚠️ Warning: Failed to save index: {error}")
                # Continue anyway - index is still in memory
            
            # ============ SUCCESS ============
            
            file_info = FileInfo(
                filename=file.filename,
                file_id=metadata.file_id,
                file_type=file_type,
                file_size_bytes=len(file_content),
                pages=metadata.pages,
                chunks=len(chunks_with_embeddings),
                status=UploadStatus.PROCESSED
            )
            
            uploaded_files_info.append(file_info)
            total_chunks += len(chunks_with_embeddings)
            total_embeddings += len(embeddings_list)
            
            logger.info(
                f"✅ {file.filename}: {len(chunks_with_embeddings)} chunks, "
                f"{len(embeddings_list)} embeddings"
            )
            
        except ValueError as e:
            # Validation error
            logger.error(f"❌ Validation error for {file.filename}: {str(e)}")
            failed_files.append({
                "filename": file.filename,
                "reason": str(e)
            })
            
        except Exception as e:
            # Processing error
            logger.error(f"❌ Processing error for {file.filename}: {str(e)}")
            failed_files.append({
                "filename": file.filename,
                "reason": f"Processing failed: {str(e)}"
            })
    
    # ============ BUILD RESPONSE ============
    
    processing_time = time.time() - start_time
    
    if not uploaded_files_info:
        # All files failed
        logger.error("❌ All files failed to process")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "error",
                "message": "Failed to process any files",
                "error_code": "PROCESSING_FAILED",
                "details": {"failed_files": failed_files}
            }
        )
    
    # At least some files succeeded
    response_data = {
        "uploaded_files": [f.model_dump() for f in uploaded_files_info],
        "total_files": len(uploaded_files_info),
        "total_chunks": total_chunks,
        "total_embeddings_generated": total_embeddings,
        "processing_time_seconds": round(processing_time, 2)
    }
    
    if failed_files:
        response_data["failed_files"] = failed_files
        response_data["partial_success"] = True
        message = f"{len(uploaded_files_info)} files succeeded, {len(failed_files)} failed"
        logger.warning(f"⚠️ {message}")
    else:
        message = f"{len(uploaded_files_info)} files uploaded and processed successfully"
        logger.info(f"✅ {message}")
    
    return UploadResponse(
        status="success",
        message=message,
        data=response_data
    )


# ============ LIST DOCUMENTS ENDPOINT ============

@router.get("/documents", tags=["Documents"])
async def list_documents(collection_id: str = "default"):
    """
    List all documents in a collection
    
    Args:
        collection_id: User/collection ID
        
    Returns:
        List of documents with metadata
    """
    
    logger.info(f"📋 Listing documents for collection: {collection_id}")
    
    try:
        faiss_store = get_faiss_store()
        stats = faiss_store.get_stats()
        
        # Get unique files from metadata
        unique_files = {}
        
        for meta in faiss_store.metadata:
            if meta["file_id"] not in unique_files:
                unique_files[meta["file_id"]] = {
                    "file_id": meta["file_id"],
                    "chunks": 0,
                    "page_numbers": set()
                }
            
            unique_files[meta["file_id"]]["chunks"] += 1
            if meta["page_number"]:
                unique_files[meta["file_id"]]["page_numbers"].add(meta["page_number"])
        
        # Format response
        documents = []
        for file_id, info in unique_files.items():
            documents.append({
                "file_id": file_id,
                "chunks": info["chunks"],
                "pages": len(info["page_numbers"]) if info["page_numbers"] else 0
            })
        
        return {
            "status": "success",
            "data": {
                "documents": documents,
                "total_documents": len(documents),
                "total_chunks": stats.get("total_chunks", 0),
                "index_stats": stats
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": "Failed to list documents",
                "error_code": "LIST_FAILED"
            }
        )


# ============ DELETE DOCUMENT ENDPOINT ============

@router.delete("/documents/{file_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    file_id: str,
    collection_id: str = "default"
) -> DeleteDocumentResponse:
    """
    Delete a document and its embeddings from FAISS
    
    Args:
        file_id: File ID to delete
        collection_id: User/collection ID
        
    Returns:
        DeleteDocumentResponse: Deletion status
    """
    
    logger.info(f"🗑️ Deleting document: {file_id}")
    
    try:
        faiss_store = get_faiss_store()
        
        # Delete from FAISS
        success, error = faiss_store.delete_by_file_id(file_id)
        
        if not success:
            logger.error(f"❌ Failed to delete: {error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "status": "error",
                    "message": error,
                    "error_code": "DELETION_FAILED"
                }
            )
        
        # Save updated index
        faiss_store.save_index()
        
        # Count deleted chunks
        deleted_chunks = sum(1 for m in faiss_store.metadata if m["file_id"] == file_id)
        
        logger.info(f"✅ Deleted document: {file_id} ({deleted_chunks} chunks)")
        
        return DeleteDocumentResponse(
            status="success",
            message=f"Document {file_id} deleted successfully",
            data={
                "file_id": file_id,
                "chunks_removed": deleted_chunks
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": f"Deletion failed: {str(e)}",
                "error_code": "DELETION_FAILED"
            }
        )


@router.delete("/documents-clear-all", tags=["Documents"])
async def clear_all_documents(collection_id: str = "default"):
    logger.info(f"🗑️ Clearing all documents for collection: {collection_id}")
    try:
        from app.services.rag_service import clear_active_images
        clear_active_images()
        
        faiss_store = get_faiss_store()
        faiss_store.clear_index()
        faiss_store.save_index()
        return {
            "status": "success",
            "message": "All indexed documents and images cleared successfully"
        }
    except Exception as e:
        logger.error(f"❌ Error clearing all documents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "status": "error",
                "message": f"Failed to clear documents: {str(e)}",
                "error_code": "CLEAR_FAILED"
            }
        )


@router.get("/documents/{file_id}/file", tags=["Documents"])
async def get_document_file(file_id: str, collection_id: str = "default"):
    faiss_store = get_faiss_store()
    filename = None
    for meta in faiss_store.metadata:
        if meta.get("file_id") == file_id:
            filename = meta.get("filename")
            break

    collection_dir = UPLOAD_DIR / collection_id
    for file_path in collection_dir.glob(f"{file_id}.*"):
        if file_path.exists():
            return FileResponse(
                path=str(file_path),
                filename=filename or file_path.name,
                media_type="application/octet-stream"
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Requested document file not found"
    )