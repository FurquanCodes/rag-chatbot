import { useState } from "react";
import MessageBubble from "./MessageBubble";
import { askQuestion } from "../api";

function ChatWindow({ messages, setMessages }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    if (!input.trim()) return;
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
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} text={m.text} source={m.source} />
        ))}
        {loading && <p className="text-sm text-gray-400">Thinking...</p>}
      </div>
      <div className="p-4 border-t border-gray-200 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question..."
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2"
        />
        <button onClick={handleSend} className="bg-blue-500 text-white px-4 py-2 rounded-lg">
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatWindow;