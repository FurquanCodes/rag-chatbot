import { useState, useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import UploadBox from "./UploadBox";
import { askQuestion } from "../api";

function ChatWindow({
  messages,
  setMessages,
  fileName,
  onUploaded,
  searchType,
  documents,
  collectionId,
  backendConnected,
}) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(customText) {
    const textToSend = customText || input;
    if (!textToSend.trim() || loading) return;

    const userMessage = { role: "user", text: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    if (!customText) setInput("");
    setLoading(true);

    try {
      const result = await askQuestion({
        question: textToSend,
        collectionId: collectionId || "default",
        searchType: searchType || "hybrid",
      });

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: result.answer,
          source: result.source,
          sources: result.sources,
          retrievalDetails: result.retrievalDetails,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: err.message || "Failed to process question. Please check backend connection.",
          isError: true,
        },
      ]);
    }
    setLoading(false);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const sampleQuestions = [
    "What are the key points in the uploaded document?",
    "Summarize the main topics.",
    "What does Wikipedia say about Quantum Computing?",
  ];

  return (
    <div className="flex flex-col flex-1 bg-gray-900 h-full overflow-hidden">
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full max-w-xl mx-auto text-center space-y-6 my-8">
            <div className="w-16 h-16 bg-blue-600/20 border border-blue-500/30 rounded-2xl flex items-center justify-center text-3xl">
              🤖
            </div>
            <div>
              <h2 className="text-xl font-bold text-white mb-2">Welcome to RAG Chatbot</h2>
              <p className="text-sm text-gray-400">
                Upload your PDF, DOCX, PPTX, or TXT documents using the clip icon below, or ask questions powered by document search and Wikipedia fallback.
              </p>
            </div>

            <div className="w-full space-y-2 pt-2">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block text-left px-1">
                Suggested Prompts
              </span>
              <div className="grid grid-cols-1 gap-2">
                {sampleQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q)}
                    className="text-left text-xs bg-gray-800/80 hover:bg-gray-800 text-gray-300 hover:text-white p-3 rounded-lg border border-gray-750 transition-colors flex items-center justify-between"
                  >
                    <span>{q}</span>
                    <span className="text-gray-400">➔</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            role={m.role}
            text={m.text}
            source={m.source}
            sources={m.sources}
            retrievalDetails={m.retrievalDetails}
            isError={m.isError}
          />
        ))}

        {loading && (
          <div className="flex items-center gap-3 text-gray-400 text-sm mb-4 p-3 bg-gray-850/60 rounded-lg w-max border border-gray-800">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <span>Searching context and generating answer...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-3 md:p-4 border-t border-gray-800 bg-gray-950/60 backdrop-blur">
        {documents && documents.length > 0 && (
          <div className="mb-2 px-1 flex items-center gap-2 overflow-x-auto text-xs text-gray-400">
            <span className="font-semibold text-gray-400">Active Context:</span>
            {documents.map((doc) => (
              <span
                key={doc.file_id}
                className="bg-gray-800 text-gray-300 px-2 py-0.5 rounded border border-gray-700 font-mono text-[11px] shrink-0"
              >
                📄 {doc.filename}
              </span>
            ))}
          </div>
        )}

        <div className="flex gap-2 items-center max-w-4xl mx-auto">
          <UploadBox onUploaded={onUploaded} collectionId={collectionId} />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              backendConnected
                ? "Ask a question about your documents..."
                : "Connecting to backend server..."
            }
            disabled={loading}
            className="flex-1 bg-gray-800 text-white placeholder-gray-500 border border-gray-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-blue-500 disabled:opacity-50 transition-colors"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className={`px-5 py-2.5 rounded-xl font-medium text-sm text-white transition-all ${
              loading || !input.trim()
                ? "bg-gray-800 text-gray-500 cursor-not-allowed border border-gray-750"
                : "bg-blue-600 hover:bg-blue-500 shadow-md shadow-blue-600/20"
            }`}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatWindow;