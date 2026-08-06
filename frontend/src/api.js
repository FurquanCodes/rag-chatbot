import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await axios.post(`${BASE_URL}/upload`, formData);
  return res.data;
}

export async function askQuestion(question) {
  const res = await axios.post(`${BASE_URL}/ask`, { question });
  return res.data;
}