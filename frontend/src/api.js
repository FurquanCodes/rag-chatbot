import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function extractErrorMessage(error) {
  if (error.response && error.response.data) {
    const detail = error.response.data.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object") {
      return detail.message || detail.error || JSON.stringify(detail);
    }
    if (error.response.data.message) {
      return error.response.data.message;
    }
  }
  return error.message || "An unexpected error occurred.";
}

export async function uploadDocument(files, collectionId = "default") {
  try {
    const formData = new FormData();
    const fileArray = Array.isArray(files) ? files : [files];
    fileArray.forEach((f) => formData.append("files", f));
    formData.append("collection_id", collectionId);
    const res = await axios.post(`${BASE_URL}/api/v1/upload`, formData);
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function uploadDocuments(files, collectionId = "default") {
  return uploadDocument(files, collectionId);
}

export async function askQuestion(options) {
  const {
    question,
    collectionId = "default",
    collection_id,
    searchType = "hybrid",
    search_type,
    topK = 5,
    top_k,
    relevanceThreshold = 0.7,
    relevance_threshold,
  } = typeof options === "string" ? { question: options } : options;

  const targetCollection = collection_id || collectionId;
  const targetStrategy = search_type || searchType;
  const targetTopK = top_k || topK;
  const targetThreshold = relevance_threshold || relevanceThreshold;

  try {
    const res = await axios.post(`${BASE_URL}/api/v1/chat`, {
      question,
      collection_id: targetCollection,
      search_type: targetStrategy,
      top_k: targetTopK,
      relevance_threshold: targetThreshold,
    });
    const data = res.data.data || res.data;
    const sourcesList = data.sources || [];
    const sourceName = sourcesList
      .map((s) => s.source_name)
      .filter(Boolean)
      .join(", ");
    return {
      answer: data.answer,
      source: sourceName || null,
      sources: sourcesList,
      retrievalDetails: data.retrieval_details || null,
      raw: res.data,
    };
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function listDocuments(collectionId = "default") {
  try {
    const res = await axios.get(`${BASE_URL}/api/v1/documents`, {
      params: { collection_id: collectionId },
    });
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function deleteDocument(fileId, collectionId = "default") {
  try {
    const res = await axios.delete(`${BASE_URL}/api/v1/documents/${fileId}`, {
      params: { collection_id: collectionId },
    });
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}

export async function checkBackendHealth() {
  try {
    const res = await axios.get(`${BASE_URL}/api/v1/health`);
    return res.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
}
