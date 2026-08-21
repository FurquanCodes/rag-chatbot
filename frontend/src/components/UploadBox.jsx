import { uploadDocuments } from "../api";

function UploadBox({ onUploaded, isUploading, setIsUploading }) {
  async function handleFileChange(e) {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    if (setIsUploading) setIsUploading(true);

    try {
      const res = await uploadDocuments(files);
      const fileNames = files.map((f) => f.name).join(", ");
      const uploadedFiles = res?.data?.uploaded_files || [];
      const fileId = uploadedFiles.length > 0 ? uploadedFiles[0].file_id : null;
      if (onUploaded) onUploaded(fileNames, fileId);
    } catch (err) {
      console.error("Upload error:", err);
      const errorDetail = err.response?.data?.detail;
      const errorMsg = errorDetail?.message || (typeof errorDetail === 'string' ? errorDetail : null) || err.message || "Failed to upload file. Please try again.";
      alert(`Upload Failed: ${errorMsg}`);
    } finally {
      if (setIsUploading) setIsUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="relative flex items-center gap-2">
      <label
        className={`w-11 h-11 rounded-xl bg-[#131B2E] border border-[#22304E] hover:border-[#2563EB] flex items-center justify-center text-lg cursor-pointer transition-all shadow-md ${
          isUploading ? "opacity-50 cursor-not-allowed" : ""
        }`}
        title="Upload Document (PDF, DOCX, PPTX, TXT)"
      >
        {isUploading ? (
          <span className="animate-spin text-sm">⏳</span>
        ) : (
          <span>📎</span>
        )}
        <input
          type="file"
          accept=".pdf,.docx,.pptx,.txt"
          multiple
          disabled={isUploading}
          onChange={handleFileChange}
          className="hidden"
        />
      </label>

      <label
        className={`w-11 h-11 rounded-xl bg-[#131B2E] border border-[#22304E] hover:border-[#2563EB] flex items-center justify-center text-lg cursor-pointer transition-all shadow-md ${
          isUploading ? "opacity-50 cursor-not-allowed" : ""
        }`}
        title="Upload Image (PNG, JPG, WEBP, GIF)"
      >
        {isUploading ? (
          <span className="animate-spin text-sm">⏳</span>
        ) : (
          <span>🖼️</span>
        )}
        <input
          type="file"
          accept=".png,.jpg,.jpeg,.webp,.gif"
          multiple
          disabled={isUploading}
          onChange={handleFileChange}
          className="hidden"
        />
      </label>
    </div>
  );
}

export default UploadBox;