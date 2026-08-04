"""
Application constants
Define all constant values used throughout the application
"""

# ============ File Type Constants ============
ALLOWED_EXTENSIONS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain"
}

# ============ API Route Constants ============
API_V1_PREFIX = "/api/v1"
API_ROUTES = {
    "upload": f"{API_V1_PREFIX}/upload",
    "chat": f"{API_V1_PREFIX}/chat",
    "documents": f"{API_V1_PREFIX}/documents",
    "health": f"{API_V1_PREFIX}/health"
}

# ============ Document Processing Constants ============
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_TOP_K = 5

# ============ Error Messages ============
ERROR_MESSAGES = {
    "INVALID_FILE_TYPE": "Invalid file type. Allowed types: PDF, DOCX, PPTX, TXT",
    "FILE_TOO_LARGE": "File size exceeds maximum limit",
    "NO_DOCUMENTS": "No documents uploaded. Please upload documents first.",
    "EMPTY_QUESTION": "Question cannot be empty",
    "RETRIEVAL_FAILED": "Failed to retrieve relevant context",
    "API_ERROR": "API request failed"
}

# ============ Success Messages ============
SUCCESS_MESSAGES = {
    "FILE_UPLOADED": "File uploaded successfully",
    "FILE_DELETED": "File deleted successfully",
    "DOCUMENT_PROCESSED": "Document processed successfully"
}

# ============ HTTP Status Codes ============
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_400_BAD_REQUEST = 400
HTTP_404_NOT_FOUND = 404
HTTP_500_INTERNAL_ERROR = 500