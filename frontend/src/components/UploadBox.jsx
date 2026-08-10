import { useState, useRef } from "react";
import { uploadDocument } from "../api";

function UploadBox({ onUploaded, collectionId = "default" }) {
  const [uploading, setUploading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const fileInputRef = useRef(null);

  async function handleFileChange(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    setUploading(true);
    setErrorMsg("");

    try {
      const res = await uploadDocument(files, collectionId);
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (onUploaded) {
        onUploaded(res);
      }
    } catch (err) {
      setUploading(false);
      setErrorMsg(err.message || "Upload failed");
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <div className="relative flex items-center gap-2">
      <label
        className={`cursor-pointer flex items-center justify-center w-10 h-10 rounded-lg border transition-all ${
          uploading
            ? "bg-blue-900/50 border-blue-600 text-blue-300 animate-pulse cursor-wait"
            : "bg-gray-800 hover:bg-gray-750 text-gray-200 border-gray-700 hover:border-gray-600"
        }`}
        title="Upload PDF, DOCX, PPTX, or TXT"
      >
        {uploading ? (
          <span className="text-sm font-bold">⏳</span>
        ) : (
          <span className="text-lg">📎</span>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.pptx,.txt"
          multiple
          onChange={handleFileChange}
          disabled={uploading}
          className="hidden"
        />
      </label>

      {errorMsg && (
        <div className="absolute bottom-12 left-0 bg-red-900/90 text-red-200 border border-red-700 text-xs px-3 py-1.5 rounded shadow-lg whitespace-nowrap z-50 flex items-center gap-2">
          <span>⚠️ {errorMsg}</span>
          <button
            onClick={() => setErrorMsg("")}
            className="text-red-300 hover:text-white font-bold ml-1"
          >
            ×
          </button>
        </div>
      )}
    </div>
  );
}

export default UploadBox;