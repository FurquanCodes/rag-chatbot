import { useState, useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import UploadBox from "./UploadBox";
import { askQuestion } from "../api";

function ChatWindow({
  messages,
  setMessages,
  fileName,
  fileId,
  onUploaded,
  searchStrategy,
  documentsCount,
  isConnected,
  isUploading,
  setIsUploading,
}) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(customText) {
    const textToSend = typeof customText === "string" ? customText : input;
    if (!textToSend.trim() || loading || isUploading || !isConnected) return;

    const userMessage = { role: "user", text: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const result = await askQuestion({
        question: textToSend,
        collection_id: "default",
        file_id: undefined,
        search_type: searchStrategy,
        top_k: 8,
        relevance_threshold: 0.0,
      });

      const responseText = result.data?.answer || result.answer || "No response received.";
      const sources = result.data?.sources || result.sources || [];

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: responseText,
          sources: sources,
        },
      ]);
    } catch (err) {
      console.error(err);
      const errorMsg =
        err.response?.data?.detail?.message ||
        err.response?.data?.message ||
        (typeof err.response?.data?.detail === "string"
          ? err.response.data.detail
          : null) ||
        err.message ||
        "Failed to process request. Please try again.";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: errorMsg,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex flex-col flex-1 bg-[#0D111D] text-slate-100 h-screen overflow-hidden">
      <div className="h-14 px-6 border-b border-[#1A2338] bg-[#0A0D16] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="font-semibold text-white text-base">New Chat</h1>
          <span className="bg-[#1E293B] text-slate-300 text-xs px-2.5 py-0.5 rounded-full border border-[#334155] font-medium">
            {searchStrategy === "hybrid"
              ? "Hybrid RAG"
              : searchStrategy === "documents_only"
              ? "Docs Only"
              : "Wikipedia"}
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <span className="text-slate-400">
            {documentsCount || 0} file(s) in index
          </span>
          <div className="flex items-center gap-1.5 font-medium">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? "bg-emerald-500 animate-pulse" : "bg-red-500"
              }`}
            ></span>
            <span
              className={`px-2.5 py-1 rounded-full text-[11px] ${
                isConnected
                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800/50"
                  : "bg-red-950 text-red-400 border border-red-800/50"
              }`}
            >
              {isConnected ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
        {messages.length === 0 ? (
          <div className="max-w-2xl mx-auto my-auto py-12 flex flex-col items-center text-center">
            <div className="w-16 h-16 rounded-2xl bg-[#1E293B] border border-[#334155] flex items-center justify-center text-3xl shadow-lg mb-6">
              🤖
            </div>

            <h2 className="text-2xl font-bold text-white mb-2">
              Welcome to RAG Chatbot
            </h2>
            <p className="text-slate-400 text-sm max-w-lg mb-8 leading-relaxed">
              Upload your PDF, DOCX, PPTX, TXT documents or Images using the icons
              below, or ask questions powered by document search and Wikipedia
              fallback.
            </p>

            <div className="w-full space-y-3">
              <p className="text-xs font-bold text-slate-500 tracking-wider text-left uppercase">
                SUGGESTED PROMPTS
              </p>

              <button
                onClick={() => handleSend("What are the key points in the uploaded document?")}
                className="w-full text-left bg-[#131B2E] hover:bg-[#1C2843] border border-[#22304E] rounded-xl p-3.5 text-xs text-slate-200 flex items-center justify-between group transition-all"
              >
                <span>What are the key points in the uploaded document?</span>
                <span className="text-slate-500 group-hover:text-white transition-colors">
                  →
                </span>
              </button>

              <button
                onClick={() => handleSend("Summarize the main topics.")}
                className="w-full text-left bg-[#131B2E] hover:bg-[#1C2843] border border-[#22304E] rounded-xl p-3.5 text-xs text-slate-200 flex items-center justify-between group transition-all"
              >
                <span>Summarize the main topics.</span>
                <span className="text-slate-500 group-hover:text-white transition-colors">
                  →
                </span>
              </button>

              <button
                onClick={() => handleSend("What does Wikipedia say about Quantum Computing?")}
                className="w-full text-left bg-[#131B2E] hover:bg-[#1C2843] border border-[#22304E] rounded-xl p-3.5 text-xs text-slate-200 flex items-center justify-between group transition-all"
              >
                <span>What does Wikipedia say about Quantum Computing?</span>
                <span className="text-slate-500 group-hover:text-white transition-colors">
                  →
                </span>
              </button>
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto space-y-4">
            {messages.map((m, i) => (
              <MessageBubble
                key={i}
                role={m.role}
                text={m.text}
                sources={m.sources}
              />
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-slate-400 text-xs italic bg-[#131B2E] p-3 rounded-xl max-w-xs">
                <span className="animate-spin">⏳</span> Processing answer...
              </div>
            )}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 bg-[#0A0D16] border-t border-[#1A2338] shrink-0">
        <div className="max-w-3xl mx-auto space-y-2">
          {fileName && (
            <p className="text-[11px] text-slate-400 flex items-center gap-1.5 px-1">
              <span>
                {fileName.match(/\.(png|jpg|jpeg|webp|gif)$/i) 
                  ? "🖼️ [Image Preview]" 
                  : "📄 Active file:"}
              </span>
              <span className="font-semibold text-slate-200">{fileName}</span>
            </p>
          )}

          <div className="flex items-center gap-3">
            <UploadBox
              onUploaded={onUploaded}
              isUploading={isUploading}
              setIsUploading={setIsUploading}
            />

            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                !isConnected
                  ? "Connecting to backend server..."
                  : isUploading
                  ? "Uploading file..."
                  : "Ask a question..."
              }
              disabled={loading || isUploading || !isConnected}
              className="flex-1 bg-[#131B2E] text-slate-100 placeholder-slate-500 border border-[#22304E] rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-[#2563EB] disabled:opacity-50 transition-colors"
            />

            <button
              onClick={() => handleSend()}
              disabled={loading || isUploading || !isConnected || !input.trim()}
              className={`px-5 py-3 rounded-xl font-medium text-sm text-white transition-all shadow-md ${
                loading || isUploading || !isConnected || !input.trim()
                  ? "bg-[#1E293B] text-slate-500 cursor-not-allowed border border-[#334155]"
                  : "bg-[#2563EB] hover:bg-[#1D4ED8]"
              }`}
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;