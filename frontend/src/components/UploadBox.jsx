import { useState } from "react";
import { uploadDocument } from "../api";

function UploadBox({ onUploaded }) {
  const [status, setStatus] = useState("");

  async function handleFileChange(e) {
    const file = e.target.files[0];
    if (!file) return;
    setStatus("Uploading...");
    try {
      await uploadDocument(file);
      setStatus(`Uploaded: ${file.name}`);
      onUploaded(file.name);
    } catch (err) {
      setStatus("Upload failed");
    }
  }

  return (
    <div className="p-4 border-b border-gray-200">
      <label className="cursor-pointer inline-block bg-blue-500 text-white px-4 py-2 rounded-lg">
        Upload Document
        <input type="file" accept=".pdf,.docx,.txt" onChange={handleFileChange} className="hidden" />
      </label>
      {status && <p className="text-sm text-gray-500 mt-2">{status}</p>}
    </div>
  );
}

export default UploadBox;