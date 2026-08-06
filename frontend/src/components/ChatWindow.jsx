import { useState, useRef, useEffect } from "react";
import MessageBubble from "./MessageBubble";
import UploadBox from "./UploadBox";
import { askQuestion } from "../api";

function ChatWindow({ messages, setMessages, fileName, onUploaded }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;
    const userMessage = { role: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    try {
      const result = await askQuestion(input);
      setMessages((prev) => [...prev, { role: "assistant", text: result.answer, source: result.source }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", text: "Something went wrong. Try again." }]);
    }
    setLoading(false);
  }

  function handleKeyDown(e) {
    if (e.key === "Enter") handleSend();
  }

  return (
    <div className="flex flex-col flex-1">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <p className="text-center text-gray-400 mt-10">Upload a document below, then ask a question to get started.</p>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} text={m.text} source={m.source} />
        ))}
        {loading && <p className="text-sm text-gray-400">Thinking...</p>}
        <div ref={bottomRef} />
      </div>
      {fileName && <p className="text-xs text-gray-500 px-4">Active document: {fileName}</p>}
      <div className="p-4 border-t border-gray-200 flex gap-2 items-center">
        <UploadBox onUploaded={onUploaded} />
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          disabled={loading}
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 disabled:bg-gray-100"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className={`px-4 py-2 rounded-lg text-white ${loading ? "bg-blue-300 cursor-not-allowed" : "bg-blue-500"}`}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatWindow;