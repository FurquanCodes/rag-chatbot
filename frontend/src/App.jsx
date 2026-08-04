import { useState } from "react";
import UploadBox from "./components/UploadBox";
import ChatWindow from "./components/ChatWindow";

function App() {
  const [messages, setMessages] = useState([]);

  return (
    <div className="flex flex-col h-screen">
      <header className="p-4 bg-gray-900 text-white text-lg font-semibold">
        Document Chatbot
      </header>
      <UploadBox onUploaded={(name) => setMessages((prev) => [...prev, { role: "assistant", text: `Document "${name}" is ready. Ask me anything about it.` }])} />
      <ChatWindow messages={messages} setMessages={setMessages} />
    </div>
  );
}

export default App;