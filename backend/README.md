# RAG Chatbot - Backend

FastAPI backend for RAG (Retrieval Augmented Generation) Chatbot system.

## Setup

### 1. Clone the repository
\\\ash
git clone https://github.com/FurquanCodes/rag-chatbot.git
cd rag-chatbot/backend
\\\

### 2. Create virtual environment
\\\ash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
\\\

### 3. Install dependencies
\\\ash
pip install -r requirements.txt
\\\

### 4. Setup environment variables
\\\ash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
\\\

### 5. Run the server
\\\ash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
\\\

Server will be available at: http://localhost:8000

## API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure
\\\
backend/
├── app/
│   ├── api/
│   │   └── routes/          # API endpoints
│   ├── services/            # Business logic
│   ├── models/              # Pydantic schemas
│   ├── utils/               # Utilities & config
│   └── storage/             # FAISS & file operations
├── tests/                   # Unit tests
├── uploads/                 # Uploaded documents
├── requirements.txt         # Dependencies
└── .env.example            # Environment template
\\\

## Team Structure
- **Backend (You):** FastAPI, LangChain, FAISS, Document Processing
- **Frontend (Teammate):** React, Tailwind CSS

## API Endpoints (Coming Soon)
- \POST /api/v1/upload\ - Upload documents
- \POST /api/v1/chat\ - Ask questions
- \GET /api/v1/documents\ - List documents
- \DELETE /api/v1/documents/{id}\ - Delete document
