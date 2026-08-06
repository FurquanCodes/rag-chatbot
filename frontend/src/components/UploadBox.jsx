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
      setStatus("");
      onUploaded(file.name);
    } catch (err) {
      setStatus("Failed");
    }
  }

  return (
    <div className="flex items-center gap-1">
      <label className="cursor-pointer flex items-center justify-center bg-gray-800 text-gray-200 w-10 h-10 rounded-lg text-lg border border-gray-700" title="Upload document">
        📎
        <input type="file" accept=".pdf,.docx,.txt" onChange={handleFileChange} className="hidden" />
      </label>
      {status && <span className="text-xs text-gray-500">{status}</span>}
    </div>
  );
}

export default UploadBox;