import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function uploadDocuments(files, collectionId = "default") {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });
  formData.append("collection_id", collectionId);
  const res = await axios.post(`${BASE_URL}/api/v1/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return res.data;
}

export async function askQuestion(params) {
  let payload;
  if (typeof params === "string") {
    payload = {
      question: params,
      collection_id: "default",
      search_type: "hybrid",
      top_k: 5,
      relevance_threshold: 0.0,
    };
  } else {
    payload = {
      question: params.question,
      collection_id: params.collection_id || "default",
      file_id: params.file_id || undefined,
      search_type: params.search_type || "hybrid",
      top_k: params.top_k || 5,
      relevance_threshold: params.relevance_threshold ?? 0.0,
    };
  }

  const res = await axios.post(`${BASE_URL}/api/v1/chat`, payload);
  return res.data;
}

export async function listDocuments(collectionId = "default") {
  const res = await axios.get(`${BASE_URL}/api/v1/documents`, {
    params: { collection_id: collectionId },
  });
  return res.data;
}

export async function deleteDocument(fileId, collectionId = "default") {
  const res = await axios.delete(`${BASE_URL}/api/v1/documents/${fileId}`, {
    params: { collection_id: collectionId },
  });
  return res.data;
}

export async function clearAllDocuments(collectionId = "default") {
  const res = await axios.delete(`${BASE_URL}/api/v1/documents-clear-all`, {
    params: { collection_id: collectionId },
  });
  return res.data;
}

export async function checkHealth() {
  const res = await axios.get(`${BASE_URL}/api/v1/health`, { timeout: 3000 });
  return res.data;
}