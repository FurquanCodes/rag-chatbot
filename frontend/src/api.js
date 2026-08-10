import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Upload multiple documents
export async function uploadDocuments(files, collectionId = "default") {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });
  formData.append("collection_id", collectionId);
  const res = await axios.post(`${BASE_URL}/api/v1/upload`, formData);

  return res.data;
}

// Ask a question with optional search strategy params
export async function askQuestion(params) {
  const questionStr = typeof params === "string" ? params : params?.question;
  const collectionId = (typeof params === "object" && params?.collection_id) || "default";
  const searchType = (typeof params === "object" && params?.search_type) || "hybrid";
  const topK = (typeof params === "object" && params?.top_k) || 5;
  const relevanceThreshold = (typeof params === "object" && params?.relevance_threshold) || 0.7;

  const payload = {
    question: questionStr,
    collection_id: collectionId,
    search_type: searchType,
    top_k: topK,
    relevance_threshold: relevanceThreshold
  };

  const res = await axios.post(`${BASE_URL}/api/v1/chat`, payload);
  return res.data;
}

// List all indexed documents for a collection
export async function listDocuments(collectionId = "default") {
  const res = await axios.get(`${BASE_URL}/api/v1/documents`, { params: { collection_id: collectionId } });
  return res.data;
}

// Delete a document by its file_id
export async function deleteDocument(fileId, collectionId = "default") {
  const res = await axios.delete(`${BASE_URL}/api/v1/documents/${fileId}`, { params: { collection_id: collectionId } });
  return res.data;
}